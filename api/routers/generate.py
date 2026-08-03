"""Génération des exercices à partir du Markdown déposé.

Un lancement crée une ligne `exercise_prompt` par couple
(type de question × niveau de Bloom), avec le texte exact envoyé au
modèle. Les exercices arrivent en `draft` : rien n'entre au feed sans
être relu.
"""

from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from ..config import LLM_NAME
from ..db import connection, row, rows, scalar, transaction
from ..llm import GenerationError, ask, render, validate
from ..schemas import (
    ExerciseOut,
    ExercisePatch,
    GenerateIn,
    GenerationRunOut,
    GenerationStatusOut,
)
from ..security import CurrentUser, DbDep
from .feed import _load_exercise, to_exercise_out
from .themes import _load, _require_owner

router = APIRouter(tags=["génération"])


def _status(conn: sqlite3.Connection, theme_id: int) -> GenerationStatusOut:
    runs = rows(
        conn,
        "SELECT ep.id, ep.status, ep.requested_count, ep.produced_count, ep.error,"
        "       p.type_question, p.type_bloom"
        " FROM exercise_prompt ep JOIN prompt p ON p.id = ep.prompt_id"
        " WHERE ep.theme_id = ? ORDER BY ep.id",
        (theme_id,),
    )
    return GenerationStatusOut(
        theme_id=theme_id,
        running=any(r["status"] in ("pending", "running") for r in runs),
        requested=sum(r["requested_count"] for r in runs),
        produced=sum(r["produced_count"] for r in runs),
        validated=scalar(
            conn,
            "SELECT COUNT(*) FROM exercise WHERE theme_id = ? AND state = 'validated'",
            (theme_id,),
        )
        or 0,
        runs=[GenerationRunOut(**r) for r in runs],
    )


async def _run(run_id: int) -> None:
    """Exécute un lancement. Isolé : un échec n'emporte pas les autres."""
    with connection() as conn:
        run = row(
            conn,
            "SELECT ep.*, p.type_question FROM exercise_prompt ep"
            " JOIN prompt p ON p.id = ep.prompt_id WHERE ep.id = ?",
            (run_id,),
        )
        if run is None:
            return
        conn.execute(
            "UPDATE exercise_prompt SET status = 'running' WHERE id = ?", (run_id,)
        )

    try:
        raw = await ask(run["rendered_prompt"])
        items = validate(raw, run["type_question"])
        if not items:
            raise GenerationError("Le modèle n'a produit aucun exercice exploitable.")
    except (GenerationError, Exception) as exc:  # noqa: BLE001 — on trace tout
        with connection() as conn:
            conn.execute(
                "UPDATE exercise_prompt SET status = 'failed', error = ?,"
                " finished_at = datetime('now') WHERE id = ?",
                (str(exc)[:1000], run_id),
            )
        return

    with connection() as conn:
        bloom = scalar(
            conn,
            "SELECT p.type_bloom FROM exercise_prompt ep JOIN prompt p ON p.id = ep.prompt_id"
            " WHERE ep.id = ?",
            (run_id,),
        )
        with transaction(conn):
            for item in items:
                conn.execute(
                    "INSERT INTO exercise (theme_id, exercise_prompt_id, type_question,"
                    " type_bloom, prompt, body, options, correct_index, ok_title, ok_line,"
                    " ko_title, ko_line, exp_title, exp_text, exp_tip, state)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'draft')",
                    (
                        run["theme_id"],
                        run_id,
                        run["type_question"],
                        bloom,
                        item["prompt"],
                        item["body"],
                        json.dumps(item["options"], ensure_ascii=False),
                        item["correct_index"],
                        item["ok_title"],
                        item["ok_line"],
                        item["ko_title"],
                        item["ko_line"],
                        item["exp_title"],
                        item["exp_text"],
                        item["exp_tip"],
                    ),
                )
            conn.execute(
                "UPDATE exercise_prompt SET status = 'done', produced_count = ?,"
                " finished_at = datetime('now') WHERE id = ?",
                (len(items), run_id),
            )


