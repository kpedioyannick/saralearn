"""Administration — la file de relecture.

Trois choses vivaient en base sans jamais remonter à l'écran :

  1. les thèmes `pending`, déposés par les utilisateurs et jamais relus ;
  2. les exercices que le vote communautaire a écartés du flux
     (`v_exercise_health.should_quarantine`) ;
  3. les commentaires, dont le cahier des charges dit « envoyé à
     l'admin » — sans que personne puisse les lire.

Ce routeur les expose, et donne les gestes qui vont avec.

Deux portes d'entrée, dans cet ordre :

  · `app_user.is_admin` — la colonne existe déjà (`db/schema.sql`), et
    `themes.py` s'en sert pour laisser un admin éditer le thème d'un
    autre. C'est le mécanisme de la maison : on ne lui en invente pas
    un deuxième.
  · `SARA_ADMIN_TOKEN` dans l'environnement du service, comparé en
    temps constant à l'en-tête `X-Admin-Token`. Il ne remplace pas la
    colonne, il l'amorce : aujourd'hui aucun compte n'a `is_admin = 1`,
    et promouvoir le premier demande un accès à la base que l'interface
    n'a pas. Variable absente ou vide = porte fermée, sans exception.

Les schémas de ce domaine vivent ici plutôt que dans `schemas.py` :
l'admin n'est pas une surface publique, et rien d'autre ne s'en sert.
"""

from __future__ import annotations

import hmac
import os
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel

from ..db import row, rows, scalar, transaction
from ..schemas import ExerciseState, Lang, TypeQuestion, Visibility
from ..security import DbDep, OptionalUser

router = APIRouter(prefix="/admin", tags=["admin"])


# --------------------------------------------------------------------------
# Porte d'entrée
# --------------------------------------------------------------------------

ADMIN_TOKEN_ENV = "SARA_ADMIN_TOKEN"


def _configured_token() -> str:
    """Lue à chaque appel : redémarrer le service suffit à la changer."""
    return os.environ.get(ADMIN_TOKEN_ENV, "").strip()


def require_admin(
    user: OptionalUser,
    x_admin_token: Annotated[str | None, Header()] = None,
) -> dict | None:
    """L'admin identifié, ou None s'il est entré par le jeton de service.

    Le jeton de service n'identifie personne — même si la requête porte
    par ailleurs une session : on retourne None, et l'écran le dit. Un
    geste d'admin sans nom vaut mieux qu'un geste attribué au mauvais.

    Un 403 unique quel que soit le motif : « jeton absent » et « jeton
    faux » n'apprennent rien de différent à qui tâtonne.
    """
    if user is not None and user["is_admin"]:
        return user

    configured = _configured_token()
    if configured and x_admin_token:
        # compare_digest : la comparaison ne doit pas fuir le jeton
        # attendu par son temps d'exécution. En octets — un en-tête
        # peut contenir n'importe quoi, et la variante texte refuse le
        # non-ASCII avec une exception qui, elle, se chronomètre.
        if hmac.compare_digest(x_admin_token.strip().encode(), configured.encode()):
            return None

    raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé à l'administration.")


AdminUser = Annotated[dict | None, Depends(require_admin)]


# --------------------------------------------------------------------------
# Schémas
# --------------------------------------------------------------------------

class AdminSummaryOut(BaseModel):
    pending_themes: int
    quarantined: int
    comments: int
    unread_comments: int
    #  Qui est entré, et comment — l'écran le dit en clair plutôt que de
    #  laisser croire à une session admin qui n'existe pas.
    identified: bool
    display_name: str | None = None


class AdminThemeOut(BaseModel):
    id: int
    title: str
    slug: str
    description: str | None = None
    lang: Lang = "fr"
    visibility: Visibility
    category_label: str
    color: str
    owner_id: int | None = None
    owner_name: str | None = None
    # Le compte est recalculé, jamais lu dans `theme.exercise_count` :
    # un compteur stocké finit toujours par mentir, et c'est justement
    # sur ce nombre qu'on décide de publier.
    exercise_count: int
    subscriber_count: int
    created_at: str
    submitted_at: str | None = None


class AdminExerciseOut(BaseModel):
    id: int
    theme_id: int
    theme_title: str
    color: str
    type_question: TypeQuestion
    state: ExerciseState
    prompt: str
    up_count: int
    down_count: int
    votes: int
    down_pct: int
    comment_count: int


class AdminCommentOut(BaseModel):
    id: int
    body: str
    created_at: str
    is_read: bool
    author: str
    user_id: int
    exercise_id: int
    exercise_prompt: str
    theme_id: int
    theme_title: str


# --------------------------------------------------------------------------
# Lectures
# --------------------------------------------------------------------------

