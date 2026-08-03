"""CRUD des thèmes, abonnements et publication.

Un thème est privé à la création : c'est ce que dit l'écran Publication,
et c'est ce qui permet à quelqu'un de déposer son cours sans l'exposer.
Le passage en public demande une relecture, d'où l'état `pending`.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata

from fastapi import APIRouter, HTTPException, Query, status

from ..db import row, rows, scalar, transaction
from ..schemas import PublishIn, ThemeIn, ThemeOut, ThemePatch
from ..security import CurrentUser, DbDep, OptionalUser

router = APIRouter(tags=["thèmes"])


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "theme"


def unique_slug(conn: sqlite3.Connection, base: str, theme_id: int | None = None) -> str:
    slug = slugify(base)
    candidate, n = slug, 2
    while True:
        clash = row(
            conn,
            "SELECT id FROM theme WHERE slug = ? AND (? IS NULL OR id != ?)",
            (candidate, theme_id, theme_id),
        )
        if clash is None:
            return candidate
        candidate, n = f"{slug}-{n}", n + 1


def _tags_of(conn: sqlite3.Connection, theme_id: int) -> list[str]:
    return [
        t["label"]
        for t in rows(
            conn,
            "SELECT g.label FROM theme_tag tt JOIN tag g ON g.id = tt.tag_id"
            " WHERE tt.theme_id = ? ORDER BY g.label",
            (theme_id,),
        )
    ]


def _set_tags(conn: sqlite3.Connection, theme_id: int, labels: list[str]) -> None:
    conn.execute("DELETE FROM theme_tag WHERE theme_id = ?", (theme_id,))
    for label in labels:
        label = label.strip()
        if not label:
            continue
        slug = slugify(label)
        conn.execute("INSERT OR IGNORE INTO tag (slug, label) VALUES (?, ?)", (slug, label))
        tag_id = scalar(conn, "SELECT id FROM tag WHERE slug = ?", (slug,))
        conn.execute(
            "INSERT OR IGNORE INTO theme_tag (theme_id, tag_id) VALUES (?, ?)",
            (theme_id, tag_id),
        )


def to_theme_out(conn: sqlite3.Connection, t: dict, user: dict | None) -> ThemeOut:
    subscribed = False
    if user is not None:
        subscribed = (
            row(
                conn,
                "SELECT 1 FROM user_theme WHERE user_id = ? AND theme_id = ?",
                (user["id"], t["id"]),
            )
            is not None
        )
    return ThemeOut(
        id=t["id"],
        slug=t["slug"],
        title=t["title"],
        description=t["description"],
        color=t["color"] or t.get("category_color"),
        category_id=t["category_id"],
        category_label=t.get("category_label"),
        sub_category_id=t["sub_category_id"],
        sub_category_label=t.get("sub_category_label"),
        visibility=t["visibility"],
        lang=t["lang"] if t["lang"] in ("fr", "en") else "fr",
        exercise_count=t["exercise_count"],
        subscriber_count=t["subscriber_count"],
        tags=_tags_of(conn, t["id"]),
        is_owner=user is not None and t["owner_id"] == user["id"],
        subscribed=subscribed,
    )


_SELECT = """
SELECT t.*,
       COALESCE(CASE WHEN ? = 'en' THEN c.label_en END, c.label) AS category_label,
       c.color AS category_color,
       COALESCE(CASE WHEN ? = 'en' THEN s.label_en END, s.label) AS sub_category_label
