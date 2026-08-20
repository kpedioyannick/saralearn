#!/usr/bin/env python3
"""Répartit la bonne réponse sur les quatre positions du QCM.

LE DÉFAUT MESURÉ : sur 261 exercices en ligne, la bonne réponse est en
position 1 ou 2 dans 223 d'entre eux, et en position 4 dans cinq. Le
modèle écrit la bonne réponse d'abord et invente les fausses ensuite —
l'ordre du fichier suit l'ordre de sa pensée. Un élève qui joue les deux
premières cases gagne sans lire, et le taux de réussite mesuré ne veut
plus rien dire.

CE QUE FAIT LE MÉLANGE, ET CE QU'IL NE CASSE PAS :

  · `correct_index` est une position dans le tableau d'options : il est
    recalculé, jamais recopié ;
  · la traduction porte SON PROPRE tableau d'options (table
    `exercise_translation`), dans le même ordre que l'anglais. La MÊME
    permutation lui est appliquée, sinon le français désignerait une
    autre case que l'anglais pour un exercice qui n'a qu'un identifiant ;
  · `attempt.chosen_index` garde la trace de ce qu'un élève a touché.
    Les lignes déjà enregistrées sont repositionnées elles aussi, sans
    quoi elles désigneraient après coup une option qu'il n'a pas
    choisie. `is_correct` ne bouge pas : il était vrai, il reste vrai.

IL EST IDEMPOTENT, et c'est voulu — un script de rattrapage se relance.
La position visée est tirée du NUMÉRO de la carte : au second passage,
la bonne réponse y est déjà, la permutation devient l'identité et rien
ne bouge. Un mélange au hasard, lui, aurait redistribué à chaque appel.

    python3 scripts/melanger_options.py --dry-run
    python3 scripts/melanger_options.py
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.db import connection, rows, transaction  # noqa: E402

# Change la graine et TOUT le catalogue se redistribue. Elle est écrite
# ici plutôt que tirée au sort pour que deux exécutions, sur deux
# machines, donnent le même catalogue.
GRAINE = 20260820


def permutation(exercise_id: int, correct: int, n: int) -> list[int]:
    """Les anciennes positions, dans leur nouvel ordre.

    `p[nouvelle] = ancienne`. La bonne réponse va à la place que lui
    donne son numéro de carte ; les autres se referment derrière elle
    en gardant leur ordre relatif — une option n'a pas de raison de
    doubler sa voisine, et le modèle les a écrites du plus au moins
    plausible.
    """
    cible = random.Random(GRAINE + exercise_id).randrange(n)
    autres = [i for i in range(n) if i != correct]
    p: list[int] = []
    for place in range(n):
        p.append(correct if place == cible else autres.pop(0))
    return p


def appliquer(tableau: list, p: list[int]) -> list:
    return [tableau[ancienne] for ancienne in p]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    avant, apres = Counter(), Counter()
    touches = trads = essais = 0
    refus: list[str] = []

    with connection() as conn:
        cartes = rows(
            conn,
            "SELECT id, options, correct_index FROM exercise"
            " WHERE state = 'validated' AND type_question = 'qcm'"
            " ORDER BY id",
        )
        print(f"{len(cartes)} QCM en ligne")

        plan = []
        for c in cartes:
            options = json.loads(c["options"])
            n = len(options)
            correct = c["correct_index"]
            avant[correct] += 1

            # Une carte cassée n'est pas réparée ici : on la signale et
            # on la laisse telle quelle. Ce script mélange, il ne juge pas.
            if n < 2 or not (0 <= correct < n):
                refus.append(f"  [{c['id']}] {n} options, correct_index={correct}")
                apres[correct] += 1
                continue

            p = permutation(c["id"], correct, n)
            nouveau = p.index(correct)
            apres[nouveau] += 1

            # `place[ancienne] = nouvelle` — l'inverse de `p`, pour les
            # réponses déjà enregistrées.
            place = {ancienne: nouvelle for nouvelle, ancienne in enumerate(p)}
            plan.append((c["id"], appliquer(options, p), nouveau, place, n))

        print(f"  {len(plan)} cartes mélangées, {len(refus)} laissées de côté")
        if refus:
            print("\ncartes laissées de côté :")
            print("\n".join(refus))

        print("\nposition de la bonne réponse :")
        for i in range(4):
            print(f"  {i + 1} : {avant[i]:4} → {apres[i]:4}")

        if args.dry_run:
            print("\n(--dry-run : rien n'est écrit)")
            return 0

        with transaction(conn):
            for eid, options, correct, place, n in plan:
                conn.execute(
                    "UPDATE exercise SET options = ?, correct_index = ? WHERE id = ?",
                    (json.dumps(options, ensure_ascii=False), correct, eid),
                )
                touches += 1

                for t in rows(
                    conn,
                    "SELECT lang, options FROM exercise_translation WHERE exercise_id = ?",
                    (eid,),
                ):
                    trad = json.loads(t["options"])
                    # Une traduction qui n'a pas le même nombre d'options
                    # que sa source ne peut pas suivre la permutation :
                    # on la laisse, elle sera refaite par le traducteur.
                    if len(trad) != n:
                        refus.append(f"  [{eid}/{t['lang']}] {len(trad)} options contre {n}")
                        continue
                    # `place` est l'inverse de `p` : on reconstruit `p`
                    # pour réordonner, pas pour repositionner.
                    p = [0] * n
                    for ancienne, nouvelle in place.items():
                        p[nouvelle] = ancienne
                    conn.execute(
                        "UPDATE exercise_translation SET options = ?"
                        " WHERE exercise_id = ? AND lang = ?",
                        (json.dumps(appliquer(trad, p), ensure_ascii=False), eid, t["lang"]),
                    )
                    trads += 1

                for a in rows(
                    conn,
                    "SELECT id, chosen_index FROM attempt"
                    " WHERE exercise_id = ? AND chosen_index IS NOT NULL",
                    (eid,),
                ):
                    nouvelle = place.get(a["chosen_index"])
                    if nouvelle is None:
                        continue
                    conn.execute(
                        "UPDATE attempt SET chosen_index = ? WHERE id = ?",
                        (nouvelle, a["id"]),
                    )
                    essais += 1

    print(f"\n{touches} exercices, {trads} traductions et {essais} réponses repositionnés.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
