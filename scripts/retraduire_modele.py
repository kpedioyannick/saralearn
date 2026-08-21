#!/usr/bin/env python3
"""Retraduit les cartes avec le modèle, qui voit la carte entière.

POURQUOI PAS GOOGLE. `deep-translator` traduit CHAMP PAR CHAMP : quand
il rend « Valves snapping shut », il n'a ni la question, ni les trois
autres options sous les yeux. Quatre mots, aucun contexte, et il choisit
le mauvais sens. Relevé sur les 261 cartes en ligne, comparées une à une
à leur original :

    Light bending through hot air  ->  « Flexion légère à travers... »
    It becomes a quarter as bright ->  « Il devient un quart PLUS brillant »
    Valves snapping shut           ->  « Les VANNES se ferment »
    the air is thinner             ->  « l'air est plus MINCE »

Vingt-cinq cartes portent un vrai défaut, huit sont injouables — leur
bonne réponse ne se reconnaît plus. Le modèle, lui, reçoit la carte
entière et traduit les options en réponses à LA question.

CE QUI N'EST PAS TRADUIT ICI, ET POURQUOI :

  · `ok_title` et `ko_title` — jeu fermé de onze formes, traduites par
    la table de `api/titres.py`. Google en avait fait « Droite ! » pour
    « Right! » sur trente-sept cartes ; une table bat un traducteur sur
    un jeu fini ;
  · `correct_index` — une POSITION dans le tableau d'options. Elle
    appartient à l'original, et l'ordre des options ne bouge pas.

Rien n'est écrit si la traduction rendue est douteuse : nombre d'options
changé, libellé vide ou trop long, deux libellés identiques. Une carte
non réécrite garde sa traduction d'avant, qui vaut mieux que rien.

    python3 scripts/retraduire_modele.py --dry-run --limite 3
    python3 scripts/retraduire_modele.py --ids 191,302,444
    python3 scripts/retraduire_modele.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.db import connection, rows, transaction  # noqa: E402
from api.llm import ask  # noqa: E402
from api.titres import traduire as titre_traduit  # noqa: E402

LANGUE = "fr"

# LA BORNE DES LIBELLÉS N'EST PAS CELLE DE L'ANGLAIS. `critic` refuse un
# libellé anglais au-delà de 60 caractères, et c'est une règle
# d'écriture : on n'écrit pas une réponse en une ligne et demie. Mais le
# français est plus long — mesuré sur les 1 044 libellés déjà en base :
# médiane 40, neuvième décile 62, maximum 86, et 116 dépassent 60 sans
# que rien ne s'en plaigne. Reprendre 60 ici faisait refuser deux
# traductions justes sur cinq, qui gardaient alors leur version cassée.
MAX_LIBELLE = 84

CONSIGNE = """Translate this exercise card into French, for a learning app
read by teenagers.

TRANSLATE THE WHOLE CARD AT ONCE. The options are answers to the
question: they must read as answers to it, and share one grammatical
form. That context is the entire point — a field-by-field translator
turned "Valves snapping shut" into "Les vannes se ferment", which is
plumbing.

Natural French, the French someone would actually write. Never
word-for-word. Keep the technical term when French uses it too.

THREE OPTIONS OUT OF FOUR ARE FALSE ON PURPOSE. Translate them
faithfully — do not fix them, do not soften them.

Hard limits:
- an option label is at most {maxi} characters, and SHORTER IS BETTER:
  aim for the length of the English one, French runs long by itself;
- keep the options in the SAME ORDER, same count;
- keep the same number of explanation steps;
- no option label may repeat another.

CARD
question: {prompt}
{body}options:
{options}
line when right: {ok_line}
line when wrong: {ko_line}
explanation title: {exp_title}
explanation: {exp_text}
explanation steps:
{steps}

