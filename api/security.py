"""Jetons et mots de passe.

Pas de dépendance JWT : un jeton signé HMAC-SHA256 avec la bibliothèque
standard fait exactement le même travail pour ce besoin, et évite
d'installer quoi que ce soit sur la machine.

Format : base64url(payload_json).base64url(hmac)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sqlite3
import time
from typing import Annotated

import bcrypt
from fastapi import Depends, Header, HTTPException, status

from .config import SECRET, TOKEN_TTL_DAYS
from .db import get_db, row


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_token(user_id: int) -> str:
    payload = {"uid": user_id, "exp": int(time.time()) + TOKEN_TTL_DAYS * 86400}
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64e(hmac.new(SECRET, body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def read_token(token: str) -> int | None:
    """Retourne l'identifiant, ou None si le jeton est invalide ou expiré."""
    try:
        body, sig = token.split(".", 1)
    except ValueError:
        return None
    expected = _b64e(hmac.new(SECRET, body.encode(), hashlib.sha256).digest())
    # compare_digest : la comparaison ne doit pas fuir la signature attendue
    # par son temps d'exécution.
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(_b64d(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("exp", 0) < time.time():
        return None
    uid = payload.get("uid")
    return uid if isinstance(uid, int) else None


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


# --------------------------------------------------------------------------
# Dépendances
# --------------------------------------------------------------------------

DbDep = Annotated[sqlite3.Connection, Depends(get_db)]


def _user_from_header(authorization: str | None, conn: sqlite3.Connection) -> dict | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    uid = read_token(authorization[7:].strip())
    if uid is None:
        return None
    return row(conn, "SELECT * FROM app_user WHERE id = ?", (uid,))


def current_user(
    conn: DbDep,
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Exige un utilisateur — même anonyme."""
    user = _user_from_header(authorization, conn)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Jeton absent ou invalide. Appelle POST /auth/anonymous.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    conn.execute(
        "UPDATE app_user SET last_seen_at = datetime('now') WHERE id = ?", (user["id"],)
    )
    return user


def optional_user(
    conn: DbDep,
    authorization: Annotated[str | None, Header()] = None,
) -> dict | None:
    """Pour les routes lisibles sans compte (catalogue public)."""
    return _user_from_header(authorization, conn)


CurrentUser = Annotated[dict, Depends(current_user)]
OptionalUser = Annotated[dict | None, Depends(optional_user)]
