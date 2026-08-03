"""Le feed, et l'activité qui s'y rattache.

Sélection, dans l'ordre :
  1. les thèmes abonnés — à défaut, tout le public (l'app doit servir un
     exercice dès le premier lancement, sans réglage préalable) ;
  2. on écarte les N derniers exercices vus ;
  3. on pondère vers les thèmes les moins avancés ;
  4. tirage aléatoire.

Pas d'algorithme adaptatif : ça viendra si le besoin se montre.
"""

from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, HTTPException, Query, status

from ..config import FEED_RECENT_WINDOW
from ..db import row, rows, scalar, transaction
from ..schemas import (
    AttemptIn,
    AttemptOut,
    CommentIn,
    CommentOut,
    ExerciseOut,
    OptionOut,
    VoteIn,
)
from ..security import CurrentUser, DbDep

router = APIRouter(tags=["feed"])


def to_exercise_out(conn: sqlite3.Connection, e: dict, user_id: int | None) -> ExerciseOut:
    raw = json.loads(e["options"])
    my_vote = None
    if user_id is not None:
        v = row(
            conn,
            "SELECT value FROM exercise_vote WHERE user_id = ? AND exercise_id = ?",
            (user_id, e["id"]),
        )
        my_vote = v["value"] if v else None
    comment_count = scalar(
        conn, "SELECT COUNT(*) FROM exercise_comment WHERE exercise_id = ?", (e["id"],)
    )
    return ExerciseOut(
        id=e["id"],
        theme_id=e["theme_id"],
        theme=e["theme_title"],
        color=e["theme_color"] or e["category_color"] or "#0A5C2C",
        type_question=e["type_question"],
        type_bloom=e["type_bloom"],
        prompt=e["prompt"],
        body=e["body"],
        image=e["sign_image"],
        image_alt=e["sign_alt"],
        options=[
            OptionOut(
                label=o.get("label", ""),
                feedback=o.get("feedback"),
                blank=o.get("blank"),
                correct=o.get("correct"),
            )
            for o in raw
        ],
        correct_index=e["correct_index"],
        ok_title=e["ok_title"],
        ok_line=e["ok_line"],
        ko_title=e["ko_title"],
        ko_line=e["ko_line"],
        exp_title=e["exp_title"],
        exp_text=e["exp_text"],
        exp_tip=e["exp_tip"],
        up_count=e["up_count"],
        down_count=e["down_count"],
        my_vote=my_vote,
        comment_count=comment_count or 0,
        state=e["state"],
    )


_SELECT = """
SELECT e.*, t.title AS theme_title, t.color AS theme_color, c.color AS category_color,
       s.image_path AS sign_image, s.image_alt AS sign_alt
FROM exercise e
JOIN theme t    ON t.id = e.theme_id
JOIN category c ON c.id = t.category_id
LEFT JOIN sign s ON s.id = e.sign_id
"""


