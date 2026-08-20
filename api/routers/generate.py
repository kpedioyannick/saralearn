"""Exécution d'un lancement de rédaction, et relecture de ce qu'il produit.

Un lancement est une ligne `exercise_prompt` portant le texte exact
envoyé au modèle. Les exercices arrivent en `draft` : rien n'entre au
feed sans être relu.

La route qui créait ces lancements depuis un gabarit versionné a été
retirée avec la table `prompt` (migration 018). Ils naissent désormais
dans `knowledge.py`, à partir d'un chapitre, qui appelle `_run` ici.
"""

from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter

from ..db import connection, row, rows, scalar, transaction
from ..llm import GenerationError, ask, validate
from ..schemas import (
    ExerciseOut,
    ExercisePatch,
    GenerationRunOut,
    GenerationStatusOut,
)
from ..security import Author, CurrentUser, DbDep
from .feed import _load_exercise, to_exercise_out
from .themes import _load, _require_owner

router = APIRouter(tags=["génération"])


def _status(conn: sqlite3.Connection, theme_id: int) -> GenerationStatusOut:
    # Le thème d'un lancement se lit sur son chapitre depuis la 019 :
    # `exercise_prompt.theme_id` a été retiré, il doublait déjà
    # `chapter.theme_id`. JOIN fermé, `chapter_id` étant NOT NULL.
    # 'qcm' est le seul type encore produit.
    runs = rows(
        conn,
        "SELECT ep.id, ep.status, ep.requested_count, ep.produced_count, ep.error,"
        "       COALESCE(c.type_question, 'qcm') AS type_question"
        " FROM exercise_prompt ep"
        " JOIN chapter c ON c.id = ep.chapter_id"
        " WHERE c.theme_id = ? ORDER BY ep.id",
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
            "SELECT ep.*, COALESCE(c.type_question, 'qcm') AS type_question,"
            "       c.theme_id, t.lang"
            " FROM exercise_prompt ep"
            " JOIN chapter c ON c.id = ep.chapter_id"
            " JOIN theme t ON t.id = c.theme_id"
            " WHERE ep.id = ?",
            (run_id,),
        )
        if run is None:
            return
        conn.execute(
            "UPDATE exercise_prompt SET status = 'running' WHERE id = ?", (run_id,)
        )

    try:
        raw = await ask(run["rendered_prompt"])
        items = validate(raw, run["type_question"], run["lang"])
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
        with transaction(conn):
            for item in items:
                conn.execute(
                    "INSERT INTO exercise (theme_id, exercise_prompt_id, type_question,"
                    " prompt, body, options, correct_index,"
                    " ok_title, ok_line, ko_title, ko_line, exp_title, exp_text,"
                    " state)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'draft')",
                    (
                        run["theme_id"],
                        run_id,
                        run["type_question"],
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
                    ),
                )
            conn.execute(
                "UPDATE exercise_prompt SET status = 'done', produced_count = ?,"
                " finished_at = datetime('now') WHERE id = ?",
                (len(items), run_id),
            )


# `POST /themes/{id}/generate` était ici. Elle cherchait un gabarit actif
# dans `prompt`, table supprimée par la migration 018 — il n'en restait
# que deux coquilles inactives, et son message d'erreur renvoyait à
# `db/seed_prompts.sql`, fichier lui-même disparu du dépôt. Trois verrous
# la rendaient déjà inatteignable : aucun thème n'a de `source_markdown`,
# aucun gabarit n'était actif, aucun thème n'a de propriétaire.
#
# Créer un lancement se fait maintenant par `POST /knowledge/{id}/generate`,
# qui part d'un chapitre et appelle `_run` ci-dessus.


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
    # La jointure sur `sign` n'est pas décorative : `to_exercise_out` lit
    # `sign_image` et `sign_alt` sans valeur de repli. Sans elle, la pile
    # à relire renvoyait un 500 — la génération produisait bien, mais
    # l'auteur ne pouvait plus rien valider, et le thème se publiait vide.
    sql = (
        "SELECT e.*, t.title AS theme_title, t.color AS theme_color, c.color AS category_color,"
        " s.image_path AS sign_image, s.image_alt AS sign_alt"
        " FROM exercise e JOIN theme t ON t.id = e.theme_id"
        " JOIN category c ON c.id = t.category_id"
        " LEFT JOIN sign s ON s.id = e.sign_id WHERE e.theme_id = ?"
    )
    params: list = [theme_id]
    if state:
        sql += " AND e.state = ?"
        params.append(state)
    sql += " ORDER BY e.id"
    return [to_exercise_out(conn, e, user["id"]) for e in rows(conn, sql, params)]


@router.patch("/exercises/{exercise_id}", response_model=ExerciseOut)
def patch_exercise(
    exercise_id: int, payload: ExercisePatch, conn: DbDep, user: Author
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
