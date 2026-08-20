#!/usr/bin/env python3
"""Donne un code de partage aux apprentissages qui n'en ont pas.

    python3 scripts/remplir_codes.py            # montre, n'écrit rien
    python3 scripts/remplir_codes.py --ecrire   # écrit

POURQUOI CE SCRIPT EXISTE. La migration 009 a ajouté la colonne `code`
et son index unique, et son commentaire annonce « une connaissance créée
avant cette migration en reçoit un par le remplissage ci-dessous » — mais
ce remplissage n'a jamais été écrit. Les apprentissages antérieurs, et
ceux créés depuis par les chemins qui oubliaient la colonne, sont restés
sans code : pas de lien à donner, et le script vidéo les écarte.

Les trois chemins de création ont été corrigés en même temps que ce
script (`api/routers/knowledge.py`, `scripts/import_tech.py`,
`scripts/import_fr_notions.py`). Celui-ci ne sert donc qu'une fois — mais
il est rejouable sans risque : il ne touche QUE les lignes à NULL, et ne
réécrit jamais un code déjà distribué.

PAS PAR LE CLI SQLITE. Le client en ligne de commande poursuit après une
erreur : une contrainte violée au milieu d'un lot passerait inaperçue et
la moitié du travail serait faite. Ici, tout est dans une transaction —
ou tout passe, ou rien.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.codes import unique_code  # noqa: E402

DB = Path(os.environ.get("SARA_DB", ROOT / "data" / "sara.db"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ecrire", action="store_true",
                    help="écrit vraiment ; sans lui, on ne fait que montrer")
    ap.add_argument("--db", default=str(DB))
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    manquants = conn.execute(
        "SELECT t.id, t.title, t.lang, t.visibility, c.slug AS categorie"
        " FROM theme t JOIN category c ON c.id = t.category_id"
        " WHERE t.code IS NULL ORDER BY t.lang, t.title"
    ).fetchall()

    total = conn.execute("SELECT COUNT(*) FROM theme").fetchone()[0]
    print(f"{len(manquants)} apprentissage(s) sans code, sur {total}.\n")
    if not manquants:
        return

    # Les codes sont tirés AVANT d'écrire, et vérifiés entre eux : dans une
    # même transaction, `unique_code` ne voit pas les codes que la boucle
    # vient d'insérer si rien n'est encore validé, et deux lignes du lot
    # pourraient repartir avec le même tirage.
    attribues: dict[int, str] = {}
    pris: set[str] = set()
    for t in manquants:
        for _ in range(12):
            code = unique_code(conn)
            if code not in pris:
                break
        else:
            sys.exit("Impossible de tirer assez de codes libres.")
        pris.add(code)
        attribues[t["id"]] = code
        print(f"  {code}  {t['lang']}  {t['visibility']:8s} {t['categorie']:16s} "
              f"{t['title'][:52]}")

    if not args.ecrire:
        print("\nRien écrit. Relance avec --ecrire.")
        return

    try:
        with conn:  # transaction : tout ou rien
            for theme_id, code in attribues.items():
                # `code IS NULL` dans le WHERE, et pas seulement dans la
                # sélection : entre la lecture et l'écriture, l'API a pu
                # en poser un. On ne remplace jamais un code existant.
                conn.execute(
                    "UPDATE theme SET code = ? WHERE id = ? AND code IS NULL",
                    (code, theme_id),
                )
    except sqlite3.IntegrityError as exc:
        sys.exit(f"Écriture annulée, rien n'a changé : {exc}")

    restants = conn.execute("SELECT COUNT(*) FROM theme WHERE code IS NULL").fetchone()[0]
    print(f"\n{len(attribues)} code(s) posé(s). Reste sans code : {restants}.")


if __name__ == "__main__":
    main()
