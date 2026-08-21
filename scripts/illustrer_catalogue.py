#!/usr/bin/env python3
"""Donne sa photo d'ambiance à chaque exercice déjà écrit.

Deux temps, et le second est lent pour une raison qui n'est pas la nôtre :

  1. LES MOTS. Le modèle lit la question et rend deux à quatre mots
     décrivant la SCÈNE — « hot empty road ». Par lots de dix questions,
     un appel par lot : c'est quelques centimes pour tout le catalogue.
  2. LA PHOTO. Une requête Unsplash par exercice. **Cinquante par heure**
     tant que l'application est en mode démo, cinq mille une fois
     approuvée. C'est ce plafond, et lui seul, qui fait durer l'affaire.

Les deux temps sont séparés exprès : les mots, une fois écrits, restent
en base (`exercise.image_query`). On peut donc relancer la seconde phase
autant de fois que le quota le permet sans jamais redemander au modèle.

Le filtre de `photos.revele` s'applique entre les deux : une requête qui
nomme le phénomène est effacée, et l'exercice reste sans photo. C'est
voulu — pas de photo est le cas normal, une photo qui donne la réponse
coûte l'exercice.

    python3 scripts/illustrer_catalogue.py --mots
    python3 scripts/illustrer_catalogue.py --photos
    python3 scripts/illustrer_catalogue.py --photos --boucle
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.db import connection, rows, transaction  # noqa: E402
from api.llm import ask  # noqa: E402
from api.photos import (  # noqa: E402
    PAR_HEURE,
    illustrer,
    illustrer_etape,
    oublier_le_quota,
    prochaine_reprise,
    quota_epuise,
    restant,
    revele,
)

LOT = 10

CONSIGNE = """For each question below, give the words to type into a PHOTO
library to find a photograph that SETS THE SCENE the question puts the
learner in front of.

Two hard rules:
  - name the PLACE, the OBJECT or the ANIMAL that would be in the frame.
    Two to four ordinary words: "hot empty road", "glass of water straw",
    "geese flying formation".
  - NEVER name the phenomenon, the mechanism or the answer. Not
    "refraction", not "mirage", not "light bending", not "diagram". The
    photo sets the scene, it never shows why.
  Return "" for any question with nothing a camera could photograph — a
  sound, an idea, a number.

QUESTIONS
{liste}

