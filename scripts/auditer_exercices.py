#!/usr/bin/env python3
"""Fait répondre le modèle aux cartes, à froid, et compte les désaccords.

Le juge de `critic.py` relit un exercice AVANT qu'il n'entre : il dit s'il
est défendable. Ce script fait autre chose, et de plus dur — il JOUE la
carte, exactement comme un élève : la question, les quatre options, rien
d'autre. Pas l'article, pas la bonne réponse, pas l'explication.

Une carte à laquelle un lecteur compétent ne tombe pas juste est cassée,
peu importe pourquoi. Deux causes attendues, et le test ne les distingue
pas — c'est le dépouillement qui le fera :

  · DEUX OPTIONS VRAIES. Le défaut né de la consigne d'intuition du
    19/08 : à force de rendre les mauvaises options plausibles, deux
    peuvent devenir défendables. Vu sur les oies en V, où « attraper la
    poussée de l'oiseau devant » et « rester dans le sillage et réduire
    la traînée » sont le même mécanisme dit deux fois. Celui-là marque
    faux quelqu'un qui a bien raisonné, et c'est le pire défaut possible
    pour une app qui vise l'intuition.
  · UNE TRADUCTION QUI A DÉPLACÉ LE SENS. `verifier()` ne regarde que la
    forme. Le français est donc testé SÉPARÉMENT de l'anglais : une
    carte juste en anglais et fausse en français accuse le traducteur,
    pas l'auteur.

On demande aussi combien d'options le modèle trouve défendables. C'est ce
chiffre qui sépare « je me suis trompé » de « la question n'a pas de
réponse unique ».

    python3 scripts/auditer_exercices.py --dry-run
    python3 scripts/auditer_exercices.py --lang en
    python3 scripts/auditer_exercices.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.db import connection, rows  # noqa: E402
from api.llm import ask  # noqa: E402

# Quatre de front. `ask` sort sur le réseau : les enchaîner une par une
# ferait durer l'audit une demi-heure pour rien. Quatre et pas vingt,
# parce que le fournisseur limite le débit et qu'un refus ferait
# compter une carte comme cassée alors qu'elle ne l'est pas.
PARALLELE = 4

QUESTION = """You are answering one multiple-choice question, alone on a screen.
You have no lesson and no other help. Answer as an attentive learner would.

QUESTION
{prompt}

OPTIONS
{options}

Reply with a JSON object ONLY:
{{"choix": <index of the option you pick, 0-based>,
  "ex_aequo": [<indices of options AS correct as your pick, or []>],
  "motif": "one short sentence"}}

"ex_aequo" is narrow on purpose, and you must not pad it. Put an index
there ONLY when that option is just as correct as the one you picked —
the same mechanism said in other words, or a second answer that is
equally true. An option that is merely plausible, or partly true, or a
common misconception, DOES NOT BELONG THERE. If your pick is the best
answer, "ex_aequo" is empty. Empty is the normal case."""


def a_jouer(lang: str, limit: int, chapitres: list[int] | None = None) -> list[dict]:
    """Les cartes en ligne, dans la langue demandée.

    En français, on lit la traduction et non l'original — c'est elle qui
    est servie, c'est donc elle qu'il faut éprouver. `correct_index`
    vient toujours de `exercise` : une position dans le tableau
    d'options n'appartient pas à la traduction.
    """
    filtre, params = "", []
    if chapitres:
        filtre = f" AND e.chapter_id IN ({','.join('?' * len(chapitres))})"
        params = list(chapitres)
    with connection() as conn:
        if lang == "en":
            return rows(
                conn,
                "SELECT e.id, e.prompt, e.options, e.correct_index, ch.title AS chapitre"
                "  FROM exercise e JOIN chapter ch ON ch.id = e.chapter_id"
                " WHERE e.state = 'validated'" + filtre + " ORDER BY e.id LIMIT ?",
                (*params, limit),
            )
        return rows(
            conn,
            "SELECT e.id, t.prompt, t.options, e.correct_index, ch.title AS chapitre"
            "  FROM exercise e JOIN chapter ch ON ch.id = e.chapter_id"
            "  JOIN exercise_translation t ON t.exercise_id = e.id AND t.lang = ?"
            " WHERE e.state = 'validated'" + filtre + " ORDER BY e.id LIMIT ?",
            (lang, *params, limit),
        )


async def jouer(carte: dict) -> dict | None:
    options = json.loads(carte["options"])
    prompt = QUESTION.format(
        prompt=carte["prompt"],
        options="\n".join(f"  {i}. {o.get('label','')}" for i, o in enumerate(options)),
    )
    try:
        raw = await ask(prompt)
    except Exception:  # noqa: BLE001 — un appel tombé n'accuse pas la carte
        return None
    for start in (m.start() for m in re.finditer(r"\{", raw)):
        try:
            data, _ = json.JSONDecoder().raw_decode(raw[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "choix" in data:
            return data
    return None


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="both", choices=["en", "fr", "both"])
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--chapter", type=int, action="append",
                    help="n'auditer que ces chapitres — pour vérifier une"
                         " réécriture sans rejouer les 165 cartes")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    langues = ["en", "fr"] if args.lang == "both" else [args.lang]
    for lang in langues:
        cartes = a_jouer(lang, args.limit, args.chapter)
        print(f"\n=== {lang.upper()} — {len(cartes)} cartes")
        if args.dry_run:
            continue

        verrou = asyncio.Semaphore(PARALLELE)

        async def une(c):
            async with verrou:
                return c, await jouer(c)

        resultats = await asyncio.gather(*(une(c) for c in cartes))

        rates, ambigus, muets = [], [], 0
        for c, r in resultats:
            if r is None:
                muets += 1
                continue
            # DEUX COMPTES, ET LE PREMIER EST CELUI QUI DÉCIDE : un
            # lecteur compétent tombe-t-il sur la bonne réponse ? Le
            # second dit pourquoi il a manqué — parce que la carte a
            # deux réponses, ou parce qu'elle en a une autre.
            if r.get("choix") != c["correct_index"]:
                rates.append((c, r))
            if [d for d in (r.get("ex_aequo") or []) if isinstance(d, int)]:
                ambigus.append((c, r))

        joues = len(cartes) - muets
        print(f"  {joues} jouées, {muets} sans réponse du modèle")
        print(f"  RÉPONSE MANQUÉE : {len(rates)}"
              f" ({100 * len(rates) // max(joues, 1)} %)   <- le chiffre qui décide")
        print(f"  DEUX RÉPONSES AUSSI JUSTES : {len(ambigus)}"
              f" ({100 * len(ambigus) // max(joues, 1)} %)")

        for c, r in ambigus:
            opts = json.loads(c["options"])
            tenues = [opts[i].get("label", "") for i in r["ex_aequo"]
                      if 0 <= i < len(opts)]
            print(f"\n  · [{c['id']}] {c['chapitre']} — {c['prompt'][:80]}")
            print(f"      ex aequo : {' / '.join(tenues)}")
            print(f"      bonne réponse annoncée : {opts[c['correct_index']].get('label','')}")
        for c, r in rates:
            opts = json.loads(c["options"])
            choisi = r["choix"]
            print(f"\n  ! [{c['id']}] {c['chapitre']} — {c['prompt'][:80]}")
            print(f"      il répond : {opts[choisi].get('label','') if 0 <= choisi < len(opts) else choisi}")
            print(f"      attendu   : {opts[c['correct_index']].get('label','')}")
            print(f"      motif     : {(r.get('motif') or '')[:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
