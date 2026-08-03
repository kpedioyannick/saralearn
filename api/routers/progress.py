"""Progression, classement, réglages.

Les pourcentages ne vivent qu'ici : jamais pendant un exercice.
Tout est dérivé des vues SQL, donc du seul journal des tentatives.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from ..db import row, rows, transaction
from ..schemas import ProgressOut, RankRowOut, SettingsIn, SettingsOut
from ..security import CurrentUser, DbDep

router = APIRouter(tags=["progression"])


@router.get("/progression", response_model=list[ProgressOut])
def progression(conn: DbDep, user: CurrentUser) -> list[ProgressOut]:
    """Les sous-catégories commencées, et rien d'autre."""
    return [
        ProgressOut(
            theme_id=p["theme_id"],
            name=p["title"],
            passed=p["passed"] or 0,
            total=p["total"] or 0,
            pct=p["pct"] or 0,
        )
        for p in rows(
            conn,
            "SELECT p.theme_id, p.passed, p.total, p.pct, t.title"
            " FROM v_user_theme_progress p JOIN theme t ON t.id = p.theme_id"
            " WHERE p.user_id = ? ORDER BY p.pct DESC, t.title",
            (user["id"],),
        )
    ]


# La semaine court du lundi : `%w` donne 0 pour dimanche, d'où le +6 % 7.
_WEEK_SQL = (
    "SELECT w.user_id, w.points, w.passed, u.display_name"
    " FROM v_theme_week_rank w JOIN app_user u ON u.id = w.user_id"
    " WHERE w.theme_id = ?"
    "   AND w.week_start = date('now', '-' ||"
    "       ((CAST(strftime('%w','now') AS INTEGER) + 6) % 7) || ' days')"
    " ORDER BY w.points DESC, w.passed DESC"
)


def _name(r: dict) -> str:
    return r["display_name"] or f"Joueur {r['user_id']}"


def _with_me(conn, top: list, user_id: int, sql: str, params: tuple) -> list[RankRowOut]:
    """Le haut du classement, plus MA ligne si elle n'y est pas.

    Un classement où l'on ne se trouve pas ne sert à rien : l'app en
    compte déjà plus de vingt joueurs, et le vingt-et-unième ne voyait
    aucune trace de lui. On ajoute donc sa ligne à la fin, avec son rang
    RÉEL — pas le rang de la dernière place affichée, qui serait un
    mensonge poli.
    """
    out = [
        RankRowOut(rank=i + 1, user_id=r["user_id"], name=_name(r),
                   points=r["points"] or 0, passed=r["passed"] or 0,
                   is_me=r["user_id"] == user_id)
        for i, r in enumerate(top)
    ]
    if any(x.is_me for x in out):
        return out
    everyone = rows(conn, sql, params)
    for i, r in enumerate(everyone):
        if r["user_id"] == user_id:
            out.append(RankRowOut(rank=i + 1, user_id=r["user_id"], name=_name(r),
                                  points=r["points"] or 0, passed=r["passed"] or 0,
                                  is_me=True))
            break
    return out


@router.get("/rank/global", response_model=list[RankRowOut])
def rank_global(
    conn: DbDep, user: CurrentUser, limit: int = Query(default=20, ge=1, le=100)
) -> list[RankRowOut]:
    base = ("SELECT g.user_id, g.points, g.passed, u.display_name"
            " FROM v_global_rank g JOIN app_user u ON u.id = g.user_id"
            " ORDER BY g.points DESC, g.passed DESC")
    return _with_me(conn, rows(conn, base + " LIMIT ?", (limit,)),
                    user["id"], base, ())


@router.get("/rank/theme/{theme_id}", response_model=list[RankRowOut])
def rank_theme(
    theme_id: int, conn: DbDep, user: CurrentUser, limit: int = Query(default=20, ge=1, le=100)
) -> list[RankRowOut]:
    """Classement de la semaine en cours — il repart chaque lundi."""
    if row(conn, "SELECT id FROM theme WHERE id = ?", (theme_id,)) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thème introuvable.")
    return _with_me(conn, rows(conn, _WEEK_SQL + " LIMIT ?", (theme_id, limit)),
                    user["id"], _WEEK_SQL, (theme_id,))


@router.get("/settings", response_model=SettingsOut)
def get_settings(conn: DbDep, user: CurrentUser) -> SettingsOut:
    return SettingsOut(
        muted=bool(user["muted"]),
        dark=None if user["dark"] is None else bool(user["dark"]),
        lang=user["lang"] if user["lang"] in ("fr", "en") else "fr",
        theme_ids=[
            r["theme_id"]
            for r in rows(
                conn, "SELECT theme_id FROM user_theme WHERE user_id = ?", (user["id"],)
            )
        ],
    )


@router.put("/settings", response_model=SettingsOut)
def put_settings(payload: SettingsIn, conn: DbDep, user: CurrentUser) -> SettingsOut:
    uid = user["id"]
    with transaction(conn):
        if payload.muted is not None:
            conn.execute("UPDATE app_user SET muted = ? WHERE id = ?", (int(payload.muted), uid))
        if payload.dark is not None:
            conn.execute("UPDATE app_user SET dark = ? WHERE id = ?", (int(payload.dark), uid))
        if payload.lang is not None:
            conn.execute("UPDATE app_user SET lang = ? WHERE id = ?", (payload.lang, uid))
        if payload.theme_ids is not None:
            conn.execute("DELETE FROM user_theme WHERE user_id = ?", (uid,))
            # OR IGNORE n'avale pas une violation de clé étrangère : un
            # thème supprimé depuis que le client a chargé son catalogue
            # faisait remonter une IntegrityError en 500. On écarte les
            # identifiants inconnus plutôt que de casser l'appel — le
            # client réenverra la liste qu'il connaît.
            for tid in payload.theme_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO user_theme (user_id, theme_id)"
                    " SELECT ?, id FROM theme WHERE id = ?",
                    (uid, tid),
                )
            conn.execute(
                "UPDATE theme SET subscriber_count ="
                " (SELECT COUNT(*) FROM user_theme WHERE theme_id = theme.id)"
            )
    fresh = row(conn, "SELECT * FROM app_user WHERE id = ?", (uid,))
    assert fresh is not None
    return get_settings(conn, fresh)
