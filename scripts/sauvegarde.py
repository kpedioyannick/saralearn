#!/usr/bin/env python3
"""Sauvegarde la base, à chaud, sans risquer une copie incohérente.

`cp base.db ailleurs` est faux sur une base vivante. SQLite est en mode
WAL : les écritures récentes vivent dans `sara.db-wal` et pas encore
dans le fichier principal. Copier l'un sans l'autre, ou les copier à
deux instants différents, produit une base tronquée ou corrompue — et on
ne s'en aperçoit que le jour où on essaie de la restaurer.

`Connection.backup()` fait le travail correctement : il tient un
instantané cohérent pendant que l'API continue d'écrire.

Chaque sauvegarde est ensuite RELUE et vérifiée avant d'être conservée.
Une sauvegarde qu'on n'a pas ouverte n'est pas une sauvegarde, c'est un
espoir.

    python3 scripts/sauvegarde.py
    python3 scripts/sauvegarde.py --vers /media/disque --garder 30
"""

from __future__ import annotations

import argparse
import gzip
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "sara.db"
DEST = Path("/var/backups/saralearn")


def sauvegarde(db: Path, dest: Path, garder: int) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    final = dest / f"sara-{horodatage}.db.gz"

    with tempfile.TemporaryDirectory() as tmp:
        brut = Path(tmp) / "sara.db"
        src = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        cible = sqlite3.connect(brut)
        with cible:
            src.backup(cible)          # instantané cohérent, base vivante
        cible.close()
        src.close()

        # On relit la copie avant de la garder. Une sauvegarde jamais
        # ouverte ne prouve rien.
        relu = sqlite3.connect(f"file:{brut}?mode=ro", uri=True)
        etat = relu.execute("PRAGMA integrity_check").fetchone()[0]
        exos = relu.execute("SELECT COUNT(*) FROM exercise").fetchone()[0]
        themes = relu.execute("SELECT COUNT(*) FROM theme").fetchone()[0]
        relu.close()
        if etat != "ok":
            raise SystemExit(f"sauvegarde illisible ({etat}) — rien conservé")

        with brut.open("rb") as f, gzip.open(final, "wb", compresslevel=6) as g:
            shutil.copyfileobj(f, g)

    poids = final.stat().st_size / 1_048_576
    print(f"{final}  {poids:.1f} Mo  ·  {exos} exercices, {themes} thèmes  ·  intégrité ok")

    # Rotation : on garde les N plus récentes, on supprime le reste.
    anciennes = sorted(dest.glob("sara-*.db.gz"), reverse=True)[garder:]
    for a in anciennes:
        a.unlink()
    if anciennes:
        print(f"{len(anciennes)} sauvegarde(s) ancienne(s) supprimée(s)")
    return final


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(DB))
    ap.add_argument("--vers", default=str(DEST))
    ap.add_argument("--garder", type=int, default=14,
                    help="nombre de sauvegardes conservées (défaut : 14)")
    args = ap.parse_args()

    db = Path(args.base)
    if not db.exists():
        print(f"base introuvable : {db}", file=sys.stderr)
        raise SystemExit(1)
    sauvegarde(db, Path(args.vers), args.garder)


if __name__ == "__main__":
    main()
