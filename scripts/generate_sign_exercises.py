#!/usr/bin/env python3
"""Fabrique des exercices de reconnaissance de panneaux.

Le point important : **aucun modèle de langue n'intervient dans la
réponse**. Pour « que signifie ce panneau ? », la bonne réponse EST le
libellé officiel du panneau, et les distracteurs sont les libellés
d'autres panneaux de la même famille. Tout sort du catalogue.

Il n'y a donc rien à halluciner. La justesse ne repose pas sur la
qualité d'une génération, elle est vraie par construction :

  · l'image vient de `sign.image_path`
  · la bonne réponse vient de `sign.name` — la MÊME ligne
  · `exercise.sign_id` pointe sur cette ligne

Le modèle ne sert qu'à l'explication, et seulement quand on la demande —
une explication maladroite donne un exercice moyen, jamais un exercice
faux.

    python3 scripts/generate_sign_exercises.py --country US --theme-id 7
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import unicodedata
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.critic import check_rules  # noqa: E402

DB = ROOT / "data" / "sara.db"

WORDING = {
    "fr": {
        "prompt": "Que signifie ce panneau ?",
        "ok_title": "C'est ça.",
        "ok_line": "Tu l'as reconnu du premier coup.",
        "ko_title": "Presque.",
        "ko_line": "Celui-là se confond facilement avec ses voisins.",
        "exp_title": lambda n: n,
        "exp_text": lambda n, f: (
            f"Les panneaux de la famille {f} partagent une forme et une couleur :"
            " c'est ce qu'on reconnaît en premier, avant même de lire le"
            " pictogramme. Repère d'abord la famille, le sens vient ensuite."),
        "exp_tip": lambda n: f"Famille reconnue, moitié du chemin faite.",
    },
    "en": {
        "prompt": "What does this sign mean?",
        "ok_title": "That's it.",
        "ok_line": "Recognised at first glance.",
        "ko_title": "So close.",
        "ko_line": "This one is easily confused with its neighbours.",
        "exp_title": lambda n: n,
        "exp_text": lambda n, f: (
            f"Signs in the {f} family share a shape and a colour: that is what"
            " you recognise first, before reading the pictogram. Spot the"
            " family, and the meaning follows."),
        "exp_tip": lambda n: "Recognise the family, and you are halfway there.",
    },
}


def normalise(text: str) -> str:
    """Pour comparer des libellés sans se faire piéger par la casse ou les accents."""
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


def build(conn: sqlite3.Connection, country: str, theme_id: int, lang: str,
          limit: int, seed: int) -> tuple[int, list[str]]:
    rng = random.Random(seed)
    w = WORDING[lang]

    # Deux états ouvrent la porte, et ils ne disent pas la même chose :
    #   'verified'  — un humain a confirmé l'appariement code ↔ image
    #   'community' — personne ne l'a regardé ; c'est le vote des
    #                 utilisateurs qui fait le tri, avec la quarantaine
    #                 automatique comme filet.
    # 'imported' reste hors circuit dans les deux cas.
    signs = [
        dict(r)
        for r in conn.execute(
            "SELECT id, code, family, name, image_path, image_alt FROM sign"
            " WHERE country = ? AND review_state IN ('verified','community')"
            "   AND image_path IS NOT NULL AND TRIM(name) != ''"
            # Les plaques (suffixe P) ne sont pas des panneaux autonomes :
            # elles complètent celui du dessus. « Que signifie ce panneau ? »
            # n'a pas de sens sur une plaque isolée.
            "   AND code NOT LIKE '%P'"
            # Un libellé d'un seul mot court est le texte imprimé sur la
            # plaque, pas une signification : « Only », « End », « Ice ».
            # Borne haute autant que basse : un libellé plus long que
            # l'option le ferait tronquer en plein mot — « must use tur ».
            # Mieux vaut pas d'exercice qu'une réponse mutilée.
            "   AND length(name) BETWEEN 12 AND 60"
            "   AND instr(TRIM(name), ' ') > 0",
            (country,),
        )
    ]
    if not signs:
        return 0, [f"aucun panneau relu pour {country} — rien à générer"]

    by_family: dict[str, list[dict]] = {}
    for s in signs:
        by_family.setdefault(s["family"] or "?", []).append(s)

    kept, skipped = 0, []
    rng.shuffle(signs)

    for sign in signs[:limit] if limit else signs:
        family = sign["family"] or "?"
        pool = [
            s for s in by_family.get(family, [])
            if s["id"] != sign["id"] and normalise(s["name"]) != normalise(sign["name"])
        ]
        # Un distracteur doit être plausible : on le prend dans la même
        # famille. Moins de trois, et le QCM n'a plus de sens — on passe
        # plutôt que de compléter avec du remplissage.
        if len(pool) < 3:
            skipped.append(f"{sign['code']}: moins de 3 voisins dans la famille {family}")
            continue

        distractors = rng.sample(pool, 3)
        options = [{"label": d["name"]} for d in distractors]
        correct = rng.randrange(4)
        options.insert(correct, {"label": sign["name"]})

        # Garde-fou : deux libellés identiques rendraient la bonne
        # réponse indécidable. Ça ne devrait pas arriver après le
        # filtrage, mais on ne publie pas un exercice ambigu.
        if len({normalise(o["label"]) for o in options}) != 4:
            skipped.append(f"{sign['code']}: libellés en double après tirage")
            continue

        item = {
            "prompt": w["prompt"], "body": None, "options": options,
            "correct_index": correct,
            "exp_text": w["exp_text"](sign["name"], family)[:600],
        }
        # Le contrôle valait pour les exercices écrits par un modèle ; il
        # vaut tout autant ici. C'est son absence qui a laissé passer
        # « Accès interdit aux véhicules dont la largeur, chargement ».
        verdict = check_rules(item, kind="qcm")
        if not verdict.ok:
            skipped.append(f"{sign['code']}: {verdict.reasons[0]}")
            continue

        conn.execute(
            "INSERT INTO exercise (theme_id, sign_id, type_question, type_bloom,"
            " prompt, options, correct_index, ok_title, ok_line, ko_title, ko_line,"
            " exp_title, exp_text, exp_tip, state)"
            " VALUES (?,?,'qcm','remember',?,?,?,?,?,?,?,?,?,?,'validated')",
            (
                theme_id, sign["id"], w["prompt"],
                json.dumps(options, ensure_ascii=False), correct,
                w["ok_title"], w["ok_line"], w["ko_title"], w["ko_line"],
                w["exp_title"](sign["name"])[:160],
                w["exp_text"](sign["name"], family)[:600],
                w["exp_tip"](sign["name"])[:240],
            ),
        )
        kept += 1

    conn.commit()
    conn.execute(
        "UPDATE theme SET exercise_count ="
        " (SELECT COUNT(*) FROM exercise WHERE theme_id = ? AND state = 'validated')"
        " WHERE id = ?", (theme_id, theme_id))
    conn.commit()
    return kept, skipped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", choices=["FR", "US"], required=True)
    ap.add_argument("--theme-id", type=int, required=True)
    ap.add_argument("--lang", choices=["fr", "en"], required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=1, help="tirage reproductible")
    args = ap.parse_args()

    conn = sqlite3.connect(DB, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")

    kept, skipped = build(conn, args.country, args.theme_id, args.lang,
                          args.limit, args.seed)
    print(f"{kept} exercice(s) créé(s)")
    if skipped:
        print(f"{len(skipped)} panneau(x) écarté(s) :")
        for s in skipped[:10]:
            print("  ·", s)
        if len(skipped) > 10:
            print(f"  … et {len(skipped) - 10} autres")
    conn.close()


if __name__ == "__main__":
    main()
