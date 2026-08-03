#!/usr/bin/env python3
"""Importe des exercices rédigés à la main, en passant par la critique.

`generate_exercises.py` demande les exercices à un modèle distant. Ce
script-ci prend un fichier JSON déjà écrit — par un humain, ou par le
modèle qui tient cette session — et le fait entrer par la même porte :
`api.critic.check_rules` d'abord, insertion ensuite.

Le juge (second avis d'un modèle) n'est pas appelé ici : quand l'auteur
et le juge sont le même, un juge n'ajoute rien. Ce qui protège, ce sont
les règles — qui, elles, ne se laissent pas convaincre — puis le vote de
la communauté une fois en ligne.

Format attendu :

    [{"theme_id": 149,
      "items": [{"type_question": "complete", "type_bloom": "remember",
                 "prompt": "…", "body": null, "correct_index": 0,
                 "options": [{"label": "…", "feedback": "…"}],
                 "ok_title": "…", "ok_line": "…",
                 "ko_title": "…", "ko_line": "…",
                 "exp_title": "…", "exp_text": "…", "exp_tip": "…"}]}]

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
DIFFICULTY = {"remember": 1, "understand": 2, "apply": 3, "analyze": 4}

# Écrit dans `exercise_prompt.model` : on doit pouvoir retrouver plus tard
# d'où vient chaque exercice, y compris ceux qui n'ont pas été générés.
AUTHOR = "claude-opus-5 (rédaction directe)"

# `exercise_prompt.prompt_id` ne peut pas être vide. Plutôt que de faire
# pointer ces exercices vers un gabarit qui ne les a pas produits — ce
# qui serait faux —, on déclare un gabarit inactif « sans gabarit » par
# langue. La traçabilité reste exacte : on saura toujours que ces
# exercices ont été écrits, pas générés.
NO_TEMPLATE = ("Rédaction directe — sans gabarit",
               "Exercices écrits à la main, entrés par api/critic.py."
               " Ce gabarit n'est jamais rendu ni envoyé à un modèle.")


def no_template_id(conn: sqlite3.Connection, lang: str) -> int:
    row = conn.execute("SELECT id FROM prompt WHERE lang=? AND label=?",
                       (lang, NO_TEMPLATE[0])).fetchone()
    if row:
        return row["id"]
    return conn.execute(
        # version 999 : la contrainte d'unicité porte sur
        # (lang, type_question, type_bloom, version) et toutes les vraies
        # versions sont basses. Rien ne risque de la percuter.
        "INSERT INTO prompt (lang, type_question, type_bloom, version, is_active,"
        " label, template) VALUES (?, 'qcm', 'remember', 999, 0, ?, ?)",
        (lang, *NO_TEMPLATE)).lastrowid


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
        theme = conn.execute("SELECT id, title, lang FROM theme WHERE id = ?",
                             (lot["theme_id"],)).fetchone()
        if not theme:
            print(f"  thème {lot['theme_id']} introuvable — lot ignoré")
            continue

        accepted, rejected = [], []
        for item in lot["items"]:
            verdict = check_rules(item, kind=item.get("type_question"))
            (accepted if verdict.ok else rejected).append((item, verdict))

        print(f"  {theme['title'][:46]:48s} {len(accepted):2d} gardé(s)"
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
            "INSERT INTO exercise_prompt (theme_id, prompt_id, rendered_prompt,"
            " model, requested_count, produced_count, status, finished_at)"
            " VALUES (?, ?, ?, ?, ?, ?, 'done', datetime('now'))",
            (theme["id"], no_template_id(conn, theme["lang"]),
             f"Rédaction directe — {theme['title']}", AUTHOR,
             len(lot["items"]), len(accepted)),
        ).lastrowid

        for item, _ in accepted:
            conn.execute(
                "INSERT INTO exercise (theme_id, exercise_prompt_id, type_question,"
                " type_bloom, prompt, body, options, correct_index, ok_title, ok_line,"
                " ko_title, ko_line, exp_title, exp_text, exp_tip, difficulty, state)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'validated')",
                (theme["id"], run, item["type_question"], item["type_bloom"],
                 item["prompt"], item.get("body"),
                 json.dumps(item["options"], ensure_ascii=False),
                 item["correct_index"], item["ok_title"], item["ok_line"],
                 item["ko_title"], item["ko_line"], item["exp_title"],
                 item["exp_text"], item["exp_tip"],
                 DIFFICULTY.get(item["type_bloom"], 2)),
            )
        conn.execute(
            "UPDATE theme SET exercise_count = (SELECT COUNT(*) FROM exercise"
            " WHERE theme_id = ? AND state = 'validated') WHERE id = ?",
            (theme["id"], theme["id"]))
        conn.commit()

    print(f"\n{total_ok} exercice(s) {'à importer' if args.dry_run else 'importé(s)'}"
          f" · {total_ko} écarté(s) par les règles")
    conn.close()


if __name__ == "__main__":
    main()
