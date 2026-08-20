#!/usr/bin/env python3
"""Une deuxième série de dix QCM par chapitre, écrite par DeepSeek.

Le catalogue est complet : 196 chapitres, dix exercices chacun, écrits
par des agents. Ce script en produit dix de plus par chapitre — moins
cher, sans agent, un appel par chapitre.

**CE N'EST PAS LA MÊME SÉRIE.** Celle des agents pose le fonctionnement :
« pourquoi un insecte peut-il tourner la tête sans bouger le corps ».
Celle-ci pose **la connaissance de base** : ce qu'un élève doit savoir
avant que le reste ait un sens — ce qu'une chose est, comment elle
s'appelle, où elle se trouve, de quoi elle est faite. Nommer, situer,
compter y sont permis, ce que la règle éditoriale décourage ailleurs.

Aucune borne de longueur n'est donnée au modèle, nulle part : ni sur
l'énoncé, ni sur les options, ni sur l'explication. La longueur suit le
registre au lieu de le contraindre — un fait de base se dit court parce
qu'il est court, pas parce qu'on a compté les caractères.

Trois choses à savoir avant de s'en servir.

**Il n'y a aucune source.** Ni `theme.source_markdown`, ni
`chapter.description` : le programme a été semé par script. Le modèle
n'a que le titre du chapitre et celui du thème. Il écrit donc de
mémoire, comme les agents avant lui — c'est la faiblesse connue du
catalogue, et elle est ici assumée.

**Les dix bonnes questions sont déjà posées.** On passe au modèle les
énoncés déjà en base pour son thème, avec ordre de ne pas les redire.
Les dix suivants vont forcément chercher plus loin ; s'attendre à un
taux de rejet plus élevé que zéro.

**Le juge de `critic.py` n'est pas appelé**, conformément à la décision
« publication directe ». Le filet, c'est `check_rules` — les cinq refus
qui attrapent un exercice cassé — appliqué ici ET repassé par
`import_exercises.py`. On ne valide PAS avec `llm.validate` : celui-ci
tronque encore `exp_text` à 600 caractères et refuse une option de plus
de 60, deux bornes que le reste du dépôt a retirées.

    # galop d'essai, trois chapitres, rien en base
    python3 scripts/generate_deepseek.py --only 221,225,226

    # le catalogue entier
    python3 scripts/generate_deepseek.py --concurrency 8

Le script n'écrit que des fichiers, dans `db/creation/serie2/`. Il
n'importe rien et ne publie rien : ça reste `import_exercises.py` puis
`semer_creation.py --step publier`, à la main, une fois relu.
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

DB = ROOT / "data" / "sara.db"
OUT = ROOT / "db" / "creation" / "serie2"

# `api.config` lit os.environ à l'import : la clé doit y être avant.
# Apache la pose pour l'application ; en ligne de commande, personne.
def _load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_env()

from api.critic import check_rules  # noqa: E402

API_URL = os.environ.get("SARA_LLM_URL", "https://api.deepseek.com/chat/completions")
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()

# Tarifs DeepSeek au 14/08/2026, en dollars par million de tokens. Ils
# servent au décompte affiché en fin de course, rien d'autre — si le
# tarif bouge, le script continue de marcher, il ment juste sur le prix.
PRICE_IN_HIT = 0.0028
PRICE_IN_MISS = 0.14
PRICE_OUT = 0.28


# ── Le contrat de sortie ────────────────────────────────────────────
#
# Il est écrit ici et n'est jamais confié au modèle : il doit
# correspondre au caractère près à ce que `check_rules` accepte et à ce
# que `import_exercises.py` attend. Un modèle à qui l'on demande
# d'inventer ce contrat le réinvente à chaque appel, et les exercices
# sont écartés en silence à l'insertion.

SYSTEM = """You write multiple-choice questions for a school student, \
in English.

WHAT THIS SERIES IS — read this first, it changes everything else:

THESE ARE BASIC KNOWLEDGE QUESTIONS. Ask what a student should simply \
know about the chapter: what a thing is, what it is called, where it \
sits, what it does, what it is made of, what happens. Plain facts, \
plainly asked. A separate series already covers the deep mechanisms — \
this one is the ground floor, and it is allowed to name, to locate, and \
to count. Do not reach for the subtle or the clever question; reach for \
the one a student must know before anything else makes sense.

Write naturally. There is no length target, no word count, and no \
character limit anywhere — not on the question, not on the options, not \
on the explanation. Say what needs saying and stop.

THE EDITORIAL RULE — it decides everything:

