#!/usr/bin/env python3
"""Importe des exercices rédigés à la main, en passant par la critique.

Il prend un fichier JSON déjà écrit — par un humain, ou par le modèle qui
tient cette session — et le fait entrer par la porte des règles :
`api.critic.check_rules` d'abord, insertion ensuite. C'est le seul chemin
d'entrée qui reste hors de l'API.

Le juge (second avis d'un modèle) n'est pas appelé ici : quand l'auteur
et le juge sont le même, un juge n'ajoute rien. Ce qui protège, ce sont
les règles — qui, elles, ne se laissent pas convaincre — puis le vote de
la communauté une fois en ligne.

Format attendu — un lot par CHAPITRE, jamais par thème : depuis la
migration 019, un lancement pend à son chapitre et le thème s'en déduit.

    [{"chapter_id": 106,
      "items": [{"type_question": "qcm",
                 "prompt": "…", "body": null, "correct_index": 0,
                 "options": [{"label": "…", "feedback": "…"}],
                 "ok_title": "…", "ok_line": "…",
                 "ko_title": "…", "ko_line": "…",
                 "exp_title": "…", "exp_text": "…"}]}]

    python3 scripts/import_exercises.py --file lot.json --dry-run
    python3 scripts/import_exercises.py --file lot.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.critic import check_rules  # noqa: E402

DB = ROOT / "data" / "sara.db"

# Écrit dans `exercise_prompt.model` : on doit pouvoir retrouver plus tard
# d'où vient chaque exercice, y compris ceux qui n'ont pas été générés.
AUTHOR = "claude-opus-5 (rédaction directe)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    lots = json.loads(Path(args.file).read_text(encoding="utf-8"))

    conn = sqlite3.connect(DB, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")

    total_ok = total_ko = 0

    for lot in lots:
        # Le chapitre porte le thème : on lit les deux d'un coup, et un
        # chapitre introuvable arrête le lot plutôt que de créer un
        # lancement orphelin — `chapter_id` est NOT NULL depuis la 019.
        cible = conn.execute(
            "SELECT ch.id AS chapter_id, ch.title AS chapter_title,"
            "       t.id AS theme_id, t.title, t.lang"
            "  FROM chapter ch JOIN theme t ON t.id = ch.theme_id"
            " WHERE ch.id = ?", (lot["chapter_id"],)).fetchone()
        if not cible:
            print(f"  chapitre {lot['chapter_id']} introuvable — lot ignoré")
            continue
        theme = cible

        accepted, rejected = [], []
        for item in lot["items"]:
            verdict = check_rules(item, kind=item.get("type_question"))
            (accepted if verdict.ok else rejected).append((item, verdict))

        print(f"  {cible['chapter_title'][:46]:48s} {len(accepted):2d} gardé(s)"
              f"{f' · {len(rejected)} écarté(s)' if rejected else ''}")
        for item, verdict in rejected:
            print(f"      ✗ {item['prompt'][:44]:46s} {verdict.reasons[0]}")

        total_ok += len(accepted)
        total_ko += len(rejected)
        if args.dry_run or not accepted:
            continue

        # Une ligne de traçabilité par lot, comme pour une génération :
        # sans elle, on ne saurait plus distinguer ces exercices des autres.
        run = conn.execute(
            "INSERT INTO exercise_prompt (chapter_id, rendered_prompt,"
            " model, requested_count, produced_count, status, finished_at)"
            " VALUES (?, ?, ?, ?, ?, 'done', datetime('now'))",
            (cible["chapter_id"],
             f"Rédaction directe — {theme['title']} · {cible['chapter_title']}",
             AUTHOR, len(lot["items"]), len(accepted)),
        ).lastrowid

        for item, _ in accepted:
            conn.execute(
                "INSERT INTO exercise (theme_id, exercise_prompt_id, type_question,"
                " prompt, body, options, correct_index, ok_title, ok_line,"
                " ko_title, ko_line, exp_title, exp_text, state)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'validated')",
                (cible["theme_id"], run, item["type_question"],
                 item["prompt"], item.get("body"),
                 json.dumps(item["options"], ensure_ascii=False),
                 item["correct_index"], item["ok_title"], item["ok_line"],
                 item["ko_title"], item["ko_line"], item["exp_title"],
                 item["exp_text"]),
            )
        conn.execute(
            "UPDATE theme SET exercise_count = (SELECT COUNT(*) FROM exercise"
            " WHERE theme_id = ? AND state = 'validated') WHERE id = ?",
            (cible["theme_id"], cible["theme_id"]))
        conn.commit()

    print(f"\n{total_ok} exercice(s) {'à importer' if args.dry_run else 'importé(s)'}"
          f" · {total_ko} écarté(s) par les règles")
    conn.close()


if __name__ == "__main__":
    main()
