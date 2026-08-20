"""Création d'une connaissance à partir d'un sujet écrit par l'utilisateur.

Premier temps du pipeline : « les fonctions PHP » entre, il en sort un
titre, une description, une catégorie, un programme de trois à cinq
chapitres et des mots-clés. Le second temps — le prompt de chaque
chapitre — vient après validation, ailleurs.

TOUT EST ÉCRIT EN BASE IMMÉDIATEMENT, EN BROUILLON. Le thème naît
`private`, les chapitres `draft`, et une catégorie créée par le modèle
naît `draft` elle aussi : elle n'entre au catalogue qu'une fois retenue.
C'est ce qui permet de reprendre une création interrompue, et de garder
la trace de ce que le modèle a proposé même quand l'utilisateur le
corrige ensuite.

Rien n'est écrit tant que le modèle n'a pas répondu quelque chose
d'exploitable : un échec ne doit pas laisser un thème vide derrière lui.
"""

from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from .. import chapters as chapter_prompts
from ..config import LLM_NAME
from ..db import connection, row, rows, transaction
from ..llm import GenerationError, ask
from ..outline import build_prompt, parse
from ..schemas import (
    ChapterOut,
    ChapterPatch,
    GenerateFromChaptersIn,
    GenerationStatusOut,
    KnowledgeOut,
    OutlineIn,
)
from ..security import Author, CurrentUser, DbDep
from .generate import _run as run_generation
from .generate import _status as generation_status_of
from ..codes import unique_code
from .themes import _set_tags, slugify, unique_slug

router = APIRouter(tags=["connaissance"])

# Palette des catégories créées par le modèle. Il ne choisit pas de
# couleur — lui en demander une donnerait du #FF0000 sur fond crème. On
# tourne dans les teintes de la maquette, indexé sur l'identifiant, pour
# que deux catégories voisines ne sortent pas identiques.
PALETTE = ["#0A5C2C", "#1D4ED8", "#7C3AED", "#B45309", "#BE123C", "#0F766E"]


def _categories(conn: sqlite3.Connection, lang: str) -> list[dict]:
    """Les catégories que le modèle a le droit de désigner.

    Les brouillons en font partie : une catégorie proposée hier et pas
    encore retenue doit pouvoir accueillir le sujet d'aujourd'hui,
    sinon on en crée une jumelle à chaque dépôt.
    """
    return [
        dict(c)
        for c in rows(
            conn,
            "SELECT id, slug, label, label_en FROM category"
            " WHERE lang = ? ORDER BY status, position, id",
            (lang,),
        )
    ]


def _unique_category_slug(conn: sqlite3.Connection, base: str) -> str:
    slug = slugify(base)
    candidate, n = slug, 2
    while row(conn, "SELECT id FROM category WHERE slug = ?", (candidate,)) is not None:
        candidate, n = f"{slug}-{n}", n + 1
    return candidate


def _chapters_of(
    conn: sqlite3.Connection, theme_id: int, only: int | None = None
) -> list[ChapterOut]:
    out = []
    for c in rows(
        conn,
        "SELECT id, position, title, description, generated_prompt,"
        " type_question, example, status, error"
        " FROM chapter WHERE theme_id = ? AND (? IS NULL OR id = ?) ORDER BY position",
        (theme_id, only, only),
    ):
        data = dict(c)
        # `example` est du JSON en base — la colonne est un TEXT, et le
        # schéma de sortie attend un objet. Un exemple illisible ne doit
        # pas faire tomber la lecture du programme entier.
        raw = data.pop("example", None)
        try:
            data["example"] = json.loads(raw) if raw else None
        except (TypeError, ValueError):
            data["example"] = None
        out.append(ChapterOut(**data))
    return out