1. ONLY THE CREATED WORLD, NEVER THE TOOL. Write about what exists and \
how it works. Never about what people build, measure, or name for their \
own use: no light bulbs, no telescopes, no time zones, no vaccines, no \
machines, no instruments, no industry, no units named after a person.

2. NO RECORDS, NO RANKINGS. Avoid superlatives and "which one is the \
biggest / fastest / oldest". A basic fact is not a record.

3. exp_text ANSWERS THE QUESTION THAT WAS ASKED. State the fact clearly, \
and add briefly how or why it is so when that helps the student \
remember. Its last sentence stays on the point of the question — never \
finish on a spectacular aside that crushes the answer.

4. EACH WRONG OPTION'S feedback SAYS WHY IT IS WRONG, not merely that \
it is. It must name the thing the student got confused about and \
correct it. Negating the option, or restating the right answer, teaches \
nothing. Bad: "There are only three sections, not four." Good: "The \
wings and legs all anchor to the middle section, so the parts you can \
count from outside are still three."

THE OUTPUT CONTRACT — exact, non-negotiable:

Return a JSON array of EXACTLY 10 objects and nothing else. No prose \
before or after, no code fence. Each object has exactly these keys:

{"type_question": "qcm", "prompt": "...?", \
"body": null, "correct_index": 0, "options": [{"label": "...", \
"feedback": "..."}, {"label": "...", "feedback": "..."}, {"label": \
"...", "feedback": "..."}, {"label": "...", "feedback": "..."}], \
"ok_title": "...", "ok_line": "...", "ko_title": "...", "ko_line": \
"...", "exp_title": "...", "exp_text": "..."}

- type_question is always "qcm"; body is always null.
- EXACTLY 4 options. correct_index is 0, 1, 2 or 3 and points at the \
correct one. Vary it across the ten questions.
- prompt MUST end with a question mark.
- No two options may read the same; no option may be empty.
- THE STUDENT HAS NEVER SEEN ANY ARTICLE, TEXT OR LESSON. Never refer \
to one. Banned outright, anywhere in any field: "the article", "the \
text", "the passage", "according to the article", "as mentioned in", \
"as described in", "the article states". If you are about to write the \
word "article", you are writing to the wrong reader — write the fact \
itself instead.
- The correct option's feedback confirms; the three others explain the \
error.
- ok_title / ko_title are two or three words. ok_line / ko_line are one \
short sentence. exp_title is a short noun phrase.
- Everything in English."""


USER = """Theme: {theme}
Chapter {position} of that theme: {chapter}

Write 10 new questions on this chapter.

{avoid}Write only about this chapter's subject. Vary what you ask \
about: do not write ten questions on the same fact seen from ten \
angles.

Return the JSON array only."""


# Le même travail, mais adossé à un article. Trois interdits s'ajoutent,
# chacun payé par un défaut observé : l'article est plein d'instruments
# et de savants (la règle éditoriale les refuse), un modèle qui vient de
# lire un texte y renvoie naturellement (`check_rules` refuse tout renvoi
# au support), et recopier les phrases de Wikipédia ferait entrer sa
# licence dans le catalogue.
USER_WIKI = """Theme: {theme}
Chapter {position} of that theme: {chapter}

Below is a reference article. EVERY FACT YOU WRITE MUST COME FROM IT. \
If the article does not say something, do not write it — not from your \
own memory, not by inference. If the article is thin on this chapter's \
subject, write fewer than ten questions rather than invent the rest.

Three things about using it:

- IGNORE what the article says about instruments, measuring devices, \
scientists, researchers, history, dates, industry, farming, units of \
measurement, and anything people build or manufacture. Those passages \
are off-limits for this catalogue, however prominent they are in the \
article. Take from it only what belongs to the created world itself.
- NEVER MENTION THE ARTICLE. No "according to the text", no "as the \
article says", no "the passage above". The student has nothing in front \
of them but your question.
- DO NOT COPY ITS SENTENCES. Write every question, option, feedback and \
explanation in your own words.

--- REFERENCE ARTICLE: {article} ---
{text}
--- END OF ARTICLE ---

{avoid}Write 10 new basic-knowledge questions on this chapter, using \
only what the article supports. Vary what you ask about.

