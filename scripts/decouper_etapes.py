#!/usr/bin/env python3
"""Donne leurs étapes — et le titre de leur image — aux cartes déjà en ligne.

Les 261 exercices écrits avant le contrat des étapes n'ont qu'un
`exp_text` d'un bloc. Ce script fait trois choses, dans cet ordre :

  1. il DÉCOUPE l'explication, avec la règle exacte de `llm._decouper` —
     les lignes d'abord, les phrases ensuite. Pas de modèle ici : le
     découpage doit être le même que celui du front, sinon les étapes ne
     tomberaient pas là où l'élève les lisait ;
  2. il DEMANDE AU MODÈLE le titre de l'image de chaque étape, une carte
     par appel, en lui donnant la question et sa réponse pour qu'il sache
     de quoi la leçon parle. Sur l'écran d'explication la réponse est
     déjà donnée : le titre PEUT nommer le mécanisme, et il doit rester
     dans le monde de la leçon ;
  3. il RECOPIE la traduction française quand elle se découpe en autant
     de morceaux — c'est le cas de 247 cartes sur 261 —, sans un appel
     au traducteur. Les autres restent sans traduction d'étape : le
     chemin normal (`traduction._traduire_les_etapes`) les prendra.

Il est IDEMPOTENT : une carte qui a déjà ses étapes est sautée. Relancer
ne coûte rien et ne réécrit rien.

    python3 scripts/decouper_etapes.py --dry-run
    python3 scripts/decouper_etapes.py --limite 5      # essai sur cinq cartes
    python3 scripts/decouper_etapes.py
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

from api.db import connection, rows, scalar, transaction  # noqa: E402
from api.llm import _decouper  # noqa: E402
from api.llm import ask  # noqa: E402

LANGUE = "fr"

CONSIGNE = """You name the picture to fetch for each step of an explanation.

The learner has ALREADY answered this question and already knows the
answer. The picture may therefore show the mechanism — that is the whole
point of these pictures.

Question: {prompt}
Answer: {answer}

Steps:
{etapes}

For each step, give THE TITLE OF THE PICTURE TO GO AND FIND: name the
thing to be shown, the way a photograph is named. Three to six words, no
sentence, English only.

Stay inside the world of the lesson — the heart, an artery, a pulse;
water, a glass, light. NEVER the comparison the step uses to explain: a
step saying "like a car whose wheels hit mud" must not ask for a car.
Never generic scenery either.

Give "" when the step states a relation nothing can show ("light travels
faster in air than in water") or denies something ("it is not the blood
moving by itself"). An empty title is the right answer there: that step
will keep the picture of the step before it.

Answer with a JSON array of strings, one per step, in order. Nothing
else, no code fence.
"""


def _tableau(brut: str, n: int) -> list[str]:
    """Le tableau de titres rendu par le modèle, ramené à n entrées."""
    texte = brut.strip()
    debut, fin = texte.find("["), texte.rfind("]")
    if debut < 0 or fin <= debut:
        return []
    try:
        data = json.loads(texte[debut : fin + 1])
    except Exception:  # noqa: BLE001 — un rendu illisible vaut pas de titre
        return []
    if not isinstance(data, list):
        return []
    titres = [str(x or "").strip()[:120] for x in data]
    return (titres + [""] * n)[:n]


def _phrases(texte: str) -> list[str]:
    lignes = [x.strip(" -–•*\t") for x in re.split(r"\r?\n+", texte or "") if x.strip()]
    if len(lignes) > 1:
        return lignes
    phrases = [x.strip() for x in re.findall(r"[^.!?]+[.!?]*", texte or "") if x.strip()]
    return phrases if len(phrases) > 1 else [texte]


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limite", type=int, default=0, help="n'en traiter que N")
    args = ap.parse_args()

    with connection() as conn:
        cartes = rows(
            conn,
            "SELECT e.id, e.prompt, e.options, e.correct_index, e.exp_text,"
            "       t.exp_text AS exp_fr"
            "  FROM exercise e"
            "  LEFT JOIN exercise_translation t"
            "    ON t.exercise_id = e.id AND t.lang = ?"
            " WHERE e.state = 'validated'"
            "   AND NOT EXISTS (SELECT 1 FROM exercise_step s WHERE s.exercise_id = e.id)"
            " ORDER BY e.id",
            (LANGUE,),
        )

    if args.limite:
        cartes = cartes[: args.limite]

    deja = 0
    with connection() as conn:
        deja = scalar(conn, "SELECT COUNT(DISTINCT exercise_id) FROM exercise_step") or 0

    print(f"{len(cartes)} cartes sans étapes ({deja} en ont déjà)")
    if not cartes:
        return 0

    posees = titres_vides = trads = 0
    for i, c in enumerate(cartes, 1):
        etapes = _decouper(c["exp_text"])
        options = json.loads(c["options"])
        reponse = options[c["correct_index"]]
        reponse = reponse["label"] if isinstance(reponse, dict) else reponse

        titres: list[str] = []
        try:
            brut = await ask(
                CONSIGNE.format(
                    prompt=c["prompt"],
                    answer=reponse,
                    etapes="\n".join(f"{n + 1}. {t}" for n, t in enumerate(etapes)),
                )
            )
            titres = _tableau(brut, len(etapes))
        except Exception as exc:  # noqa: BLE001 — un modèle muet ne bloque rien
            print(f"  [{c['id']}] pas de titres ({type(exc).__name__})")

        if not titres:
            titres = [""] * len(etapes)
        titres_vides += sum(1 for t in titres if not t)

        # Le français, gratuitement, quand il se découpe pareil.
        fr = _phrases(c["exp_fr"]) if c["exp_fr"] else []
        aligne = len(fr) == len(etapes)

        print(f"  [{c['id']}] {len(etapes)} étapes"
              f" · {sum(1 for t in titres if t)} titres"
              f" · fr {'aligné' if aligne else 'à traduire'}"
              f"   ({i}/{len(cartes)})")
        for n, (t, ti) in enumerate(zip(etapes, titres)):
            print(f"        {n + 1}. « {ti or '—'} »  {t[:64]}")

        if args.dry_run:
            continue

        with connection() as conn:
            with transaction(conn):
                for n, (texte, titre) in enumerate(zip(etapes, titres)):
                    conn.execute(
                        "INSERT OR IGNORE INTO exercise_step"
                        " (exercise_id, rang, texte, image_title) VALUES (?,?,?,?)",
                        (c["id"], n, texte, titre or None),
                    )
                    posees += 1
                if aligne:
                    for n, texte in enumerate(fr):
                        conn.execute(
                            "INSERT OR IGNORE INTO exercise_step_translation"
                            " (exercise_id, rang, lang, texte) VALUES (?,?,?,?)",
                            (c["id"], n, LANGUE, texte),
                        )
                        trads += 1

    if args.dry_run:
        print("\n(--dry-run : rien n'est écrit)")
        return 0

    print(f"\n{posees} étapes posées, {trads} traduites, {titres_vides} sans titre d'image.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
