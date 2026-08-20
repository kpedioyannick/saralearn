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


def registered_user(user: Annotated[dict, Depends(current_user)]) -> dict:
    """Exige un vrai compte : email et mot de passe.

    L'app se joue sans compte, et ça ne change pas — répondre, s'abonner,
    voter, commenter restent ouverts à une session anonyme. Créer une
    connaissance, non : elle porte un auteur, elle passe en relecture, et
    elle reste attachée à quelqu'un après publication. Une session
    anonyme meurt avec le `localStorage` de son appareil ; l'y adosser,
    c'est fabriquer des contenus orphelins qu'aucun humain ne peut plus
    corriger ni retirer.

    Le contrôle est ici et pas dans l'interface : l'API est publique, et
    un bouton grisé n'a jamais empêché un POST.
    """
    if user["email"] is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Il faut un compte pour créer une connaissance.",
        )
    return user


def author(user: Annotated[dict, Depends(current_user)]) -> dict:
    """Qui a le droit de déposer une connaissance : l'administration, et
    elle seule, le temps de la remise à niveau.

    Le pipeline de création parle le schéma d'avant la reconstruction du
    catalogue — `category`, `theme.owner_id`, `chapter.generated_prompt`
    ont disparu — et ses sept routes rendent 500. Un 500 ne dit rien à
    celui qui le reçoit ; ce 403 dit ce qui se passe.

    Le contrôle est ici et pas seulement dans l'interface : l'API est
    publique, et un écran fermé n'a jamais empêché un POST.
    """
    if not user["is_admin"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Déposer une connaissance est réservé à l'administration.",
        )
    return user


CurrentUser = Annotated[dict, Depends(current_user)]
OptionalUser = Annotated[dict | None, Depends(optional_user)]
RegisteredUser = Annotated[dict, Depends(registered_user)]
Author = Annotated[dict, Depends(author)]
