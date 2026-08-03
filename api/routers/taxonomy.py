"""Catégories, sous-catégories, tags — ce que l'écran Paramètres liste."""

from __future__ import annotations

from fastapi import APIRouter

from ..db import rows
from ..schemas import CategoryOut, SubCategoryOut
from ..security import DbDep, OptionalUser

router = APIRouter(tags=["taxonomie"])


@router.get("/categories", response_model=list[CategoryOut])
def categories(conn: DbDep, user: OptionalUser) -> list[CategoryOut]:
    # La taxonomie est traduite : on retombe sur le libellé français si
    # la traduction manque, plutôt que d'afficher un trou.
    en = user is not None and user["lang"] == "en"
    label = "COALESCE(label_en, label)" if en else "label"
    lang = "en" if en else "fr"
    # Une catégorie sans lang vaut pour tout le monde ; « Français » et
    # « English » enseignent une langue donnée et n'ont de sens que dans
    # celle-ci. Sans ce filtre on proposait à la création une catégorie
    # dont les thèmes seraient ensuite écartés du catalogue, qui filtre
    # déjà sur la langue (voir /themes).
    cats = rows(
        conn,
        f"SELECT id, slug, {label} AS label, color FROM category"
        " WHERE lang IS NULL OR lang = ? ORDER BY position, label",
        (lang,),
    )
    subs = rows(
        conn,
        f"SELECT id, category_id, slug, {label} AS label, color FROM sub_category"
        " WHERE lang IS NULL OR lang = ? ORDER BY position, label",
        (lang,),
    )
    by_cat: dict[int, list[SubCategoryOut]] = {}
    for s in subs:
        by_cat.setdefault(s["category_id"], []).append(
            SubCategoryOut(id=s["id"], slug=s["slug"], label=s["label"], color=s["color"])
        )
    return [
        CategoryOut(
            id=c["id"],
            slug=c["slug"],
            label=c["label"],
            color=c["color"],
            sub_categories=by_cat.get(c["id"], []),
        )
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
    return [t["label"] for t in rows(conn, "SELECT label FROM tag ORDER BY label")]