# Ce que relit l'admin, ce sont des CHAPITRES — un apprentissage est un
# chapitre depuis les migrations 016 à 022, et le vocabulaire de l'API
# n'a pas suivi (voir `routers/feed.py`). Trois choses ont disparu avec
# l'ancien modèle et valent désormais une constante :
#   · la langue — anglais seul, décidé et non rouvert ;
#   · le propriétaire — le catalogue est semé par script, personne ne
#     possède rien, donc pas d'auteur à joindre ;
#   · la catégorie — c'est le thème, l'un des jours de la création.
_CHAPTER_SELECT = """
SELECT ch.id, ch.title, ch.slug, ch.description, ch.visibility,
       ch.subscriber_count, ch.created_at, ch.published_at,
       th.title AS category_label, th.color AS category_color,
       (SELECT COUNT(*) FROM exercise e
         WHERE e.chapter_id = ch.id AND e.state = 'validated') AS live_count
FROM chapter ch
JOIN theme th ON th.id = ch.theme_id
"""


def _to_theme_out(t: dict) -> AdminThemeOut:
    return AdminThemeOut(
        id=t["id"],
        title=t["title"],
        slug=t["slug"],
        description=t["description"],
        lang="en",
        visibility=t["visibility"],
        category_label=t["category_label"],
        color=t["category_color"] or "#0A5C2C",
        owner_id=None,
        owner_name=None,
        exercise_count=t["live_count"],
        subscriber_count=t["subscriber_count"],
        created_at=t["created_at"],
        submitted_at=t["published_at"],
    )


def _load_theme(conn: sqlite3.Connection, theme_id: int) -> dict:
    t = row(conn, _CHAPTER_SELECT + " WHERE ch.id = ?", (theme_id,))
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Apprentissage introuvable.")
    return t


@router.get("/summary", response_model=AdminSummaryOut)
def summary(conn: DbDep, admin: AdminUser) -> AdminSummaryOut:
    """De quoi peindre les compteurs d'onglets en un aller-retour."""
    return AdminSummaryOut(
        pending_themes=scalar(
            conn, "SELECT COUNT(*) FROM chapter WHERE visibility = 'pending'"
        )
        or 0,
        quarantined=scalar(
            conn,
            "SELECT COUNT(*) FROM v_exercise_health h JOIN exercise e"
            " ON e.id = h.exercise_id"
            " WHERE h.should_quarantine = 1 AND e.state != 'rejected'",
        )
        or 0,
        comments=scalar(conn, "SELECT COUNT(*) FROM exercise_comment") or 0,
        unread_comments=scalar(
            conn, "SELECT COUNT(*) FROM exercise_comment WHERE is_read = 0"
        )
        or 0,
        identified=admin is not None,
        display_name=None if admin is None else admin["display_name"],
    )


@router.get("/themes/pending", response_model=list[AdminThemeOut])
def pending_themes(conn: DbDep, admin: AdminUser) -> list[AdminThemeOut]:
    """La file d'attente, du plus ancien dépôt au plus récent."""
    return [
        _to_theme_out(t)
        for t in rows(
            conn,
            _CHAPTER_SELECT
            + " WHERE ch.visibility = 'pending'"
            " ORDER BY COALESCE(ch.published_at, ch.created_at) ASC, ch.id ASC",
        )
    ]


@router.get("/exercises/quarantine", response_model=list[AdminExerciseOut])
def quarantined_exercises(
    conn: DbDep,
    admin: AdminUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AdminExerciseOut]:
    """Ce que le vote a écarté — les plus rejetés d'abord.

    Un exercice déjà `rejected` a été tranché : il sort de la file.
    `state` reste affiché parce qu'il dit ce qui s'est passé — la
    quarantaine automatique repasse en `draft`, pas en `rejected`.
    """
    return [
        AdminExerciseOut(
            id=e["id"],
            theme_id=e["chapter_id"],
            theme_title=e["chapter_title"],
            color=e["day_color"] or "#0A5C2C",
            type_question=e["type_question"],
            state=e["state"],
            prompt=e["prompt"],
            up_count=e["up_count"],
            down_count=e["down_count"],
            votes=e["votes"],
            down_pct=int(e["down_pct"] or 0),
            comment_count=e["comment_count"],
        )
        for e in rows(
            conn,
            "SELECT e.id, e.chapter_id, e.type_question, e.state, e.prompt,"
            "       h.up_count, h.down_count, h.votes, h.down_pct,"
            "       ch.title AS chapter_title, th.color AS day_color,"
            "       (SELECT COUNT(*) FROM exercise_comment k"
            "         WHERE k.exercise_id = e.id) AS comment_count"
            " FROM v_exercise_health h"
            " JOIN exercise e  ON e.id = h.exercise_id"
            " JOIN chapter ch  ON ch.id = e.chapter_id"
            " JOIN theme th    ON th.id = ch.theme_id"
            " WHERE h.should_quarantine = 1 AND e.state != 'rejected'"
            " ORDER BY h.down_count DESC, e.id ASC LIMIT ?",
            (limit,),
        )
    ]