@router.post(
    "/knowledge/outline",
    response_model=KnowledgeOut,
    status_code=status.HTTP_201_CREATED,
)
async def outline(payload: OutlineIn, conn: DbDep, user: Author) -> KnowledgeOut:
    """Un sujet entre, une connaissance en brouillon en sort."""
    lang = payload.lang or user["lang"] or "fr"
    catalogue = _categories(conn, lang)

    try:
        raw = await ask(build_prompt(payload.subject, catalogue, lang))
        proposal = parse(raw, catalogue)
    except GenerationError as exc:
        # 502 et non 500 : ce n'est pas notre code qui a échoué, c'est le
        # service de génération. La distinction compte pour qui lit les
        # journaux, et pour le front qui peut proposer de réessayer.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    with transaction(conn):
        category_id = proposal["category_id"]
        category_is_new = False

        if category_id is None:
            label = proposal["category_label"] or payload.subject
            cur = conn.execute(
                "INSERT INTO category (slug, label, label_en, lang, color, position, status)"
                " VALUES (?, ?, ?, ?, ?,"
                "         (SELECT COALESCE(MAX(position), 0) + 1 FROM category),"
                "         'draft')",
                (
                    _unique_category_slug(conn, label),
                    label,
                    label,
                    lang,
                    PALETTE[len(catalogue) % len(PALETTE)],
                ),
            )
            category_id = cur.lastrowid
            category_is_new = True

        # Le code de partage se pose À LA CRÉATION, comme dans
        # `POST /themes`. Il manquait ici, et c'est par ici que passe la
        # création depuis l'app : tout apprentissage écrit avec le modèle
        # naissait donc sans code, donc sans lien à donner — alors que la
        # colonne est unique et qu'un code ne doit jamais changer une fois
        # distribué. Le rattraper après coup était possible ; ne pas
        # l'oublier est plus simple.
        cur = conn.execute(
            "INSERT INTO theme (category_id, owner_id, slug, title, description,"
            " lang, visibility, code) VALUES (?, ?, ?, ?, ?, ?, 'private', ?)",
            (
                category_id,
                user["id"],
                unique_slug(conn, proposal["title"]),
                proposal["title"],
                proposal["description"],
                lang,
                unique_code(conn),
            ),
        )
        theme_id = cur.lastrowid

        _set_tags(conn, theme_id, proposal["tags"])

        for position, chapter in enumerate(proposal["chapters"], start=1):
            conn.execute(
                "INSERT INTO chapter (theme_id, position, title, description, model, status)"
                " VALUES (?, ?, ?, ?, ?, 'draft')",
                (theme_id, position, chapter["title"], chapter["description"], LLM_NAME),
            )

    category = row(conn, "SELECT label FROM category WHERE id = ?", (category_id,))
    return KnowledgeOut(
        theme_id=theme_id,
        title=proposal["title"],
        description=proposal["description"],
        category_id=category_id,
        category_label=category["label"],
        category_is_new=category_is_new,
        tags=proposal["tags"],
        chapters=_chapters_of(conn, theme_id),
    )


def _owned(conn, theme_id: int, user: dict) -> dict:
    theme = row(
        conn,
        "SELECT t.*, c.label AS category_label, c.status AS category_status"
        " FROM theme t JOIN category c ON c.id = t.category_id WHERE t.id = ?",
        (theme_id,),
    )
    if theme is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connaissance introuvable.")
    if theme["owner_id"] != user["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce n'est pas votre connaissance.")
    return theme


async def _write_prompt(chapter_id: int) -> None:
    """Écrit le prompt d'un chapitre. Isolé : un échec n'emporte pas les autres.

    Chaque tâche ouvre sa propre connexion — celle de la requête est morte
    depuis longtemps quand la tâche de fond démarre.
    """
    with connection() as conn:
        ch = row(
            conn,
            "SELECT c.*, t.title AS theme_title, t.lang FROM chapter c"
            " JOIN theme t ON t.id = c.theme_id WHERE c.id = ?",
            (chapter_id,),
        )
        if ch is None:
            return
        # Repartir de zéro : une reprise après échec ne doit pas laisser
        # l'ancienne erreur affichée à côté du nouveau prompt.
        conn.execute(
            "UPDATE chapter SET error = NULL, generated_prompt = NULL WHERE id = ?",
            (chapter_id,),
        )

    try:
        raw = await ask(
            chapter_prompts.build_prompt(
                ch["theme_title"], ch["title"], ch["description"],
                ch["position"], ch["lang"],
            )
        )
        result = chapter_prompts.parse(raw)
    except Exception as exc:  # noqa: BLE001 — on trace tout, y compris l'imprévu
        with connection() as conn:
            conn.execute(
                "UPDATE chapter SET error = ? WHERE id = ?",
                (str(exc)[:1000], chapter_id),
            )
        return

    with connection() as conn:
        conn.execute(
            "UPDATE chapter SET generated_prompt = ?, type_question = ?,"
            " example = ?, model = ?, error = NULL WHERE id = ?",
            (
                # La langue va jusqu'au contrat : sans elle, des consignes
                # anglaises se referment sur un contrat français, et les
                # exercices sortent en français sous un titre anglais.
                chapter_prompts.compose(
                    result["instructions"], result["type_question"], lang=ch["lang"]
                ),
                result["type_question"],
                json.dumps(result["example"], ensure_ascii=False)
                if result["example"]
                else None,
                LLM_NAME,
                chapter_id,
            ),
        )