Answer with JSON only, no code fence:
{{"prompt": "...", "body": null,
  "options": [{{"label": "...", "feedback": "..."}}],
  "ok_line": "...", "ko_line": "...",
  "exp_title": "...", "exp_text": "...",
  "steps": ["...", "..."]}}"""


def _json(brut: str) -> dict | None:
    debut, fin = brut.find("{"), brut.rfind("}")
    if debut < 0 or fin <= debut:
        return None
    try:
        d = json.loads(brut[debut : fin + 1])
    except Exception:  # noqa: BLE001 — un rendu illisible n'écrase rien
        return None
    return d if isinstance(d, dict) else None


def verifier(d: dict, opts_en: list, n_etapes: int) -> str | None:
    """Le mot qui fait refuser cette traduction, ou None si elle passe."""
    if not str(d.get("prompt", "")).strip():
        return "question vide"
    if not str(d.get("exp_text", "")).strip():
        return "explication vide"
    o = d.get("options")
    if not isinstance(o, list) or len(o) != len(opts_en):
        return f"{len(o) if isinstance(o, list) else '?'} options au lieu de {len(opts_en)}"
    labels = [str(x.get("label", "")).strip() for x in o if isinstance(x, dict)]
    if len(labels) != len(opts_en) or not all(labels):
        return "libellé vide"
    if any(len(x) > MAX_LIBELLE for x in labels):
        return f"libellé de plus de {MAX_LIBELLE} caractères"
    if len({x.casefold() for x in labels}) != len(labels):
        return "deux libellés identiques"
    e = d.get("steps")
    if n_etapes and (not isinstance(e, list) or len(e) != n_etapes):
        return f"{len(e) if isinstance(e, list) else '?'} étapes au lieu de {n_etapes}"
    return None


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--ids", default="", help="liste de cartes, séparées par des virgules")
    args = ap.parse_args()

    vises = {int(x) for x in args.ids.split(",") if x.strip()} if args.ids else None

    with connection() as conn:
        cartes = rows(
            conn,
            "SELECT id, prompt, body, options, correct_index, ok_title, ko_title,"
            "       ok_line, ko_line, exp_title, exp_text"
            "  FROM exercise WHERE state = 'validated' ORDER BY id",
        )
        etapes = {}
        for r in rows(conn, "SELECT exercise_id, rang, texte FROM exercise_step ORDER BY rang"):
            etapes.setdefault(r["exercise_id"], []).append(r["texte"])

    if vises:
        cartes = [c for c in cartes if c["id"] in vises]
    if args.limite:
        cartes = cartes[: args.limite]
    print(f"{len(cartes)} cartes à retraduire\n")

    ecrites = refusees = muettes = 0
    for i, c in enumerate(cartes, 1):
        opts = json.loads(c["options"])
        pas = etapes.get(c["id"], [])
        consigne = CONSIGNE.format(
            maxi=MAX_LIBELLE,
            prompt=c["prompt"],
            body=f"text shown with it: {c['body']}\n" if c["body"] else "",
            options="\n".join(
                f"{n + 1}. {o.get('label','')}  —  {o.get('feedback','')}"
                for n, o in enumerate(opts)
            ),
            ok_line=c["ok_line"] or "",
            ko_line=c["ko_line"] or "",
            exp_title=c["exp_title"] or "",
            exp_text=c["exp_text"],
            steps="\n".join(f"{n + 1}. {t}" for n, t in enumerate(pas)) or "(none)",
        )
        try:
            d = _json(await ask(consigne))
        except Exception as exc:  # noqa: BLE001 — un modèle muet ne casse rien
            print(f"  [{c['id']}] muet ({type(exc).__name__})")
            muettes += 1
            continue
        if d is None:
            print(f"  [{c['id']}] rendu illisible")
            muettes += 1
            continue

        faute = verifier(d, opts, len(pas))
        if faute:
            print(f"  [{c['id']}] REFUSÉE — {faute}")
            refusees += 1
            continue

        options = [
            {"label": str(x["label"]).strip(),
             **({"feedback": str(x.get("feedback", "")).strip()} if x.get("feedback") else {}),
             **{k: v for k, v in opts[n].items() if k in ("blank", "correct")}}
            for n, x in enumerate(d["options"])
        ]
        print(f"  [{c['id']}] {str(d['prompt'])[:72]}   ({i}/{len(cartes)})")
        print(f"        ✔ {options[c['correct_index']]['label']}")

        if args.dry_run:
            continue

        with connection() as conn:
            with transaction(conn):
                conn.execute(
                    "UPDATE exercise_translation SET prompt = ?, body = ?, options = ?,"
                    " ok_title = ?, ko_title = ?, ok_line = ?, ko_line = ?,"
                    " exp_title = ?, exp_text = ?, source = 'modele'"
                    " WHERE exercise_id = ? AND lang = ?",
                    (
                        str(d["prompt"]).strip(),
                        (str(d.get("body")).strip() if d.get("body") else None),
                        json.dumps(options, ensure_ascii=False),
                        # Les deux titres viennent de la table, jamais du modèle.
                        titre_traduit(c["ok_title"], LANGUE) or c["ok_title"],
                        titre_traduit(c["ko_title"], LANGUE) or c["ko_title"],
                        str(d.get("ok_line", "")).strip(),
                        str(d.get("ko_line", "")).strip(),
                        str(d.get("exp_title", "")).strip(),
                        str(d["exp_text"]).strip(),
                        c["id"],
                        LANGUE,
                    ),
                )
                if pas:
                    conn.execute(
                        "DELETE FROM exercise_step_translation"
                        " WHERE exercise_id = ? AND lang = ?",
                        (c["id"], LANGUE),
                    )
                    for rang, texte in enumerate(d["steps"]):
                        conn.execute(
                            "INSERT INTO exercise_step_translation"
                            " (exercise_id, rang, lang, texte) VALUES (?,?,?,?)",
                            (c["id"], rang, LANGUE, str(texte).strip()),
                        )
        ecrites += 1

    print(f"\n{ecrites} cartes réécrites, {refusees} refusées, {muettes} sans rendu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
