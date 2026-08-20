#!/usr/bin/env python3
"""Ramène `ok_title` et `ko_title` au jeu fermé de `api/titres.py`.

Les cartes écrites avant la liste portent soixante-dix formes de titre de
réussite pour cent soixante-treize cartes, et leur traduction française
est parfois fausse — « Droite ! » pour « Right! », « Fermer » pour
« Close ». Voir la note en tête de `api/titres.py`.

Ce script fait les deux langues d'un coup, SANS AUCUN APPEL RÉSEAU :
l'anglais est rattaché à la liste par `canoniser`, le français en est
déduit par la table. Pas de modèle, pas de traducteur, rien à attendre.

Ce qui n'accroche aucun motif — « Bouncer! », « Space kitchen » — se
répartit sur la liste par le numéro de la carte. Ces titres-là ne
veulent rien dire de précis, et les voir varier vaut mieux que les voir
tous devenir « Exact. ».

    python3 scripts/normaliser_titres.py --dry-run
    python3 scripts/normaliser_titres.py
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.db import connection, rows, transaction  # noqa: E402
from api.titres import canoniser, traduire  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lang", default="fr")
    args = ap.parse_args()

    with connection() as conn:
        cartes = rows(
            conn,
            "SELECT id, ok_title, ko_title FROM exercise WHERE state = 'validated'"
            " ORDER BY id",
        )
        traductions = {
            r["exercise_id"]: r
            for r in rows(
                conn,
                "SELECT exercise_id, ok_title, ko_title FROM exercise_translation"
                " WHERE lang = ?",
                (args.lang,),
            )
        }

    maj_en: list[tuple] = []
    maj_fr: list[tuple] = []
    change = Counter()
    for c in cartes:
        ok = canoniser(c["ok_title"] or "", True, c["id"])
        ko = canoniser(c["ko_title"] or "", False, c["id"])
        if ok != c["ok_title"] or ko != c["ko_title"]:
            maj_en.append((ok, ko, c["id"]))
            change[(c["ok_title"], ok)] += 1
            change[(c["ko_title"], ko)] += 1
        t = traductions.get(c["id"])
        if t is None:
            continue
        ok_fr, ko_fr = traduire(ok, args.lang), traduire(ko, args.lang)
        if ok_fr and ko_fr and (ok_fr != t["ok_title"] or ko_fr != t["ko_title"]):
            maj_fr.append((ok_fr, ko_fr, c["id"], args.lang))

    print(f"{len(cartes)} cartes en ligne")
    print(f"  {len(maj_en)} titres anglais à ramener dans la liste")
    print(f"  {len(maj_fr)} traductions à refaire depuis la table\n")
    print("les remplacements les plus fréquents :")
    for (avant, apres), n in change.most_common(12):
        if avant != apres:
            print(f"  {n:>3}  {avant!r:<28} → {apres!r}")

    if args.dry_run:
        return 0

    with connection() as conn:
        with transaction(conn):
            if maj_en:
                conn.executemany(
                    "UPDATE exercise SET ok_title = ?, ko_title = ? WHERE id = ?",
                    maj_en,
                )
            if maj_fr:
                conn.executemany(
                    "UPDATE exercise_translation SET ok_title = ?, ko_title = ?"
                    " WHERE exercise_id = ? AND lang = ?",
                    maj_fr,
                )
    print(f"\n{len(maj_en)} cartes et {len(maj_fr)} traductions remises d'aplomb.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
