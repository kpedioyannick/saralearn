#!/usr/bin/env python3
"""Rattrape les exercices validés qui n'ont pas leur traduction.

L'écriture emporte désormais sa traduction (`topup.ecrire_et_traduire`),
donc ce script ne sert qu'au retard accumulé — 35 exercices au 19/08,
laissés en anglais par les coupures de Google des 17 et 18/08, quand un
seul morceau raté jetait le chapitre entier sans reprise.

Il passe par le MÊME chemin que l'API : `traduire_exercice`, un exercice
à la fois, avec ses reprises et son verrou. Rien de parallèle — c'est
justement le parallélisme qui faisait couper Google.

    python3 scripts/traduire_manquants.py --dry-run
    python3 scripts/traduire_manquants.py
    python3 scripts/traduire_manquants.py --lang fr --limit 20
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.db import connection, rows  # noqa: E402
from api.traduction import LANGUES_CACHE, traduire_exercice  # noqa: E402


def manquants(lang: str, limit: int) -> list[dict]:
    """Les validés sans version, chapitre le plus fourni en tête.

    L'ordre par chapitre n'est pas cosmétique : traduire un chapitre en
    entier le rend lisible, alors que trente exercices pris au hasard sur
    trente chapitres ne rendent aucun chapitre lisible.
    """
    with connection() as conn:
        return rows(
            conn,
            "SELECT e.id, e.chapter_id, ch.title, substr(e.prompt, 1, 60) AS debut"
            "  FROM exercise e JOIN chapter ch ON ch.id = e.chapter_id"
            " WHERE e.state = 'validated'"
            "   AND NOT EXISTS (SELECT 1 FROM exercise_translation t"
            "                    WHERE t.exercise_id = e.id AND t.lang = ?)"
            " ORDER BY e.chapter_id, e.id LIMIT ?",
            (lang, limit),
        )


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default=LANGUES_CACHE[0], choices=list(LANGUES_CACHE))
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    reste = manquants(args.lang, args.limit)
    if not reste:
        print(f"Rien à traduire en {args.lang}.")
        return 0

    par_chapitre: dict[int, str] = {}
    for e in reste:
        par_chapitre.setdefault(e["chapter_id"], e["title"])
    print(f"{len(reste)} exercices sans version {args.lang}, "
          f"sur {len(par_chapitre)} chapitres :")
    for cid, titre in par_chapitre.items():
        n = sum(1 for e in reste if e["chapter_id"] == cid)
        print(f"  {cid:>5}  {titre[:50]:<50} {n}")
    # Une quinzaine d'appels par exercice, un peu moins d'une seconde
    # chacun : de quoi savoir si on part pour dix minutes ou pour deux
    # heures avant de lancer.
    print(f"\n≈ {len(reste) * 9 // 60} min. Verrou global : rien en parallèle.")
    if args.dry_run:
        return 0

    ecrits, refuses = 0, []
    for i, e in enumerate(reste, 1):
        ok = await traduire_exercice(e["id"], args.lang)
        if ok:
            ecrits += 1
        else:
            refuses.append(e)
        print(f"  [{i}/{len(reste)}] {e['id']:>4} {'✓' if ok else '✗'} {e['debut']}")

    print(f"\n{ecrits} traduits, {len(refuses)} laissés en anglais.")
    if refuses:
        # Un refus n'est pas forcément une panne : `verifier()` écarte les
        # traductions cassées dans leur forme — deux options devenues
        # identiques, un « ? » perdu. Celles-là resteront en anglais quoi
        # qu'on fasse, et c'est le bon comportement.
        print("Relancer le script réessaiera ceux que le réseau a fait tomber.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
