"""Catégories et tags — ce que l'écran Paramètres liste."""

from __future__ import annotations

from fastapi import APIRouter

from ..db import rows
from ..schemas import CategoryOut
from ..security import DbDep, OptionalUser

router = APIRouter(tags=["taxonomie"])


@router.get("/categories", response_model=list[CategoryOut])
def categories(conn: DbDep, user: OptionalUser) -> list[CategoryOut]:
    """Les catégories, ce sont les THÈMES — les six jours de la création.

    La table `category` a disparu avec la reconstruction du catalogue, et
    tout ce qui la joignait rendait 500 : l'écran affichait « 0 learning ·
    0 category » parce qu'il ne recevait rien, pas parce qu'il n'avait
    rien à montrer.

    La base avait déjà bougé sans l'API : `attempt.chapter_id`,
    `user_chapter`, `exercise.chapter_id` — tout est accroché au chapitre
    depuis les migrations 016 à 022. Le vocabulaire suit enfin :

        catégorie  ←  theme    (11 lignes, les jours de la création)
        learning   ←  chapter  (l'arbre de connaissance, voir /themes)

    Le titre suit la langue du lecteur quand il a été traduit. Les onze
    jours sont nommés à la main dans la migration 025 : ce sont des noms
    choisis, pas des traductions — « The Human Being » devient « L'Être
    humain » parce que quelqu'un l'a décidé, pas parce qu'une machine
    l'a rendu.
    """
    lang = user["lang"] if user and user["lang"] in ("fr", "en") else "en"
    cats = rows(
        conn,
        "SELECT th.id, th.slug, COALESCE(tt.title, th.title) AS label, th.color"
        "  FROM theme th"
        "  LEFT JOIN theme_translation tt ON tt.theme_id = th.id AND tt.lang = ?"
        " WHERE th.status = 'active' ORDER BY th.position, th.title",
        (lang,),
    )
    return [
        CategoryOut(id=c["id"], slug=c["slug"], label=c["label"], color=c["color"])
        for c in cats
    ]


@router.get("/credits")
def credits(conn: DbDep) -> dict:
    """Crédits des illustrations.

    Les SVG de panneaux français viennent de Wikimedia sous CC BY-SA :
    citer leurs auteurs n'est pas une politesse, c'est la condition de
    la licence. On la sert depuis la base plutôt que de la maintenir à
    la main dans le front, qui finirait par diverger.
    """
    return {
        "signs": rows(
            conn,
            "SELECT license, attribution, COUNT(*) AS count,"
            "       MIN(source_url) AS example_url, country"
            " FROM sign WHERE image_path IS NOT NULL"
            " GROUP BY license, attribution, country"
            " ORDER BY count DESC",
        )
    }


@router.get("/tags", response_model=list[str])
def tags(conn: DbDep) -> list[str]:
    """Plus de tags : les tables `tag` et `theme_tag` sont parties avec la
    reconstruction du catalogue, et rien ne les a remplacées — un
    apprentissage est rangé par son jour, ça suffit.

    La route reste, et rend une liste vide plutôt qu'un 500 : le client
    déployé la demande encore, et une erreur ici lui abîmait un écran
    pour une donnée qui n'existe plus.
    """
    return []
