#!/usr/bin/env python3
"""Donner une source à chaque chapitre : l'article Wikipédia qui en parle.

Le catalogue a été écrit de mémoire, sans source consultée — c'est sa
faiblesse connue, et elle a produit au moins une erreur nette (DeepSeek
affirmant que les araignées ont deux antennes, quand le catalogue lui-
même enseigne qu'elles n'en ont aucune). Un modèle qui lit un texte ne
se trompe pas comme un modèle qui se souvient.

LE CHOIX DE L'ARTICLE N'EST PAS UN CLASSEMENT, C'EST UN JUGEMENT. La
recherche par mots se trompe systématiquement : « The distances of the
universe » remonte *List of He-Man and the Masters of the Universe
characters*, « Records of rain and snow » remonte une chanson, et
ajouter le nom du thème empire les choses — « Ferns » seul rend *Fern*,
« Ferns · The Quiet Ones of the Soil » rend *Cortegada Island*. La
recherche propose donc, et un modèle choisit, AVEC LE DROIT DE DIRE
« aucun ». Un chapitre sans article vaut mieux qu'un chapitre adossé au
mauvais.

Wikipédia coupe à HTTP 429 si on tape trop vite ou sans se présenter :
en-tête `User-Agent` descriptif, trois appels en parallèle au plus,
et on repasse après une pause.

    python3 scripts/wikipedia_source.py            # les 196 chapitres
    python3 scripts/wikipedia_source.py --only 80,148

Le résultat va dans `db/creation/wiki/<id>.json` — titre retenu, URL, et
le texte brut plafonné. Rien d'autre n'est touché : ni la base, ni les
exercices. C'est `generate_deepseek.py --source wiki` qui s'en sert.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB = ROOT / "data" / "sara.db"
OUT = ROOT / "db" / "creation" / "wiki"

WIKI = "https://en.wikipedia.org/w/api.php"
# Wikipédia demande qu'on se présente, et rend 429 aux anonymes pressés.
AGENT = ("saralearn/1.0 (https://learn.sara.education; "
         "yannick.kpedio@gmail.com)")

# Au-delà, on paie des tokens pour l'histoire de la discipline et les
# références bibliographiques. Les faits de base sont en tête d'article.
MAX_CHARS = 9000


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

PICK = """A school chapter needs a source article. Below are candidate \
Wikipedia articles found by keyword search — keyword search is \
unreliable, so several of them are probably about something else \
entirely.

Chapter: {chapter}
It belongs to a theme called: {theme}

Candidates:
{candidates}

Read each candidate's OPENING SENTENCE before anything else. It states \
what the article is actually about, and it overrules the title \
completely.

Disqualify a candidate outright — no matter how well its title matches \
— if its opening sentence says it is a song, a ballad, an album, a \
band, a film, a novel, a poem, a game, a TV series, a company, a \
person, a place, a ship, or a work of art. A title matching by accident \
is the normal case here, not the exception.

Then pick the article whose subject IS the chapter's subject. A broad \
article on the right subject is a good source — the chapter only needs \
solid ground, not an exact title match.

WHEN TWO CANDIDATES ARE BOTH ON THE SUBJECT, TAKE THE BROADER ONE. The \
chapter covers a whole topic, so a general survey article beats a \
narrow one about a single part or a single species. For a chapter on \
insect anatomy, "Insect morphology" is the right source and "Gaster \
(insect anatomy)" is the wrong one — the second is about one body \
segment of one order.

Answer none when no candidate is on the chapter's subject at all. Do \
not settle for the closest of a bad set: a chapter with no source is \
better than a chapter with the wrong one.

Answer with JSON only: {{"pick": "<exact article title>", "subject": \
"<what that article is about, in five words>"}} or {{"pick": null}}."""


async def _wiki(client: httpx.AsyncClient, params: dict) -> dict:
    """Un appel à l'API, avec patience sur le 429."""
    params = {**params, "format": "json", "formatversion": "2"}
    for attempt in range(4):
        resp = await client.get(WIKI, params=params,
                                headers={"User-Agent": AGENT})
        if resp.status_code == 429:
            await asyncio.sleep(2 ** attempt * 3)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("Wikipédia refuse toujours après quatre essais (429)")