Return the JSON array only."""


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "chapitre"


def chapters(conn: sqlite3.Connection, only: list[int], theme: int | None,
             limit: int) -> list[sqlite3.Row]:
    sql = ("SELECT ch.id, ch.theme_id, ch.position, ch.title,"
           " t.title AS theme_title, t.slug AS theme_slug"
           " FROM chapter ch JOIN theme t ON t.id = ch.theme_id"
           " WHERE t.lang = 'en'")
    params: list = []
    if only:
        sql += f" AND ch.id IN ({','.join('?' * len(only))})"
        params += only
    if theme:
        sql += " AND ch.theme_id = ?"
        params.append(theme)
    # Par thème puis par position : les appels d'un même thème se
    # suivent, et le bloc « déjà posé » reste identique d'un appel au
    # suivant — c'est ce que le cache de DeepSeek facture au centième.
    sql += " ORDER BY ch.theme_id, ch.position"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return list(conn.execute(sql, params))


def already_asked(conn: sqlite3.Connection, theme_id: int) -> str:
    """Les énoncés déjà en base pour ce thème, à ne pas redire."""
    rows = [r[0] for r in conn.execute(
        "SELECT prompt FROM exercise WHERE theme_id = ? AND state = 'validated'"
        " ORDER BY id", (theme_id,))]
    if not rows:
        return ""
    listing = "\n".join(f"- {p}" for p in rows)
    return ("These questions already exist for this theme. Do NOT ask "
            "them again, and do not ask a reworded version of any of "
            f"them:\n{listing}\n\n")


def parse(raw: str) -> list[dict]:
    """Le tableau JSON, quoi que le modèle ait mis autour."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start = text.find("[")
    if start == -1:
        raise ValueError("aucun tableau JSON dans la réponse")
    data, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(data, list):
        raise ValueError("la réponse n'est pas un tableau")
    return [d for d in data if isinstance(d, dict)]


def keep(item: dict) -> tuple[dict | None, str]:
    """Les mêmes refus qu'à l'import, plus la forme attendue du lot.

    On ne tronque rien et on ne rattrape rien : un exercice mal formé
    est écarté, il en reste neuf.
    """
    options = item.get("options")
    if not isinstance(options, list) or len(options) != 4:
        return None, "n'a pas quatre options"
    for opt in options:
        if not isinstance(opt, dict) or not str(opt.get("label", "")).strip():
            return None, "option sans libellé"
    prompt = str(item.get("prompt") or "").strip()
    if not prompt.endswith("?"):
        return None, "l'énoncé ne finit pas par « ? »"
    if not str(item.get("exp_text") or "").strip():
        return None, "exp_text vide"

    clean = {
        "type_question": "qcm",
        "prompt": prompt,
        "body": None,
        "correct_index": item.get("correct_index"),
        "options": [{"label": str(o["label"]).strip(),
                     "feedback": str(o.get("feedback") or "").strip()}
                    for o in options],
    }
    for field in ("ok_title", "ok_line", "ko_title", "ko_line",
                  "exp_title", "exp_text"):
        clean[field] = str(item.get(field) or "").strip() or None

    verdict = check_rules(clean, kind="qcm")
    if not verdict.ok:
        return None, " ; ".join(verdict.reasons)
    return clean, ""


WIKI = ROOT / "db" / "creation" / "wiki"


def source(chapter_id: int) -> dict | None:
    """L'article retenu pour ce chapitre, s'il y en a un."""
    path = WIKI / f"{chapter_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


async def one(client: httpx.AsyncClient, row: sqlite3.Row, avoid: str,
              model: str, gate: asyncio.Semaphore, force: bool,
              out: Path, use_wiki: bool) -> dict:
    name = f"{row['theme_slug']}-{row['position']:02d}-{slug(row['title'])}.json"
    path = out / name
    label = f"{row['theme_title']} · {row['title']}"

    if path.exists() and not force:
        return {"chapter": label, "file": name, "skipped": True}

    src = source(row["id"]) if use_wiki else None
    if use_wiki and not src:
        return {"chapter": label, "file": name, "nosource": True}
    if src:
        question = USER_WIKI.format(
            theme=row["theme_title"], position=row["position"],
            chapter=row["title"], avoid=avoid,
            article=src["article"], text=src["text"])
    else:
        question = USER.format(
            theme=row["theme_title"], position=row["position"],
            chapter=row["title"], avoid=avoid)

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": question},
        ],
        "max_tokens": 14000,
        "stream": False,
    }

    async with gate:
        try:
            resp = await client.post(
                API_URL, json=body,
                headers={"Authorization": f"Bearer {API_KEY}"})
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:  # réseau, 4xx, 5xx : on note et on passe
            return {"chapter": label, "file": name, "error": str(exc)[:160]}

    usage = payload.get("usage") or {}
    try:
        raw = payload["choices"][0]["message"]["content"]
        items = parse(raw)
    except Exception as exc:
        return {"chapter": label, "file": name, "usage": usage,
                "error": f"réponse illisible : {str(exc)[:120]}"}

    kept, rejected = [], []
    for item in items:
        clean, why = keep(item)
        if clean:
            kept.append(clean)
        else:
            rejected.append(why)

    if kept:
        out.mkdir(parents=True, exist_ok=True)
        # Une LISTE de lots, pas un lot : `import_exercises.py` fait
        # `for lot in lots`. Un objet seul lui donne ses propres clés à
        # itérer, et il casse sur `lot["theme_id"]`.
        path.write_text(json.dumps(
            [{"theme_id": row["theme_id"], "items": kept}],
            ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {"chapter": label, "file": name, "usage": usage,
            "kept": len(kept), "rejected": rejected,
            "article": src["article"] if src else None}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="identifiants de chapitres, séparés par des virgules")
    ap.add_argument("--theme", type=int, default=0, help="un seul thème")
    ap.add_argument("--limit", type=int, default=0, help="nombre de chapitres")
    ap.add_argument("--model", default="deepseek-chat")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--force", action="store_true", help="réécrire un fichier existant")
    ap.add_argument("--source", choices=["memoire", "wiki"], default="memoire",
                    help="wiki : n'écrire que les chapitres ayant un article")
    ap.add_argument("--out", default="", help="répertoire de sortie")
    ap.add_argument("--dry-run", action="store_true",
                    help="afficher le prompt du premier chapitre et s'arrêter")
    args = ap.parse_args()

    if not API_KEY:
        sys.exit("DEEPSEEK_API_KEY absente : ni dans l'environnement, ni dans .env")

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    only = [int(x) for x in args.only.split(",") if x.strip()]
    todo = chapters(conn, only, args.theme or None, args.limit)
    if not todo:
        sys.exit("aucun chapitre ne correspond")

    # Un bloc « déjà posé » par thème, calculé une fois : il est le même
    # pour tous les chapitres d'un thème.
    avoid = {t: already_asked(conn, t) for t in {r["theme_id"] for r in todo}}

    if args.dry_run:
        row = todo[0]
        print(SYSTEM)
        print("\n" + "─" * 70 + "\n")
        print(USER.format(theme=row["theme_title"], position=row["position"],
                          chapter=row["title"], avoid=avoid[row["theme_id"]]))
        return

    print(f"{len(todo)} chapitre(s) · modèle {args.model} · "
          f"{args.concurrency} appels en parallèle\n")

    use_wiki = args.source == "wiki"
    out = ROOT / args.out if args.out else (
        ROOT / "db" / "creation" / ("serie2-wiki" if use_wiki else "serie2"))

    gate = asyncio.Semaphore(args.concurrency)
    async with httpx.AsyncClient(timeout=300) as client:
        results = await asyncio.gather(*[
            one(client, r, avoid[r["theme_id"]], args.model, gate,
                args.force, out, use_wiki)
            for r in todo])

    kept = hit = miss = sortie = 0
    failed: list[dict] = []
    for res in results:
        if res.get("skipped"):
            print(f"  ·  {res['chapter']} — déjà écrit")
            continue
        if res.get("nosource"):
            print(f"  —  {res['chapter']} — pas d'article, laissé au filet")
            continue
        usage = res.get("usage") or {}
        hit += usage.get("prompt_cache_hit_tokens", 0)
        miss += usage.get("prompt_cache_miss_tokens", usage.get("prompt_tokens", 0))
        sortie += usage.get("completion_tokens", 0)
        if res.get("error"):
            failed.append(res)
            print(f"  ✗  {res['chapter']} — {res['error']}")
            continue
        kept += res["kept"]
        mark = "✓" if res["kept"] == 10 else "~"
        note = f" · {len(res['rejected'])} écarté(s)" if res["rejected"] else ""
        art = f"  ← {res['article']}" if res.get("article") else ""
        print(f"  {mark}  {res['chapter']} — {res['kept']} gardé(s){note}{art}")
        for why in res["rejected"]:
            print(f"         écarté : {why}")

    cost = (hit * PRICE_IN_HIT + miss * PRICE_IN_MISS + sortie * PRICE_OUT) / 1e6
    print(f"\n{kept} exercice(s) écrit(s) dans {out.relative_to(ROOT)}/")
    print(f"tokens : {hit} en cache · {miss} hors cache · {sortie} en sortie")
    print(f"coût estimé : {cost:.4f} $")
    if failed:
        print(f"{len(failed)} chapitre(s) en échec — relancer avec --only "
              "sur leurs identifiants")
    print("\nRien n'est en base. Relire, puis :")
    print(f"  python3 scripts/import_exercises.py --file "
          f"{out.relative_to(ROOT)}/<fichier> --dry-run")


if __name__ == "__main__":
    asyncio.run(main())
