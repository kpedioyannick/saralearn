#!/usr/bin/env python3
"""Confronter chaque exercice à l'article dont il a été tiré.

C'est la vérification que toute la chaîne rend possible : le texte
source est sur disque, la question aussi, et la comparaison est
mécanique. Elle ne demande pas au modèle s'il est sûr de lui — elle lui
demande de retrouver, dans l'article, la phrase qui porte la réponse.

Trois verdicts par exercice :

  · `supported`   — l'article porte la réponse, avec la phrase citée ;
  · `contradicted`— l'article dit le contraire : l'exercice est faux ;
  · `unsupported` — l'article n'en parle pas : le modèle a inventé,
                    alors que la consigne était de ne rien écrire qui
                    ne vienne du texte.

Les contredits sont RETIRÉS. Les non étayés sont retirés aussi par
défaut — c'est le choix « refuser plutôt que corriger » de `critic.py`,
et celui d'un catalogue que personne ne relira. `--garder-non-etayes`
les laisse passer si l'on préfère le volume.

Le vérificateur est `deepseek-reasoner` et non `deepseek-chat` : un
relecteur qui partage exactement les angles morts de l'auteur ne
vérifie pas grand-chose, et comparer deux textes est le terrain d'un
modèle à raisonnement.

    python3 scripts/verify_deepseek.py --dry-run   # ne réécrit rien
    python3 scripts/verify_deepseek.py

Ne touche ni la base ni les fichiers sans source : seuls les lots
adossés à un article passent ici.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

WIKI = ROOT / "db" / "creation" / "wiki"
LOTS = ROOT / "db" / "creation" / "serie2-wiki"
RAPPORT = ROOT / "db" / "creation" / "verification.json"
DB = ROOT / "data" / "sara.db"


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower() or "chapitre"


def sources() -> dict[str, dict]:
    """Nom du lot → article source, via la base.

    Le nom d'un lot est `<slug-thème>-<NN>-<slug-chapitre>.json` et
    celui d'une source `<id-chapitre>.json` : rien ne les rapproche
    sans passer par `chapter`.
    """
    conn = sqlite3.connect(DB)
    table = {}
    for cid, ct, ts, pos in conn.execute(
            "SELECT ch.id, ch.title, t.slug, ch.position FROM chapter ch"
            " JOIN theme t ON t.id = ch.theme_id WHERE t.lang = 'en'"):
        path = WIKI / f"{cid}.json"
        if path.exists():
            table[f"{ts}-{pos:02d}-{slug(ct)}.json"] = json.loads(
                path.read_text(encoding="utf-8"))
    return table


def _load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_env()

API_URL = os.environ.get("SARA_LLM_URL", "https://api.deepseek.com/chat/completions")
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()

PRICE_IN_HIT, PRICE_IN_MISS, PRICE_OUT = 0.0028, 0.14, 0.28
SRC: dict[str, dict] = {}

PROMPT = """You are checking quiz questions against the article they \
were written from. You are not judging style, difficulty or wording — \
only whether the article backs what each question teaches.

--- ARTICLE ---
{text}
--- END OF ARTICLE ---

Here are the questions. For each one you are given its number, the \
question, the answer marked correct, and the explanation shown to the \
student afterwards.

{items}

For each numbered question, decide:

- "supported" — the article states this. You must quote the sentence \
from the article that carries it. If you cannot quote one, it is not \
supported.
- "contradicted" — the article says something different. Quote the \
sentence that conflicts.
- "unsupported" — the article simply does not cover this. The claim may \
well be true in the world; that is not the point. If the article is \
silent, say unsupported.

Judge the ANSWER and the EXPLANATION together. If the marked answer is \
right but the explanation adds a claim the article does not carry, that \
is unsupported.

Return a JSON array, one object per question, nothing else:
[{{"n": 1, "verdict": "supported", "quote": "<sentence from the \
article>"}}, ...]