# Un filet déterministe AVANT le modèle. Il ne juge pas la pertinence —
# il retire ce qui ne peut pas être une source : une chanson, un film,
# un groupe. « Records of rain and snow » a rendu *Rain and Snow*, une
# ballade folk, et le modèle l'a choisie alors qu'il lisait « is an
# American folksong ». Une expression régulière, elle, ne se laisse pas
# attendrir.
HORS_SUJET = re.compile(
    r"\b(?:is|was|are|were)\s+(?:an?\s+|the\s+)?(?:\w+\s+){0,3}?"
    # `\w*song` et non `song` : l'article piège s'ouvrait sur « is an
    # American folksong », que `\bsong\b` laissait passer.
    r"(?:\w*song|ballad|album|single|band|film|movie|novel|poem|play|opera|"
    r"video game|game|manga|comic|TV series|television series|sitcom|"
    r"episode|footballer|actor|actress|singer|musician|politician|"
    r"painter|writer|company|brand|ship|locomotive|municipality|village|"
    r"town|commune|racehorse)\b", re.I)


def _nu(text: str) -> str:
    """Titre réduit à son os : minuscules, sans article, au singulier."""
    t = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    t = re.sub(r"^(the|a|an)\s+", "", t.strip())
    t = re.sub(r"\s+", " ", t).strip()
    return t[:-1] if t.endswith("s") and not t.endswith("ss") else t


def evident(chapter: str, cands: list[dict]) -> str | None:
    """Le rattrapage sans modèle.

    « Ferns » et l'article *Fern* sont le même mot ; le modèle a pourtant
    répondu « aucun » une fois sur deux. Quand un candidat porte
    exactement le titre du chapitre, au pluriel et à l'article près, on
    ne demande l'avis de personne.
    """
    cible = _nu(chapter)
    for c in cands:
        if _nu(c["title"]) == cible:
            return c["title"]
    return None


def suspect(cand: dict) -> bool:
    tete = (cand["description"] + ". " + cand["extract"])[:400]
    return bool(HORS_SUJET.search(tete))


# Les titres de chapitres sont des phrases, pas des mots-clés : « Why
# clouds stay up », « Telling the main cloud types apart ». La recherche
# les prend au pied de la lettre et rate *Cloud*. On lui donne donc
# aussi les mots pleins, une fois le décor retiré.
VIDES = {"the", "a", "an", "of", "and", "or", "in", "on", "to", "for",
         "is", "are", "was", "were", "does", "do", "did", "why", "how",
         "what", "when", "where", "which", "that", "this", "it", "its",
         "up", "out", "apart", "own", "your", "you", "we", "our", "main",
         "telling", "finding", "exist", "exists", "some", "other",
         "others", "things", "living", "great", "way", "ways"}


def mots_pleins(titre: str) -> str:
    mots = [m for m in re.findall(r"[A-Za-z]+", titre)
            if m.lower() not in VIDES]
    return " ".join(mots)


async def candidates(client: httpx.AsyncClient, chapter: str,
                     theme: str) -> list[dict]:
    """Les articles proposés, avec de quoi juger sur pièce.

    Deux recherches — le chapitre seul, puis chapitre et thème — parce
    qu'aucune des deux n'est fiable seule : le thème sauve les titres
    vagues et perd les titres précis.
    """
    seen: dict[str, dict] = {}
    requetes = [chapter, f"{chapter} {theme}"]
    reduit = mots_pleins(chapter)
    if reduit and reduit.lower() != chapter.lower():
        requetes.append(reduit)
    for query in requetes:
        data = await _wiki(client, {
            "action": "query", "generator": "search",
            "gsrsearch": query, "gsrlimit": "5",
            "prop": "extracts|description",
            "exintro": "1", "explaintext": "1", "exsentences": "2",
        })
        for page in (data.get("query", {}) or {}).get("pages", []) or []:
            title = page.get("title")
            if title and title not in seen:
                seen[title] = {
                    "title": title,
                    "description": page.get("description") or "",
                    "extract": (page.get("extract") or "").strip(),
                }
    return list(seen.values())


async def pick(client: httpx.AsyncClient, chapter: str, theme: str,
               cands: list[dict]) -> str | None:
    lignes = []
    for i, c in enumerate(cands, 1):
        titre = c["title"]
        if c["description"]:
            titre += " — " + c["description"]
        lignes.append(f"{i}. {titre}\n   {c['extract'][:300]}")
    listing = "\n".join(lignes)
    resp = await client.post(API_URL, json={
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": PICK.format(
            chapter=chapter, theme=theme, candidates=listing)}],
        "max_tokens": 200, "stream": False,
    }, headers={"Authorization": f"Bearer {API_KEY}"})
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]
    start = raw.find("{")
    if start == -1:
        return None
    data, _ = json.JSONDecoder().raw_decode(raw[start:])
    chosen = data.get("pick")
    if not chosen:
        return None
    # Le modèle doit citer un titre proposé, pas en inventer un.
    titles = {c["title"] for c in cands}
    return chosen if chosen in titles else None