FROM theme t
JOIN category c ON c.id = t.category_id
LEFT JOIN sub_category s ON s.id = t.sub_category_id
"""


def _lang(user: dict | None) -> str:
    return user["lang"] if user and user["lang"] in ("fr", "en") else "fr"


def _load(conn: sqlite3.Connection, theme_id: int, lang: str = "fr") -> dict:
    t = row(conn, _SELECT + " WHERE t.id = ?", (lang, lang, theme_id))
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thème introuvable.")
    return t


def _require_owner(t: dict, user: dict) -> None:
    if t["owner_id"] != user["id"] and not user["is_admin"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce thème ne t'appartient pas.")


@router.get("/themes", response_model=list[ThemeOut])
def list_themes(
    conn: DbDep,
    user: OptionalUser,
    mine: bool = Query(default=False, description="Seulement mes thèmes"),
    sub_category_id: int | None = None,
) -> list[ThemeOut]:
    where = []
    params: list = []
    if mine:
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Connexion requise.")
        where.append("t.owner_id = ?")
        params.append(user["id"])
    else:
        # On ne montre le privé qu'à son auteur.
        where.append("(t.visibility = 'public' OR t.owner_id = ?)")
        params.append(user["id"] if user else -1)
    if sub_category_id is not None:
        where.append("t.sub_category_id = ?")
        params.append(sub_category_id)

    lang = _lang(user)
    where.append("t.lang = ?")
    params.append(lang)
    sql = _SELECT + " WHERE " + " AND ".join(where) + " ORDER BY t.title"
    return [to_theme_out(conn, t, user) for t in rows(conn, sql, [lang, lang, *params])]


@router.get("/themes/{theme_id}", response_model=ThemeOut)
def get_theme(theme_id: int, conn: DbDep, user: OptionalUser) -> ThemeOut:
    t = _load(conn, theme_id, _lang(user))
    if t["visibility"] != "public" and (user is None or t["owner_id"] != user["id"]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thème introuvable.")
    return to_theme_out(conn, t, user)


@router.post("/themes", response_model=ThemeOut, status_code=status.HTTP_201_CREATED)
def create_theme(payload: ThemeIn, conn: DbDep, user: CurrentUser) -> ThemeOut:
    if row(conn, "SELECT id FROM category WHERE id = ?", (payload.category_id,)) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Catégorie inconnue.")

    with transaction(conn):
        cur = conn.execute(
            "INSERT INTO theme (category_id, sub_category_id, owner_id, slug, title,"
            " description, color, source_markdown, lang, visibility)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'private')",
            (
                payload.category_id,
                payload.sub_category_id,
                user["id"],
                unique_slug(conn, payload.title),
                payload.title,
                payload.description,
                payload.color,
                payload.source_markdown,
                payload.lang,
            ),
        )
        theme_id = cur.lastrowid
        _set_tags(conn, theme_id, payload.tags)
    return to_theme_out(conn, _load(conn, theme_id, _lang(user)), user)


@router.patch("/themes/{theme_id}", response_model=ThemeOut)
def update_theme(
    theme_id: int, payload: ThemePatch, conn: DbDep, user: CurrentUser
) -> ThemeOut:
    t = _load(conn, theme_id, _lang(user))
    _require_owner(t, user)

    fields = payload.model_dump(exclude_unset=True, exclude={"tags"})
    with transaction(conn):
        if "title" in fields:
            fields["slug"] = unique_slug(conn, fields["title"], theme_id)
        if fields:
            sets = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(
                f"UPDATE theme SET {sets} WHERE id = ?", (*fields.values(), theme_id)
            )
        if payload.tags is not None:
            _set_tags(conn, theme_id, payload.tags)
    return to_theme_out(conn, _load(conn, theme_id, _lang(user)), user)


@router.delete(
    "/themes/{theme_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_theme(theme_id: int, conn: DbDep, user: CurrentUser) -> None:
    t = _load(conn, theme_id, _lang(user))
    _require_owner(t, user)
    with transaction(conn):
        # Les exercices, tentatives et abonnements suivent en cascade.
        conn.execute("DELETE FROM theme WHERE id = ?", (theme_id,))


@router.post("/themes/{theme_id}/publish", response_model=ThemeOut)
def publish(theme_id: int, payload: PublishIn, conn: DbDep, user: CurrentUser) -> ThemeOut:
    """Privé par défaut ; le public passe par une relecture."""
    t = _load(conn, theme_id, _lang(user))
    _require_owner(t, user)
    visibility = "pending" if payload.public else "private"
    with transaction(conn):
        conn.execute(
            "UPDATE theme SET visibility = ?, published_at = datetime('now') WHERE id = ?",
            (visibility, theme_id),
        )
    return to_theme_out(conn, _load(conn, theme_id, _lang(user)), user)


@router.post("/themes/{theme_id}/subscribe", response_model=ThemeOut)
def subscribe(theme_id: int, conn: DbDep, user: CurrentUser) -> ThemeOut:
    t = _load(conn, theme_id, _lang(user))
    with transaction(conn):
        conn.execute(
            "INSERT OR IGNORE INTO user_theme (user_id, theme_id) VALUES (?, ?)",
            (user["id"], theme_id),
        )
        conn.execute(
            "UPDATE theme SET subscriber_count ="
            " (SELECT COUNT(*) FROM user_theme WHERE theme_id = ?) WHERE id = ?",
            (theme_id, theme_id),
        )
    return to_theme_out(conn, _load(conn, t["id"], _lang(user)), user)


@router.delete("/themes/{theme_id}/subscribe", response_model=ThemeOut)
def unsubscribe(theme_id: int, conn: DbDep, user: CurrentUser) -> ThemeOut:
    _load(conn, theme_id, _lang(user))
    with transaction(conn):
        conn.execute(
            "DELETE FROM user_theme WHERE user_id = ? AND theme_id = ?",
            (user["id"], theme_id),
        )
        conn.execute(
            "UPDATE theme SET subscriber_count ="
            " (SELECT COUNT(*) FROM user_theme WHERE theme_id = ?) WHERE id = ?",
            (theme_id, theme_id),
        )
    return to_theme_out(conn, _load(conn, theme_id, _lang(user)), user)