Reply with a JSON object ONLY: {{"queries": ["...", "..."]}} — exactly
{n} entries, in the same order."""


async def ecrire_les_mots() -> int:
    with connection() as conn:
        attente = rows(
            conn,
            "SELECT id, prompt FROM exercise"
            " WHERE state = 'validated' AND image_query IS NULL AND image_url IS NULL"
            " ORDER BY id",
        )
    if not attente:
        print("Toutes les cartes ont déjà leurs mots.")
        return 0
    print(f"{len(attente)} cartes sans mots, par lots de {LOT}")
    ecrits = 0
    for depart in range(0, len(attente), LOT):
        lot = attente[depart : depart + LOT]
        liste = "\n".join(f"{i + 1}. {c['prompt']}" for i, c in enumerate(lot))
        try:
            raw = await ask(CONSIGNE.format(liste=liste, n=len(lot)))
            queries = json.loads(raw[raw.index("{") : raw.rindex("}") + 1])["queries"]
        except Exception as exc:  # noqa: BLE001
            print(f"  lot {depart // LOT + 1} : échec ({str(exc)[:60]})")
            continue
        if len(queries) != len(lot):
            print(f"  lot {depart // LOT + 1} : {len(queries)} réponses pour {len(lot)} questions")
            continue
        with connection() as conn:
            with transaction(conn):
                for c, q in zip(lot, queries):
                    q = str(q or "").strip()[:120]
                    if q:
                        conn.execute(
                            "UPDATE exercise SET image_query = ? WHERE id = ?", (q, c["id"])
                        )
                        ecrits += 1
        print(f"  lot {depart // LOT + 1}/{(len(attente) - 1) // LOT + 1} : {ecrits} mots posés")
    return ecrits


# Le sommeil du veilleur quand le catalogue est à jour. Court, parce
# qu'il attend une écriture et non un quota.
VEILLE = 600


async def poser_les_photos(boucle: bool) -> int:
    total = 0
    while True:
        # LA FILE NE TIENT PLUS QUE LES PHOTOS DE CARTES. Les images
        # d'étapes ont été coupées le 21/08/2026 : ce que les banques
        # rendaient pour une étape était du décor, jamais le mécanisme,
        # et l'explication garde désormais la photo de la question.
        # Le raisonnement complet est dans `topup.ecrire_et_traduire`.
        #
        # `illustrer_etape` reste importée et vivante : elle attend des
        # gabarits dessinés, qui eux seront exacts.
        with connection() as conn:
            reste = [
                ("carte", r["id"], None)
                for r in rows(
                    conn,
                    "SELECT id FROM exercise WHERE state = 'validated'"
                    "   AND image_query IS NOT NULL AND image_url IS NULL ORDER BY id",
                )
            ]
        if not reste:
            if not boucle:
                print("Plus rien à illustrer.")
                return total
            # EN BOUCLE, « plus rien » N'EST PAS UNE FIN. C'est même
            # l'état normal du catalogue entre deux écritures, et rendre
            # la main ici faisait sortir le veilleur au bout de la
            # première ronde — pm2 le relançait alors sans cesse.
            #
            # L'attente est courte, sans rapport avec celle du quota :
            # ce qu'on guette n'est pas le renouvellement des requêtes
            # mais l'arrivée d'un lot fraîchement écrit. La chaîne
            # d'écriture illustre déjà ce qu'elle produit ; ce veilleur
            # ne ramasse que ce qu'elle a manqué — coupure réseau,
            # banques à sec sur le moment, API relancée en plein travail.
            print(f"Plus rien à illustrer — nouvelle ronde dans {VEILLE // 60} min.")
            time.sleep(VEILLE)
            oublier_le_quota()
            continue
        # Avant le premier appel on ne sait rien : on dimensionne sur le
        # plafond connu. Ensuite c'est Unsplash qui dit ce qu'il reste,
        # et la boucle s'arrête sur lui.
        place = PAR_HEURE if restant() is None else restant()
        print(f"{len(reste)} cartes en attente, {place} requêtes disponibles cette heure")
        if place == 0 and not boucle:
            return total
        pose = refuse = 0
        for sorte, eid, rang in reste[:place]:
            if quota_epuise():
                print("  quota atteint en cours de ronde")
                break
            fait = (
                await illustrer(eid) if sorte == "carte"
                else await illustrer_etape(eid, rang)
            )
            if fait:
                pose += 1
            else:
                refuse += 1
        total += pose
        print(f"  {pose} photos posées, {refuse} sans suite (requête refusée, ou rien trouvé)")
        if not boucle:
            return total

        # UNE RONDE QUI A PRODUIT NE DORT PAS UNE HEURE. Elle repart au
        # haut de la boucle, qui relit ce qui reste : s'il ne reste rien
        # — le cas normal — c'est la veille courte qui prend, et un lot
        # écrit dans la minute est illustré dans les dix.
        #
        # On ne dort longtemps que sur les deux vraies impasses : plus
        # de quota nulle part, ou une ronde entière sans une seule photo
        # posée. La seconde compte autant que la première : des cartes
        # dont AUCUNE banque ne rend rien resteraient sinon en boucle
        # serrée, à rappeler trois APIs toutes les secondes pour la même
        # réponse vide.
        if pose == 0 or quota_epuise():
            # L'ATTENTE SUIT LA BANQUE QUI SE ROUVRE LE PLUS TÔT, et non
            # l'heure d'Unsplash. Pixabay compte à la MINUTE : dormir
            # une heure parce qu'il est à sec, c'est laisser dormir six
            # mille requêtes. Le 20/08/2026, 348 images d'étapes en
            # attente annonçaient quatre heures pour cette seule raison.
            attente = prochaine_reprise()
            print(f"  rien à en tirer pour l'instant — reprise dans {attente} s")
            time.sleep(attente)
            # Le compteur d'AVANT l'attente ne vaut plus rien, et le
            # garder bloque tout : une ronde dimensionnée sur zéro ne
            # fait aucun appel, et sans appel l'en-tête ne se relit
            # jamais. On repart sur « inconnu », donc sur le plafond,
            # donc sur un vrai appel qui dira la vérité.
            oublier_le_quota()


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mots", action="store_true", help="phase 1 : le modèle écrit les requêtes")
    ap.add_argument("--photos", action="store_true", help="phase 2 : Unsplash rend les images")
    ap.add_argument("--boucle", action="store_true", help="attendre le quota et continuer")
    args = ap.parse_args()
    if not (args.mots or args.photos):
        ap.error("choisir --mots, --photos, ou les deux")

    if args.mots:
        n = await ecrire_les_mots()
        print(f"\n{n} requêtes écrites.\n")
        # Ce que le filtre écartera, dit AVANT de dépenser du quota.
        with connection() as conn:
            cartes = rows(
                conn,
                "SELECT id, prompt, image_query, options, correct_index, exp_title, exp_text"
                "  FROM exercise WHERE state = 'validated' AND image_query IS NOT NULL",
            )
        fautives = [(c, revele(c["image_query"], c)) for c in cartes]
        fautives = [(c, m) for c, m in fautives if m]
        print(f"{len(fautives)} requêtes nomment le phénomène et seront refusées :")
        for c, m in fautives[:12]:
            print(f"  [{c['id']}] {c['image_query']!r} — mot fautif : {m}")

    if args.photos:
        n = await poser_les_photos(args.boucle)
        print(f"\n{n} photos posées.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