async def fetch(client: httpx.AsyncClient, title: str) -> tuple[str, str]:
    data = await _wiki(client, {
        "action": "query", "titles": title,
        "prop": "extracts|info", "explaintext": "1", "inprop": "url",
    })
    pages = (data.get("query", {}) or {}).get("pages", []) or []
    if not pages:
        return "", ""
    page = pages[0]
    return (page.get("extract") or "")[:MAX_CHARS], page.get("fullurl", "")


async def one(client: httpx.AsyncClient, row: sqlite3.Row,
              gate: asyncio.Semaphore, force: bool) -> dict:
    path = OUT / f"{row['id']}.json"
    label = f"{row['theme_title']} · {row['title']}"
    if path.exists() and not force:
        return {"label": label, "skipped": True}

    async with gate:
        try:
            bruts = await candidates(client, row["title"], row["theme_title"])
            cands = [c for c in bruts if not suspect(c)]
            ecartes = len(bruts) - len(cands)
            if not cands:
                return {"label": label, "article": None,
                        "why": f"aucun candidat ({ecartes} hors sujet écarté(s))"}
            # Le rattrapage d'abord, mais il n'a pas le dernier mot : un
            # titre identique attrape aussi les pages d'homonymie et les
            # films (« Smell », « The Touch », « Cold Blood »). Si
            # l'article est famélique, on rend la main au modèle en le
            # privant de ce candidat-là.
            chosen = evident(row["title"], cands)
            text, url = await fetch(client, chosen) if chosen else ("", "")
            if len(text) < 2500:
                restants = [c for c in cands if c["title"] != chosen]
                autre = await pick(client, row["title"], row["theme_title"],
                                   restants) if restants else None
                if autre:
                    texte2, url2 = await fetch(client, autre)
                    if len(texte2) > len(text):
                        chosen, text, url = autre, texte2, url2
            if not chosen:
                return {"label": label, "article": None,
                        "why": f"{len(cands)} candidats, aucun ne convient"}
        except Exception as exc:
            return {"label": label, "error": str(exc)[:140]}

    if len(text) < 2500:
        return {"label": label, "article": None,
                "why": f"« {chosen} » trop court pour servir de source ({len(text)} car.)"}

    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "chapter_id": row["id"], "chapter": row["title"],
        "theme": row["theme_title"], "article": chosen, "url": url,
        "chars": len(text), "text": text,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"label": label, "article": chosen, "chars": len(text)}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=3,
                    help="Wikipédia rend 429 au-delà de quelques appels")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--missing", action="store_true",
                    help="seulement les chapitres encore sans source")
    args = ap.parse_args()

    if not API_KEY:
        sys.exit("DEEPSEEK_API_KEY absente")

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    sql = ("SELECT ch.id, ch.title, t.title AS theme_title"
           " FROM chapter ch JOIN theme t ON t.id = ch.theme_id"
           " WHERE t.lang = 'en'")
    params: list = []
    only = [int(x) for x in args.only.split(",") if x.strip()]
    if only:
        sql += f" AND ch.id IN ({','.join('?' * len(only))})"
        params += only
    sql += " ORDER BY ch.theme_id, ch.position"
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"
    todo = list(conn.execute(sql, params))
    if args.missing:
        todo = [r for r in todo if not (OUT / f"{r['id']}.json").exists()]

    print(f"{len(todo)} chapitre(s) · {args.concurrency} appels en parallèle\n")
    gate = asyncio.Semaphore(args.concurrency)
    async with httpx.AsyncClient(timeout=90) as client:
        results = await asyncio.gather(*[one(client, r, gate, args.force)
                                         for r in todo])

    ok = sans = 0
    for res in results:
        if res.get("skipped"):
            continue
        if res.get("error"):
            sans += 1
            print(f"  ✗  {res['label']} — {res['error']}")
        elif res.get("article"):
            ok += 1
            print(f"  ✓  {res['label']}  →  {res['article']} "
                  f"({res['chars']} car.)")
        else:
            sans += 1
            print(f"  —  {res['label']} — {res['why']}")

    print(f"\n{ok} chapitre(s) avec source · {sans} sans")
    print(f"écrit dans {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    asyncio.run(main())
