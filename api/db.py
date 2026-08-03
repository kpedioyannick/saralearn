"""Accès SQLite.

Une connexion par requête, refermée à la fin. SQLite en WAL supporte
plusieurs lecteurs pendant une écriture, ce qui suffit largement ici :
le feed lit, les tentatives écrivent, et rien ne bloque.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from .config import DB_PATH


def _connect() -> sqlite3.Connection:
    # check_same_thread=False : FastAPI répartit chaque dépendance
    # synchrone dans son pool de threads, sans garantir que la
    # dépendance `get_db` et celle qui l'utilise tombent sur le même.
    # La connexion franchit donc légitimement une frontière de thread.
    #
    # C'est sans danger ici parce qu'elle n'est JAMAIS partagée entre
    # deux requêtes : `get_db` en ouvre une par requête et la referme à
    # la fin. Les threads s'y succèdent, ils ne s'y télescopent pas.
    conn = sqlite3.connect(
        DB_PATH, timeout=10, isolation_level=None, check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    # Les clés étrangères sont désactivées par défaut dans SQLite : sans
    # ça, ON DELETE CASCADE ne s'applique pas.
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """Dépendance FastAPI."""
    with connection() as conn:
        yield conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def rows(conn: sqlite3.Connection, sql: str, params: Any = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def row(conn: sqlite3.Connection, sql: str, params: Any = ()) -> dict | None:
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None


def scalar(conn: sqlite3.Connection, sql: str, params: Any = ()) -> Any:
    r = conn.execute(sql, params).fetchone()
    return r[0] if r else None
