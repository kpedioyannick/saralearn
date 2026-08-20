"""Inscription, connexion, et fusion de la session anonyme.

L'app ouvre directement sur un exercice : l'utilisateur joue d'abord,
crée un compte ensuite. Tout l'enjeu est que rien de ce qu'il a fait
avant ne soit perdu — c'est ce que promet l'écran Compte.

Deux cas :
  · signup depuis une session anonyme → on attache l'email à la MÊME
    ligne. Rien à déplacer, l'identifiant ne change pas.
  · login depuis une session anonyme vers un compte existant → on
    déplace l'activité de l'anonyme vers le compte, puis on supprime
    l'anonyme.
"""

from __future__ import annotations

import sqlite3
import uuid

from fastapi import APIRouter, HTTPException, status

from ..db import row, transaction
from ..schemas import AnonymousIn, LoginIn, SignupIn, TokenOut, UserOut
from ..security import (
    CurrentUser,
    DbDep,
    OptionalUser,
    hash_password,
    make_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def to_user_out(user: dict) -> UserOut:
    return UserOut(
        id=user["id"],
        lang=user["lang"] if user["lang"] in ("fr", "en") else "fr",
        display_name=user["display_name"],
        email=user["email"],
        is_anonymous=user["email"] is None,
        is_admin=bool(user["is_admin"]),
        muted=bool(user["muted"]),
        dark=None if user["dark"] is None else bool(user["dark"]),
    )


@router.post("/anonymous", response_model=TokenOut)
def anonymous(payload: AnonymousIn, conn: DbDep) -> TokenOut:
    """Ouvre une session sans compte. Idempotent sur le device_id.

    Cette route ne demande pas de mot de passe : elle ne doit donc JAMAIS
    rendre un compte. Un device_id qui retombe sur une ligne devenue
    compte est un identifiant périmé — le compte a rompu le lien avec
    l'appareil en se créant. On le libère et on ouvre une session neuve,
    sans quoi connaître le device_id suffirait à entrer dans le compte.
    """
    user = row(
        conn,
        "SELECT * FROM app_user WHERE device_id = ? AND email IS NULL",
        (payload.device_id,),
    )
    if user is None:
        with transaction(conn):
            # Ligne d'avant la rotation au signup : elle squatte encore le
            # device_id de l'appareil, on le lui retire.
            conn.execute(
                "UPDATE app_user SET device_id = ? WHERE device_id = ? AND email IS NOT NULL",
                (f"acct-{uuid.uuid4()}", payload.device_id),
            )
            cur = conn.execute(
                "INSERT INTO app_user (device_id, lang) VALUES (?, ?)",
                (payload.device_id, payload.lang),
            )
            user_id = cur.lastrowid
        user = row(conn, "SELECT * FROM app_user WHERE id = ?", (user_id,))
    assert user is not None
    return TokenOut(token=make_token(user["id"]), user=to_user_out(user))


@router.post("/signup", response_model=TokenOut)
def signup(payload: SignupIn, conn: DbDep, user: OptionalUser) -> TokenOut:
    """Crée un compte, en conservant la session anonyme si elle existe."""
    taken = row(conn, "SELECT id FROM app_user WHERE email = ?", (payload.email,))
    if taken:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cet email a déjà un compte.")

    pwd = hash_password(payload.password)

    if user is not None and user["email"] is None:
        # Session anonyme : on attache l'email à la ligne existante.
        # Aucune donnée à déplacer, l'identifiant ne bouge pas.
        #
        # Le device_id, lui, doit partir. Il servait à retrouver la session
        # sans mot de passe ; le laisser sur un compte, c'est garder une
        # porte qui s'ouvre avec le seul identifiant de l'appareil — et
        # empêcher toute déconnexion, puisque rouvrir une session anonyme
        # sur cet appareil reconnecterait au compte.
        with transaction(conn):
            # `COALESCE` et non une écriture sèche : le pseudo choisi en
            # session anonyme est déjà sur cette ligne, et le formulaire
            # d'inscription n'a pas de champ pour lui. Sans ça,
            # s'inscrire effaçait le nom qu'on portait au classement.
            conn.execute(
                "UPDATE app_user SET email = ?, password_hash = ?,"
                " display_name = COALESCE(?, display_name),"
                " lang = ?, device_id = ? WHERE id = ?",
                (
                    payload.email,
                    pwd,
                    payload.display_name,
                    payload.lang,
                    f"acct-{uuid.uuid4()}",
                    user["id"],
                ),
            )
        fresh = row(conn, "SELECT * FROM app_user WHERE id = ?", (user["id"],))
    else:
        with transaction(conn):
            cur = conn.execute(
                "INSERT INTO app_user (device_id, email, password_hash, display_name, lang)"
                " VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), payload.email, pwd, payload.display_name, payload.lang),
            )
            new_id = cur.lastrowid
        fresh = row(conn, "SELECT * FROM app_user WHERE id = ?", (new_id,))

    assert fresh is not None
    return TokenOut(token=make_token(fresh["id"]), user=to_user_out(fresh))


def _merge(conn: sqlite3.Connection, source_id: int, target_id: int) -> None:
    """Déplace l'activité d'une session anonyme vers un compte."""
    if source_id == target_id:
        return
    with transaction(conn):
        conn.execute("UPDATE attempt SET user_id = ? WHERE user_id = ?", (target_id, source_id))
        conn.execute(
            "UPDATE exercise_comment SET user_id = ? WHERE user_id = ?", (target_id, source_id)
        )
        # Votes et abonnements ont une clé primaire composite : INSERT OR
        # IGNORE écarte les doublons — si le compte a déjà voté sur un
        # exercice, son vote prime sur celui de la session anonyme —
        # puis on efface la source.
        conn.execute(
            "INSERT OR IGNORE INTO exercise_vote (user_id, exercise_id, value, created_at)"
            " SELECT ?, exercise_id, value, created_at FROM exercise_vote WHERE user_id = ?",
            (target_id, source_id),
        )
        conn.execute("DELETE FROM exercise_vote WHERE user_id = ?", (source_id,))
        conn.execute(
            "INSERT OR IGNORE INTO user_chapter (user_id, chapter_id, created_at)"
            " SELECT ?, chapter_id, created_at FROM user_chapter WHERE user_id = ?",
            (target_id, source_id),
        )
        conn.execute("DELETE FROM user_chapter WHERE user_id = ?", (source_id,))
        # Plus de propriétaire à transférer : `theme.owner_id` est parti
        # avec la reconstruction du catalogue, qui est semé par script et
        # n'appartient à personne. La ligne qui le déplaçait faisait
        # échouer toute connexion depuis une session anonyme — c'est-à-dire
        # la seule façon normale de se connecter.
        conn.execute("DELETE FROM app_user WHERE id = ?", (source_id,))


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, conn: DbDep, user: OptionalUser) -> TokenOut:
    account = row(conn, "SELECT * FROM app_user WHERE email = ?", (payload.email,))
    if account is None or not account["password_hash"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou mot de passe incorrect.")
    if not verify_password(payload.password, account["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou mot de passe incorrect.")

    # Session anonyme en cours : on la fusionne dans le compte retrouvé.
    if user is not None and user["email"] is None:
        _merge(conn, user["id"], account["id"])
        account = row(conn, "SELECT * FROM app_user WHERE id = ?", (account["id"],))

    assert account is not None
    return TokenOut(token=make_token(account["id"]), user=to_user_out(account))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return to_user_out(user)