@router.get("/comments", response_model=list[AdminCommentOut])
def recent_comments(
    conn: DbDep,
    admin: AdminUser,
    unread_only: bool = Query(default=False, description="Seulement les non lus"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AdminCommentOut]:
    where = "WHERE k.is_read = 0" if unread_only else ""
    return [
        AdminCommentOut(
            id=k["id"],
            body=k["body"],
            created_at=k["created_at"],
            is_read=bool(k["is_read"]),
            author=k["display_name"] or "Anonyme",
            user_id=k["user_id"],
            exercise_id=k["exercise_id"],
            exercise_prompt=k["prompt"],
            theme_id=k["chapter_id"],
            theme_title=k["chapter_title"],
        )
        for k in rows(
            conn,
            "SELECT k.id, k.body, k.created_at, k.is_read, k.user_id, k.exercise_id,"
            "       u.display_name, e.prompt, ch.id AS chapter_id,"
            "       ch.title AS chapter_title"
            " FROM exercise_comment k"
            " JOIN app_user u ON u.id = k.user_id"
            " JOIN exercise e ON e.id = k.exercise_id"
            " JOIN chapter ch ON ch.id = e.chapter_id"
            f" {where}"
            " ORDER BY k.created_at DESC, k.id DESC LIMIT ?",
            (limit,),
        )
    ]


# --------------------------------------------------------------------------
# Actions
# --------------------------------------------------------------------------

@router.post("/themes/{theme_id}/approve", response_model=AdminThemeOut)
def approve_theme(theme_id: int, conn: DbDep, admin: AdminUser) -> AdminThemeOut:
    """Met le thème en ligne. `published_at` marque la mise en ligne,
    pas la demande : c'est la date qu'attend quiconque lira l'historique."""
    t = _load_theme(conn, theme_id)
    if t["visibility"] == "public":
        return _to_theme_out(t)
    with transaction(conn):
        conn.execute(
            "UPDATE chapter SET visibility = 'public', published_at = datetime('now')"
            " WHERE id = ?",
            (theme_id,),
        )
    return _to_theme_out(_load_theme(conn, theme_id))


@router.post("/themes/{theme_id}/reject", response_model=AdminThemeOut)
def reject_theme(theme_id: int, conn: DbDep, admin: AdminUser) -> AdminThemeOut:
    """Refuse la publication — le thème redevient privé.

    On ne supprime rien : l'auteur garde son cours et ses exercices
    dans son propre flux, et peut redemander la publication après
    correction. Refuser n'est pas punir.
    """
    t = _load_theme(conn, theme_id)
    if t["visibility"] != "pending":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Cet apprentissage n'est pas en attente de relecture."
        )
    with transaction(conn):
        conn.execute(
            "UPDATE chapter SET visibility = 'private', published_at = NULL WHERE id = ?",
            (theme_id,),
        )
    return _to_theme_out(_load_theme(conn, theme_id))


def _recount(conn: sqlite3.Connection, chapter_id: int) -> None:
    """`chapter.exercise_count` ne compte que le validé — comme partout ailleurs."""
    conn.execute(
        "UPDATE chapter SET exercise_count ="
        " (SELECT COUNT(*) FROM exercise WHERE chapter_id = ? AND state = 'validated')"
        " WHERE id = ?",
        (chapter_id, chapter_id),
    )


def _set_state(conn: sqlite3.Connection, exercise_id: int, state: str) -> dict:
    e = row(conn, "SELECT id, chapter_id FROM exercise WHERE id = ?", (exercise_id,))
    if e is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exercice introuvable.")
    with transaction(conn):
        conn.execute("UPDATE exercise SET state = ? WHERE id = ?", (state, exercise_id))
        _recount(conn, e["chapter_id"])
    return e


@router.post(
    "/exercises/{exercise_id}/withdraw",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def withdraw_exercise(exercise_id: int, conn: DbDep, admin: AdminUser) -> None:
    """Retire définitivement l'exercice de la circulation.

    `rejected` plutôt que suppression : le texte reste attaché à son
    `exercise_prompt`, donc au prompt exact qui l'a écrit. C'est la
    seule façon de remonter d'un exercice fautif au gabarit fautif.
    """
    _set_state(conn, exercise_id, "rejected")


@router.post(
    "/exercises/{exercise_id}/restore",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def restore_exercise(exercise_id: int, conn: DbDep, admin: AdminUser) -> None:
    """Remet en circulation un exercice écarté à tort.

    Attention : les votes ne sont pas effacés. Le prochain pouce baissé
    rouvre la porte de `feed.vote` et le remet en quarantaine. Remettre
    en ligne sans corriger le texte ne tient donc pas longtemps — c'est
    voulu, la communauté garde le dernier mot.
    """
    _set_state(conn, exercise_id, "validated")


@router.post(
    "/comments/{comment_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def mark_comment_read(comment_id: int, conn: DbDep, admin: AdminUser) -> None:
    """`is_read` existe depuis le premier schéma et n'avait jamais servi :
    sans lui, la file des non lus ne se vide jamais."""
    if row(conn, "SELECT id FROM exercise_comment WHERE id = ?", (comment_id,)) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Commentaire introuvable.")
    with transaction(conn):
        conn.execute("UPDATE exercise_comment SET is_read = 1 WHERE id = ?", (comment_id,))


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_comment(comment_id: int, conn: DbDep, admin: AdminUser) -> None:
    if row(conn, "SELECT id FROM exercise_comment WHERE id = ?", (comment_id,)) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Commentaire introuvable.")
    with transaction(conn):
        conn.execute("DELETE FROM exercise_comment WHERE id = ?", (comment_id,))