@router.get("/feed", response_model=list[ExerciseOut])
def feed(conn: DbDep, user: CurrentUser, n: int = Query(default=5, ge=1, le=20)) -> list[ExerciseOut]:
    uid = user["id"]

    # Les abonnements ne sont retenus que s'ils existent dans la langue
    # courante : sinon, changer de langue viderait le feed d'un coup.
    # On retombe alors sur le catalogue public, comme au premier lancement.
    subscribed = [
        r["theme_id"]
        for r in rows(
            conn,
            "SELECT ut.theme_id FROM user_theme ut JOIN theme t ON t.id = ut.theme_id"
            " WHERE ut.user_id = ? AND t.lang = ?",
            (uid, user["lang"]),
        )
    ]

    recent = [
        r["exercise_id"]
        for r in rows(
            conn,
            "SELECT DISTINCT exercise_id FROM attempt WHERE user_id = ?"
            " ORDER BY created_at DESC LIMIT ?",
            (uid, FEED_RECENT_WINDOW),
        )
    ]

    # Un thème est ÉCRIT dans une langue : on ne sert jamais un exercice
    # français à quelqu'un qui lit l'app en anglais.
    where = ["e.state = 'validated'", "t.lang = ?"]
    params: list = [user["lang"]]
    if subscribed:
        where.append(f"e.theme_id IN ({','.join('?' * len(subscribed))})")
        params += subscribed
    else:
        # Premier lancement : rien n'est encore choisi, on sert le public.
        where.append("t.visibility = 'public'")

    def query(exclude: list[int]) -> list[dict]:
        clauses = list(where)
        local = list(params)
        if exclude:
            clauses.append(f"e.id NOT IN ({','.join('?' * len(exclude))})")
            local += exclude
        # La pondération : moins un thème est avancé, plus il remonte.
        # COALESCE parce qu'un thème jamais commencé n'a pas de ligne
        # dans la vue de progression — et c'est justement celui-là qu'on
        # veut proposer en premier.
        #
        # Le bruit va jusqu'à 999 et non jusqu'à 3 : avec seulement
        # quatre valeurs possibles, presque tous les exercices avaient la
        # même clé de tri, et SQLite départageait dans l'ordre de la
        # table. Le feed servait donc toujours les mêmes — les panneaux,
        # insérés en premier — et un thème ajouté ensuite n'apparaissait
        # jamais. Un tri « aléatoire » qui ne l'est pas ne se voit pas :
        # il ressemble à un catalogue pauvre.
        sql = (
            _SELECT
            + " LEFT JOIN v_user_theme_progress p ON p.theme_id = e.theme_id AND p.user_id = ?"
            + " WHERE " + " AND ".join(clauses)
            + " ORDER BY (COALESCE(p.pct, 0) / 25) * 250 + ABS(RANDOM() % 1000)"
            + " LIMIT ?"
        )
        return rows(conn, sql, [uid, *local, n])

    picked = query(recent)
    if len(picked) < n:
        # Le stock est plus petit que la fenêtre anti-répétition : on
        # rouvre plutôt que de renvoyer une liste vide.
        seen = {e["id"] for e in picked}
        for e in query([]):
            if e["id"] not in seen:
                picked.append(e)
                seen.add(e["id"])
            if len(picked) >= n:
                break

    return [to_exercise_out(conn, e, uid) for e in picked]


def _load_exercise(conn: sqlite3.Connection, exercise_id: int) -> dict:
    e = row(conn, _SELECT + " WHERE e.id = ?", (exercise_id,))
    if e is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exercice introuvable.")
    return e


@router.get("/exercises/{exercise_id}", response_model=ExerciseOut)
def get_exercise(exercise_id: int, conn: DbDep, user: CurrentUser) -> ExerciseOut:
    return to_exercise_out(conn, _load_exercise(conn, exercise_id), user["id"])


@router.post("/attempts", response_model=AttemptOut)
def create_attempt(payload: AttemptIn, conn: DbDep, user: CurrentUser) -> AttemptOut:
    """Enregistre une réponse — ou un passage au swipe si chosen_index est nul."""
    e = _load_exercise(conn, payload.exercise_id)
    uid = user["id"]

    is_correct: bool | None = None
    if payload.chosen_index is not None:
        is_correct = payload.chosen_index == e["correct_index"]

    with transaction(conn):
        conn.execute(
            "INSERT INTO attempt (user_id, exercise_id, theme_id, chosen_index, is_correct, answer_ms)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                uid,
                e["id"],
                e["theme_id"],
                payload.chosen_index,
                None if is_correct is None else int(is_correct),
                payload.answer_ms,
            ),
        )
        conn.execute(
            "UPDATE exercise SET attempt_count = attempt_count + 1 WHERE id = ?", (e["id"],)
        )

    totals = row(
        conn,
        "SELECT SUM(is_correct = 1) AS win, SUM(is_correct = 0) AS fail"
        " FROM attempt WHERE user_id = ?",
        (uid,),
    ) or {"win": 0, "fail": 0}

    # Série en cours : on remonte les tentatives répondues jusqu'au
    # premier échec.
    streak = 0
    for r in rows(
        conn,
        "SELECT is_correct FROM attempt WHERE user_id = ? AND chosen_index IS NOT NULL"
        " ORDER BY id DESC LIMIT 50",
        (uid,),
    ):
        if r["is_correct"] == 1:
            streak += 1
        else:
            break

    return AttemptOut(
        is_correct=is_correct,
        win=totals["win"] or 0,
        fail=totals["fail"] or 0,
        streak=streak,
    )


