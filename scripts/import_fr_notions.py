#!/usr/bin/env python3
"""Importe les notions de français comme thèmes.

Un FIL de la base source (« L'accord de l'adjectif ») devient un thème.
Ses OBJECTIFS (« Accorder l'adjectif en genre avec le nom ») deviennent
son `source_markdown` : c'est à partir d'eux que les exercices seront
rédigés.

Pourquoi les objectifs plutôt que les documents : un objectif dit ce que
l'élève doit savoir FAIRE. C'est exactement l'entrée d'un exercice, et
c'est plus court et plus net qu'un cours entier.

Le tri grammaire / conjugaison / orthographe vient de
`classify_fr_threads.py`, qui écarte au passage la lecture et
l'expression écrite — elles s'évaluent sur une production, pas sur un
choix à quatre options.

    python3 scripts/import_fr_notions.py --dry-run
    python3 scripts/import_fr_notions.py
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify_fr_threads import LEVEL, WORKSPACES, classify, fold  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "sara.db"
SOURCE = Path("/var/www/saralearn-anythingllm/server/storage/anythingllm.db")

SUB = {"Grammaire": "grammaire", "Conjugaison": "conjugaison", "Orthographe": "orthographe"}
COLOR = "#7A4FCB"


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower() or "notion"


def unique_slug(conn: sqlite3.Connection, base: str) -> str:
    slug, n = base, 2
    while conn.execute("SELECT 1 FROM theme WHERE slug = ?", (slug,)).fetchone():
        slug, n = f"{base}-{n}", n + 1
    return slug


def markdown_of(title: str, level: str, objectives: list[sqlite3.Row]) -> str:
    """Le cours donné au modèle : la notion, le niveau, et ce qui est attendu."""
    lines = [f"# {title}", "", f"Niveau : {level}", "",
             "## Ce que l'élève doit savoir faire", ""]
    for o in objectives:
        lines.append(f"- {o['title'].strip()}")
        desc = (o["description"] or "").strip()
        # La description ne répète parfois que le titre : inutile de la
        # redonner au modèle.
        if desc and fold(desc) not in fold(o["title"]):
            lines.append(f"  {desc}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = sqlite3.connect(f"file:{SOURCE}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    threads = src.execute(
        "SELECT w.name AS espace, t.id AS thread_id, t.name AS titre,"
        "       COUNT(o.id) AS n"
        " FROM workspace_threads t JOIN workspaces w ON w.id = t.workspace_id"
        " LEFT JOIN thread_objectives o ON o.threadId = t.id"
        f" WHERE w.name IN ({','.join('?' * len(WORKSPACES))})"
        " GROUP BY t.id HAVING n > 0 ORDER BY t.name",
        WORKSPACES,
    ).fetchall()

    # Même dédoublonnage que le classement : à titre égal, la version la
    # plus fournie l'emporte.
    best: dict[str, sqlite3.Row] = {}
    for t in threads:
        key = fold(t["titre"])
        if key not in best or t["n"] > best[key]["n"]:
            best[key] = t

    conn = sqlite3.connect(DB, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")

    cat = conn.execute("SELECT id FROM category WHERE slug='francais'").fetchone()
    if not cat:
        raise SystemExit("catégorie « francais » absente — joue d'abord le seed")
    subs = {
        r["slug"]: r["id"]
        for r in conn.execute(
            "SELECT slug, id FROM sub_category WHERE category_id = ?", (cat["id"],)
        )
    }
    tag_id = None
    if not args.dry_run:
        conn.execute("INSERT OR IGNORE INTO tag (slug, label) VALUES ('cm2','CM2')")
        tag_id = conn.execute("SELECT id FROM tag WHERE slug='cm2'").fetchone()["id"]

    created, skipped = 0, 0
    per_sub: dict[str, int] = {}

    for t in sorted(best.values(), key=lambda r: r["titre"]):
        bucket = classify(t["titre"])
        if bucket not in SUB:
            skipped += 1
            continue

        objectives = src.execute(
            "SELECT title, description FROM thread_objectives"
            " WHERE threadId = ? ORDER BY orderIndex, id",
            (t["thread_id"],),
        ).fetchall()
        if not objectives:
            skipped += 1
            continue

        level = LEVEL[t["espace"]]
        markdown = markdown_of(t["titre"], level, objectives)
        per_sub[bucket] = per_sub.get(bucket, 0) + 1

        if args.dry_run:
            created += 1
            if created <= 3:
                print(f"\n--- {bucket} · {t['titre']} ({len(objectives)} objectifs) ---")
                print(markdown[:340])
            continue

        slug = unique_slug(conn, slugify(f"{t['titre']}-{level}"))
        cur = conn.execute(
            "INSERT INTO theme (category_id, sub_category_id, slug, title, description,"
            " color, source_markdown, lang, visibility, published_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, 'fr', 'public', datetime('now'))",
            (cat["id"], subs[SUB[bucket]], slug, t["titre"],
             f"{len(objectives)} objectifs du programme de {level}.",
             COLOR, markdown),
        )
        conn.execute(
            "INSERT OR IGNORE INTO theme_tag (theme_id, tag_id) VALUES (?, ?)",
            (cur.lastrowid, tag_id),
        )
        conn.commit()
        created += 1

    print(f"\n{created} notion(s) {'à importer' if args.dry_run else 'importée(s)'}"
          f" · {skipped} écartée(s)")
    for k, v in sorted(per_sub.items()):
        print(f"  {k:12s} {v}")
    conn.close()
    src.close()


if __name__ == "__main__":
    main()