# Volontairement synchrone : la dépendance SQLite est créée dans un thread
# du pool, et une connexion sqlite3 ne peut pas franchir un thread. Une
# route `async` la ferait ouvrir ici et utiliser sur la boucle — erreur
# garantie. Rien n'est attendu dans ce corps ; le travail long part en
# tâche de fond, qui, elle, est bien asynchrone.
@router.post("/themes/{theme_id}/generate", response_model=GenerationStatusOut)
def generate(
    theme_id: int,
    payload: GenerateIn,
    conn: DbDep,
    user: CurrentUser,
    background: BackgroundTasks,
) -> GenerationStatusOut:
    theme = _load(conn, theme_id, user["lang"])
    _require_owner(theme, user)

    if not theme["source_markdown"]:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Ce thème n'a pas encore de cours. Dépose du Markdown avant de générer.",
        )

    tags = ", ".join(
        t["label"]
        for t in rows(
            conn,
            "SELECT g.label FROM theme_tag tt JOIN tag g ON g.id = tt.tag_id"
            " WHERE tt.theme_id = ?",
            (theme_id,),
        )
    )

    pairs = [(q, b) for q in payload.types for b in payload.blooms]
    # Le volume demandé se répartit sur les couples choisis, au minimum 1.
    per_run = max(1, payload.count // max(1, len(pairs)))

    run_ids: list[int] = []
    with transaction(conn):
        for type_question, type_bloom in pairs:
            gabarit = row(
                conn,
                "SELECT * FROM prompt WHERE lang = ? AND type_question = ?"
                " AND type_bloom = ? AND is_active = 1 ORDER BY version DESC LIMIT 1",
                (theme["lang"], type_question, type_bloom),
            )
            if gabarit is None:
                continue
            rendered = render(
                gabarit["template"],
                title=theme["title"],
                tags=tags or "aucun",
                count=per_run,
                source=theme["source_markdown"],
            )
            cur = conn.execute(
                "INSERT INTO exercise_prompt (theme_id, prompt_id, rendered_prompt,"
                " model, requested_count, status) VALUES (?, ?, ?, ?, ?, 'pending')",
                (theme_id, gabarit["id"], rendered, LLM_NAME, per_run),
            )
            run_ids.append(cur.lastrowid)

    if not run_ids:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Aucun gabarit actif pour ces types. Lance db/seed_prompts.sql.",
        )

    for run_id in run_ids:
        background.add_task(_run, run_id)

    return _status(conn, theme_id)


@router.get("/themes/{theme_id}/generation", response_model=GenerationStatusOut)
def generation_status(theme_id: int, conn: DbDep, user: CurrentUser) -> GenerationStatusOut:
    theme = _load(conn, theme_id, user["lang"])
    _require_owner(theme, user)
    return _status(conn, theme_id)


@router.get("/themes/{theme_id}/exercises", response_model=list[ExerciseOut])
def theme_exercises(
    theme_id: int, conn: DbDep, user: CurrentUser, state: str | None = None
) -> list[ExerciseOut]:
    """La pile à relire, dans l'ordre de production."""
    theme = _load(conn, theme_id, user["lang"])
    _require_owner(theme, user)
    sql = (
        "SELECT e.*, t.title AS theme_title, t.color AS theme_color, c.color AS category_color"
        " FROM exercise e JOIN theme t ON t.id = e.theme_id"
        " JOIN category c ON c.id = t.category_id WHERE e.theme_id = ?"
    )
    params: list = [theme_id]
    if state:
        sql += " AND e.state = ?"
        params.append(state)
    sql += " ORDER BY e.id"
    return [to_exercise_out(conn, e, user["id"]) for e in rows(conn, sql, params)]


@router.patch("/exercises/{exercise_id}", response_model=ExerciseOut)
def patch_exercise(
    exercise_id: int, payload: ExercisePatch, conn: DbDep, user: CurrentUser
) -> ExerciseOut:
    """Valider, écarter ou corriger un exercice relu."""
    e = _load_exercise(conn, exercise_id)
    theme = _load(conn, e["theme_id"], user["lang"])
    _require_owner(theme, user)

    fields = payload.model_dump(exclude_unset=True)
    if fields:
        with transaction(conn):
            sets = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(
                f"UPDATE exercise SET {sets} WHERE id = ?", (*fields.values(), exercise_id)
            )
            conn.execute(
                "UPDATE theme SET exercise_count ="
                " (SELECT COUNT(*) FROM exercise WHERE theme_id = ? AND state = 'validated')"
                " WHERE id = ?",
                (e["theme_id"], e["theme_id"]),
            )
    return to_exercise_out(conn, _load_exercise(conn, exercise_id), user["id"])
