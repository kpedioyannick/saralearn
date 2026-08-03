#!/usr/bin/env python3
"""Génère les exercices d'un thème à partir de son Markdown.

Contrairement aux panneaux — où la bonne réponse sortait d'un catalogue
et où rien ne pouvait être inventé — ici le modèle produit la question
ET la réponse. C'est inévitable : il n'existe pas de catalogue des
accords du participe passé.

Trois filets, du plus sûr au plus tardif :

  1. validation de forme à la sortie du modèle (api/llm.py) ;
  2. passe de CRITIQUE avant insertion (api/critic.py) — des règles,
     puis un juge qui n'a ni le cours ni le contexte et à qui l'on
     demande de refuser par défaut ;
  3. le vote communautaire et la quarantaine automatique une fois en ligne.

Le deuxième est le plus utile : il coûte un appel de modèle et évite
qu'un exercice faux atteigne un élève.

    python3 scripts/generate_exercises.py --lang fr --limit 2 --dry-run
    python3 scripts/generate_exercises.py --lang fr --count 6
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.critic import review  # noqa: E402
from api.llm import GenerationError, ask, render, validate  # noqa: E402

DB = ROOT / "data" / "sara.db"

# En dessous, le « cours » n'est que le titre recopié : voir one_theme().
MIN_SOURCE = 250

# La difficulté suit le niveau de Bloom : elle n'était pas renseignée et
# valait 2 partout, ce qui rendait toute progression impossible.
DIFFICULTY = {"remember": 1, "understand": 2, "apply": 3, "analyze": 4}


async def one_theme(conn: sqlite3.Connection, theme: sqlite3.Row,
                    types: list[str], blooms: list[str], count: int,
                    dry_run: bool, no_judge: bool = False) -> tuple[int, list[str]]:
    kept, notes = 0, []
    # Le niveau vient des tags : c'est lui qu'on donne au juge pour qu'il
    # apprécie la difficulté.
    level = next((r[0] for r in conn.execute(
        "SELECT g.label FROM theme_tag tt JOIN tag g ON g.id=tt.tag_id"
        " WHERE tt.theme_id=? LIMIT 1", (theme["id"],))), "CM2")
    per_run = max(1, count // max(1, len(types) * len(blooms)))

    # Un tiers des notions n'a pour « cours » que son propre titre : la
    # base source ne contient rien de plus. Le modèle qui reçoit l'ordre
    # de ne s'appuyer que sur ce cours n'a alors qu'une matière — le
    # titre — et pose une question dessus. On le lui dit franchement :
    # la notion vient d'ici, la matière vient du programme.
    source = theme["source_markdown"] or theme["title"]
    if len(source) < MIN_SOURCE:
        source = (f"{source}\n\n(Ce cours ne donne que l'intitulé de la notion."
                  f" Tu connais le programme de {level} : c'est à toi d'écrire"
                  " les phrases, les mots et les formes sur lesquels porteront"
                  " les exercices, en restant strictement sur cette notion et"
                  " sur ce niveau.)")
        notes.append("cours réduit au titre — matière tirée du programme")

    for type_question in types:
        for bloom in blooms:
            gabarit = conn.execute(
                "SELECT * FROM prompt WHERE lang = ? AND type_question = ?"
                " AND type_bloom = ? AND is_active = 1 ORDER BY version DESC LIMIT 1",
                (theme["lang"], type_question, bloom),
            ).fetchone()
            if not gabarit:
                notes.append(f"aucun gabarit {type_question}/{bloom} en {theme['lang']}")
                continue

            tags = ", ".join(
                r[0] for r in conn.execute(
                    "SELECT g.label FROM theme_tag tt JOIN tag g ON g.id = tt.tag_id"
                    " WHERE tt.theme_id = ?", (theme["id"],))
            )
            prompt = render(
                gabarit["template"], title=theme["title"], tags=tags or "aucun",
                count=per_run, source=source,
            )

            if dry_run:
                notes.append(f"{type_question}/{bloom} — prompt de {len(prompt)} caractères")
                continue

            cur = conn.execute(
                "INSERT INTO exercise_prompt (theme_id, prompt_id, rendered_prompt,"
                " model, requested_count, status) VALUES (?, ?, ?, 'deepseek', ?, 'running')",
                (theme["id"], gabarit["id"], prompt, per_run),
            )
            run_id = cur.lastrowid
            conn.commit()

            try:
                raw = await ask(prompt)
                items = validate(raw, type_question)
                if not items:
                    raise GenerationError("aucun exercice exploitable")
            except Exception as exc:  # noqa: BLE001 — on trace tout
                conn.execute(
                    "UPDATE exercise_prompt SET status='failed', error=?,"
                    " finished_at=datetime('now') WHERE id=?",
                    (str(exc)[:500], run_id))
                conn.commit()
                notes.append(f"{type_question}/{bloom} : {str(exc)[:70]}")
                continue

            # Passe de critique : chaque exercice est jugé avant d'entrer.
            # Les règles écartent d'abord ce qui se voit (renvoi au
            # support, options en double, énoncé trop long), puis un juge
            # qui n'a ni le cours ni le contexte tranche le reste.
            accepted, rejected = [], []
            for item in items:
                verdict = await review(item, theme["lang"], level,
                                       with_judge=not no_judge, kind=type_question)
                (accepted if verdict.ok else rejected).append((item, verdict))

            for reason in rejected[:3]:
                notes.append(f"rejeté : {reason[1].reasons[0][:64]}")
            if rejected:
                notes.append(f"{len(rejected)}/{len(items)} écartés par la critique")

            for item, _ in accepted:
                conn.execute(
                    "INSERT INTO exercise (theme_id, exercise_prompt_id, type_question,"
                    " type_bloom, prompt, body, options, correct_index, ok_title, ok_line,"
                    " ko_title, ko_line, exp_title, exp_text, exp_tip,"
                    " difficulty, state)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'validated')",
                    (theme["id"], run_id, type_question, bloom, item["prompt"],
                     item["body"], json.dumps(item["options"], ensure_ascii=False),
                     item["correct_index"], item["ok_title"], item["ok_line"],
                     item["ko_title"], item["ko_line"], item["exp_title"],
                     item["exp_text"], item["exp_tip"],
                     DIFFICULTY.get(bloom, 2)),
                )
            conn.execute(
                "UPDATE exercise_prompt SET status='done', produced_count=?,"
                " error=?, finished_at=datetime('now') WHERE id=?",
                (len(accepted),
                 f"{len(rejected)} écarté(s) par la critique" if rejected else None,
                 run_id))
            conn.commit()
            kept += len(accepted)

    conn.execute(
        "UPDATE theme SET exercise_count ="
        " (SELECT COUNT(*) FROM exercise WHERE theme_id=? AND state='validated')"
        " WHERE id=?", (theme["id"], theme["id"]))
    conn.commit()
    return kept, notes


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["fr", "en"], required=True)
    ap.add_argument("--types", default="qcm,complete,find_error")
    ap.add_argument("--blooms", default="remember,understand,apply")
    ap.add_argument("--count", type=int, default=6, help="exercices visés par thème")
    ap.add_argument("--limit", type=int, default=0, help="nombre de thèmes")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-judge", action="store_true",
                    help="garde les règles, saute le second avis du modèle")
    args = ap.parse_args()

    conn = sqlite3.connect(DB, timeout=120)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 120000")

    # On ne régénère pas ce qui a déjà des exercices : le script est
    # relançable, et une génération coûte du temps de modèle.
    themes = conn.execute(
        "SELECT t.* FROM theme t"
        " JOIN category c ON c.id = t.category_id"
        " WHERE t.lang = ? AND c.lang IS NOT NULL"
        "   AND t.source_markdown IS NOT NULL"
        "   AND (SELECT COUNT(*) FROM exercise e WHERE e.theme_id = t.id) = 0"
        " ORDER BY t.id", (args.lang,),
    ).fetchall()
    if args.limit:
        themes = themes[: args.limit]

    print(f"{len(themes)} thème(s) sans exercice en {args.lang}\n")
    total = 0
    for i, theme in enumerate(themes, 1):
        kept, notes = await one_theme(
            conn, theme, args.types.split(","), args.blooms.split(","),
            args.count, args.dry_run, args.no_judge)
        total += kept
        print(f"  [{i}/{len(themes)}] {theme['title'][:48]:50s} {kept:3d} exercices")
        for n in notes[:2]:
            print(f"        · {n}")

    print(f"\n{total} exercice(s) créé(s)")
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