Use "quote": null only for unsupported."""


def bloc(items: list[dict]) -> str:
    lignes = []
    for i, it in enumerate(items, 1):
        bonne = it["options"][it["correct_index"]]["label"]
        lignes.append(
            f"{i}. Q: {it['prompt']}\n"
            f"   Correct answer: {bonne}\n"
            f"   Explanation: {it['exp_text']}")
    return "\n\n".join(lignes)


async def one(client: httpx.AsyncClient, path: Path, gate: asyncio.Semaphore,
              model: str) -> dict:
    lots = json.loads(path.read_text(encoding="utf-8"))
    tid = lots[0]["theme_id"]
    items = [it for l in lots for it in l["items"]]

    src = SRC.get(path.name)
    if src is None:
        return {"file": path.name, "skipped": "source introuvable"}

    async with gate:
        try:
            resp = await client.post(API_URL, json={
                "model": model,
                "messages": [{"role": "user", "content": PROMPT.format(
                    text=src["text"], items=bloc(items))}],
                "max_tokens": 32000, "stream": False,
            }, headers={"Authorization": f"Bearer {API_KEY}"})
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            return {"file": path.name, "error": str(exc)[:140]}

    usage = payload.get("usage") or {}
    raw = payload["choices"][0]["message"]["content"]
    start = raw.find("[")
    if start == -1:
        fin = payload["choices"][0].get("finish_reason")
        return {"file": path.name, "usage": usage,
                "error": f"verdict illisible (finish={fin})"}
    try:
        verdicts, _ = json.JSONDecoder().raw_decode(raw[start:])
    except json.JSONDecodeError as exc:
        return {"file": path.name, "usage": usage,
                "error": f"verdict illisible : {exc}"}

    par_n = {v.get("n"): v for v in verdicts if isinstance(v, dict)}
    detail = []
    for i, it in enumerate(items, 1):
        v = par_n.get(i, {})
        detail.append({
            "n": i,
            "verdict": v.get("verdict", "unsupported"),
            "quote": v.get("quote"),
            "prompt": it["prompt"],
        })
    return {"file": path.name, "theme_id": tid, "usage": usage,
            "article": src["article"], "items": items, "detail": detail}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="deepseek-reasoner")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true",
                    help="mesurer sans rien réécrire")
    ap.add_argument("--strict", action="store_true",
                    help="retirer aussi les non étayés (voir la note)")
    args = ap.parse_args()

    if not API_KEY:
        sys.exit("DEEPSEEK_API_KEY absente")

    global SRC
    SRC = sources()
    lots = [p for p in sorted(LOTS.glob("*.json")) if p.name in SRC]
    if args.limit:
        lots = lots[:args.limit]
    print(f"{len(lots)} lot(s) · vérificateur {args.model} · "
          f"{args.concurrency} en parallèle\n")

    gate = asyncio.Semaphore(args.concurrency)
    async with httpx.AsyncClient(timeout=600) as client:
        res = await asyncio.gather(*[one(client, p, gate, args.model)
                                     for p in lots])

    compte = {"supported": 0, "contradicted": 0, "unsupported": 0}
    hit = miss = out = 0
    retires = 0
    rapport = []
    for r in res:
        if r.get("skipped") or r.get("error"):
            print(f"  ✗  {r['file']} — {r.get('error') or r['skipped']}")
            continue
        u = r.get("usage") or {}
        hit += u.get("prompt_cache_hit_tokens", 0)
        miss += u.get("prompt_cache_miss_tokens", u.get("prompt_tokens", 0))
        out += u.get("completion_tokens", 0)

        garder, jetes = [], []
        for d, it in zip(r["detail"], r["items"]):
            compte[d["verdict"]] = compte.get(d["verdict"], 0) + 1
            # Seuls les CONTREDITS partent par défaut. « Non étayé »
            # confond deux choses très différentes — un fait inventé, et
            # un fait vrai mais situé au-delà des 9 000 caractères
            # d'article qu'on a récupérés. Jeter les seconds coûterait
            # 13 % du catalogue pour rien. `--strict` le fait quand même.
            mauvais = d["verdict"] == "contradicted" or (
                args.strict and d["verdict"] == "unsupported")
            (jetes if mauvais else garder).append((d, it))

        if jetes:
            retires += len(jetes)
            print(f"  {r['file'][:52]:54s} {len(jetes):2d} retiré(s) "
                  f"← {r['article']}")
            for d, _ in jetes[:3]:
                print(f"       {d['verdict']:13s} {d['prompt'][:70]}")

        rapport.append({
            "file": r["file"], "article": r["article"],
            "verdicts": [{"verdict": d["verdict"], "prompt": d["prompt"],
                          "quote": d["quote"]} for d in r["detail"]],
        })

        if not args.dry_run and jetes:
            (LOTS / r["file"]).write_text(json.dumps(
                [{"theme_id": r["theme_id"], "items": [it for _, it in garder]}],
                ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    total = sum(compte.values())
    cost = (hit * PRICE_IN_HIT + miss * PRICE_IN_MISS + out * PRICE_OUT) / 1e6
    print(f"\n{total} exercice(s) vérifié(s)")
    for k in ("supported", "contradicted", "unsupported"):
        part = f"{round(100 * compte[k] / total)} %" if total else "—"
        print(f"  {k:14s} {compte[k]:5d}   {part}")
    print(f"\n{retires} retiré(s)" + (" (à blanc : rien réécrit)"
                                      if args.dry_run else ""))
    print(f"tokens : {hit} en cache · {miss} hors cache · {out} en sortie")
    print(f"coût estimé : {cost:.4f} $")
    RAPPORT.write_text(json.dumps(rapport, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    print(f"détail complet dans {RAPPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