@router.post("/exercises/{exercise_id}/vote", response_model=ExerciseOut)
def vote(
    exercise_id: int, payload: VoteIn, conn: DbDep, user: CurrentUser
) -> ExerciseOut:
    """Pouce en haut, pouce en bas, ou retrait du vote.

    Le pouce en bas n'est pas qu'un ressenti : c'est le seul mécanisme
    qui retire du flux un exercice fautif, puisqu'il n'y a pas de
    relecture humaine. D'où la mise en quarantaine ci-dessous.
    """
    _load_exercise(conn, exercise_id)

    with transaction(conn):
        if payload.value == 0:
            conn.execute(
                "DELETE FROM exercise_vote WHERE user_id = ? AND exercise_id = ?",
                (user["id"], exercise_id),
            )
        else:
            conn.execute(
                "INSERT INTO exercise_vote (user_id, exercise_id, value) VALUES (?, ?, ?)"
                " ON CONFLICT (user_id, exercise_id) DO UPDATE SET value = excluded.value",
                (user["id"], exercise_id, payload.value),
            )

        conn.execute(
            "UPDATE exercise SET"
            "  up_count   = (SELECT COUNT(*) FROM exercise_vote v"
            "                WHERE v.exercise_id = ? AND v.value =  1),"
            "  down_count = (SELECT COUNT(*) FROM exercise_vote v"
            "                WHERE v.exercise_id = ? AND v.value = -1)"
            " WHERE id = ?",
            (exercise_id, exercise_id, exercise_id),
        )

        # La porte : un exercice majoritairement rejeté, sur un échantillon
        # suffisant, sort du flux tout seul. Deux garde-fous plutôt qu'un —
        # un minimum de votes, et une proportion, pas un compte absolu.
        health = row(
            conn,
            "SELECT should_quarantine FROM v_exercise_health WHERE exercise_id = ?",
            (exercise_id,),
        )
        if health and health["should_quarantine"]:
            conn.execute(
                "UPDATE exercise SET state = 'draft' WHERE id = ? AND state = 'validated'",
                (exercise_id,),
            )
            conn.execute(
                "UPDATE theme SET exercise_count ="
                " (SELECT COUNT(*) FROM exercise WHERE theme_id = theme.id"
                "  AND state = 'validated')"
                " WHERE id = (SELECT theme_id FROM exercise WHERE id = ?)",
                (exercise_id,),
            )

    return to_exercise_out(conn, _load_exercise(conn, exercise_id), user["id"])


@router.get("/exercises/{exercise_id}/comments", response_model=list[CommentOut])
def list_comments(exercise_id: int, conn: DbDep, user: CurrentUser) -> list[CommentOut]:
    _load_exercise(conn, exercise_id)
    return [
        CommentOut(
            id=c["id"],
            body=c["body"],
            author=c["display_name"] or "Anonyme",
            created_at=c["created_at"],
        )
        for c in rows(
            conn,
            "SELECT c.id, c.body, c.created_at, u.display_name"
            " FROM exercise_comment c JOIN app_user u ON u.id = c.user_id"
            " WHERE c.exercise_id = ? ORDER BY c.created_at DESC LIMIT 100",
            (exercise_id,),
        )
    ]


@router.post(
    "/exercises/{exercise_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    exercise_id: int, payload: CommentIn, conn: DbDep, user: CurrentUser
) -> CommentOut:
    """Champ libre, lu par l'admin — `is_read` sert sa file de relecture."""
    _load_exercise(conn, exercise_id)
    with transaction(conn):
        cur = conn.execute(
            "INSERT INTO exercise_comment (user_id, exercise_id, body) VALUES (?, ?, ?)",
            (user["id"], exercise_id, payload.body),
        )
        comment_id = cur.lastrowid
    c = row(conn, "SELECT * FROM exercise_comment WHERE id = ?", (comment_id,))
    assert c is not None
    return CommentOut(
        id=c["id"],
        body=c["body"],
        author=user["display_name"] or "Toi",
        created_at=c["created_at"],
    )