# Synchrone à dessein, comme `generate` : la connexion SQLite de la
# dépendance vit dans un thread du pool et ne peut pas franchir la boucle.
# Rien n'est attendu ici ; le travail long part en tâches de fond.
@router.post("/knowledge/{theme_id}/prompts", response_model=KnowledgeOut)
def write_prompts(
    theme_id: int,
    conn: DbDep,
    user: Author,
    background: BackgroundTasks,
    force: bool = False,
) -> KnowledgeOut:
    """Lance la rédaction d'un prompt par chapitre — un appel au modèle chacun.

    Par défaut, seuls les chapitres qui n'ont pas encore de prompt sont
    traités. C'est ce qui rend la relance après un échec partiel sans
    danger : réécrire les quatre chapitres réussis coûterait quatre
    appels pour rien, et surtout effacerait les corrections que l'auteur
    y aurait apportées entre-temps. `force=true` refait tout, en le
    sachant.
    """
    theme = _owned(conn, theme_id, user)

    pending = rows(
        conn,
        "SELECT id FROM chapter WHERE theme_id = ? AND status != 'rejected'"
        "   AND (? = 1 OR generated_prompt IS NULL) ORDER BY position",
        (theme_id, 1 if force else 0),
    )
    if not pending:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Rien à préparer : chaque chapitre a déjà son prompt. "
            "Relance avec force=true pour les réécrire.",
        )

    for ch in pending:
        background.add_task(_write_prompt, ch["id"])

    return _knowledge_out(conn, theme)


@router.post("/knowledge/{theme_id}/generate", response_model=GenerationStatusOut)
def generate_from_chapters(
    theme_id: int,
    payload: GenerateFromChaptersIn,
    conn: DbDep,
    user: Author,
    background: BackgroundTasks,
) -> GenerationStatusOut:
    """Écrit les exercices à partir des prompts de chapitre.

    Un lancement par chapitre, chacun citant son chapitre et non un
    gabarit : `exercise_prompt.rendered_prompt` reçoit le prompt tel
    qu'il a été écrit et relu. C'est ce qui permet, d'un exercice
    douteux, de remonter au chapitre ET au texte exact qui l'a commandé.

    Les chapitres écartés sont ignorés ; ceux qui n'ont pas de prompt
    aussi — leur préparation a échoué, les relancer ici ne produirait
    rien.
    """
    _owned(conn, theme_id, user)

    ready = rows(
        conn,
        "SELECT id, type_question, generated_prompt FROM chapter"
        " WHERE theme_id = ? AND status != 'rejected' AND generated_prompt IS NOT NULL"
        "   AND type_question IS NOT NULL ORDER BY position",
        (theme_id,),
    )
    if not ready:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Aucun chapitre prêt. Prépare les questions avant de lancer la rédaction.",
        )

    # Le volume demandé se répartit sur les chapitres retenus, au moins 1.
    per_run = max(1, payload.count // len(ready))

    run_ids: list[int] = []
    with transaction(conn):
        for ch in ready:
            cur = conn.execute(
                "INSERT INTO exercise_prompt (chapter_id, rendered_prompt,"
                " model, requested_count, status) VALUES (?, ?, ?, ?, 'pending')",
                (
                    ch["id"],
                    # Le nombre est dans le contrat, en fin de prompt : on
                    # le réécrit ici pour que le volume choisi à l'écran
                    # soit celui qui part au modèle.
                    chapter_prompts.recount(ch["generated_prompt"], per_run),
                    LLM_NAME,
                    per_run,
                ),
            )
            run_ids.append(cur.lastrowid)

    for run_id in run_ids:
        background.add_task(run_generation, run_id)

    return generation_status_of(conn, theme_id)


@router.patch("/chapters/{chapter_id}", response_model=ChapterOut)
def patch_chapter(
    chapter_id: int, payload: ChapterPatch, conn: DbDep, user: Author
) -> ChapterOut:
    """Corriger, retenir ou écarter un chapitre relu."""
    ch = row(conn, "SELECT theme_id FROM chapter WHERE id = ?", (chapter_id,))
    if ch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chapitre introuvable.")
    _owned(conn, ch["theme_id"], user)

    fields = payload.model_dump(exclude_unset=True)
    if fields:
        with transaction(conn):
            sets = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(
                f"UPDATE chapter SET {sets} WHERE id = ?", (*fields.values(), chapter_id)
            )

    return _chapters_of(conn, ch["theme_id"], only=chapter_id)[0]


@router.get("/knowledge/{theme_id}", response_model=KnowledgeOut)
def get_knowledge(theme_id: int, conn: DbDep, user: CurrentUser) -> KnowledgeOut:
    """Relire une connaissance en cours — c'est ce qui rend la reprise possible."""
    return _knowledge_out(conn, _owned(conn, theme_id, user))


def _knowledge_out(conn, theme: dict) -> KnowledgeOut:
    theme_id = theme["id"]
    return KnowledgeOut(
        theme_id=theme["id"],
        title=theme["title"],
        description=theme["description"],
        category_id=theme["category_id"],
        category_label=theme["category_label"],
        category_is_new=theme["category_status"] == "draft",
        tags=[
            t["label"]
            for t in rows(
                conn,
                "SELECT g.label FROM theme_tag tt JOIN tag g ON g.id = tt.tag_id"
                " WHERE tt.theme_id = ? ORDER BY g.label",
                (theme_id,),
            )
        ],
        chapters=_chapters_of(conn, theme_id),
    )
