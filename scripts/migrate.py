#!/usr/bin/env python3
"""Joue une migration en s'arrêtant à la PREMIÈRE erreur.

Le client `sqlite3` en ligne de commande poursuit après une instruction
fautive. Sur une migration qui reconstruit une table, ça signifie qu'un
`INSERT` raté n'empêche pas le `DROP TABLE` qui suit de s'exécuter — la
table est détruite et son contenu perdu. C'est arrivé deux fois sur ce
projet : 619 panneaux la première, 886 exercices la seconde.

`executescript` de Python s'arrête à la première exception. Ce script
sauvegarde d'abord, joue ensuite, et restaure si quoi que ce soit
échoue.

    python3 scripts/migrate.py db/migrations/007_saisie_libre_et_trous.sql
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "sara.db"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("migration")
    ap.add_argument("--db", default=str(DB))
    args = ap.parse_args()

    db = Path(args.db)
    sql = Path(args.migration)
    backup = db.with_suffix(db.suffix + f".avant-{sql.stem}")

    shutil.copy2(db, backup)
    print(f"sauvegarde : {backup.name}")

    conn = sqlite3.connect(db)
    before = conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0]
    try:
        conn.executescript(sql.read_text(encoding="utf-8"))
        conn.commit()
    except Exception as exc:  # noqa: BLE001 — on restaure quoi qu'il arrive
        conn.close()
        shutil.copy2(backup, db)
        print(f"ÉCHEC : {exc}\nbase restaurée depuis {backup.name}", file=sys.stderr)
        raise SystemExit(1)

    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    orphans = conn.execute("PRAGMA foreign_key_check").fetchall()
    after = conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0]
    conn.close()

    if integrity != "ok" or orphans:
        shutil.copy2(backup, db)
        print(f"ÉCHEC après coup : intégrité={integrity},"
              f" {len(orphans)} lignes orphelines — base restaurée", file=sys.stderr)
        raise SystemExit(1)

    print(f"appliquée · objets du schéma {before} → {after} · intégrité ok")


if __name__ == "__main__":
    main()
