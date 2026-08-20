"""CRUD des thèmes, abonnements et publication.

Un thème est privé à la création : c'est ce que dit l'écran Publication,
et c'est ce qui permet à quelqu'un de déposer son cours sans l'exposer.
Le passage en public demande une relecture, d'où l'état `pending`.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from ..config import FEED_TYPES
from ..db import row, rows, scalar, transaction
from ..schemas import PublishIn, ThemeIn, ThemeOut, ThemePatch
from ..codes import normalize as normalize_code, unique_code
from ..security import Author, CurrentUser, DbDep, OptionalUser
from ..topup import LOW_WATER, ecrire_et_traduire, unseen_count
from ..traduction import traduire_chapitre

router = APIRouter(tags=["thèmes"])


# --------------------------------------------------------------------------
# Le catalogue ne montre que le haut de l'arbre.
#
# Les 2 187 chapitres sont un arbre sur cinq étages : 11 racines, 172
# piliers, puis 651, 912 et 441 ramifications. Servis à plat, ils mettaient
# « Optics » et « Positional alcohol nystagmus » au même rang, dans la même
# colonne, rangés par ordre alphabétique — l'arbre existait en base et
# l'écran n'en montrait rien.
#
# On s'arrête donc à l'étage 1 : la racine du thème, et ses piliers. 183
# apprentissages au lieu de 2 187. Ce qui est plus bas reste en base, garde
# ses exercices et son abonnement — c'est le CATALOGUE qui se tait, pas la
# base.
#
# UNE SEULE EXCEPTION : `mine` ne filtre pas la profondeur. « Mes
# apprentissages » doit rendre ce qu'on suit, à l'étage où ça se trouve.
#
# Cette constante sert DEUX FOIS, et c'est le point : elle borne ce que le
# catalogue affiche, et elle borne ce qu'un abonnement ramasse tout seul
# (voir `_caches`). Une seule frontière — au-dessus on coche à la main, en
# dessous l'abonnement s'en charge. Deux valeurs différentes et les deux
# règles se contredisent : c'est arrivé, et ça affichait « Le Soleil · 228 »
# avec vingt piliers cochés que personne n'avait choisis.
# --------------------------------------------------------------------------
PROFONDEUR_MAX = 1


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


# --------------------------------------------------------------------------
# CE QUE `/themes` SERT, C'EST UN CHAPITRE.
#
# Le vocabulaire de l'IHM appelle « learning » ce que la route nomme
# thème. Depuis la reconstruction du catalogue, l'apprentissage qu'on
# suit et qu'on joue, c'est le CHAPITRE — un article de l'arbre de
# connaissance. Le thème, lui, est passé au-dessus : c'est la catégorie,
# l'un des jours de la création, servi par `/categories`.
#
#     catégorie  ←  theme    (11 lignes)
#     learning   ←  chapter  (2 187 lignes)
#
# La base avait déjà bougé : `attempt.chapter_id`, `user_chapter`,
# `exercise.chapter_id`, `v_user_chapter_progress`, `v_chapter_week_rank`.
# Seule l'API était restée sur `theme`, et elle joignait une table
# `category` supprimée — d'où le 500 sur toutes les routes de catalogue,
# et l'écran qui affichait « 0 learning · 0 category ».
#
# Ce qui a disparu avec l'ancien modèle, et vaut désormais une constante :
#   · les tags — les tables `tag` et `theme_tag` n'existent plus ;
#   · le propriétaire — un chapitre est semé par script, personne ne le
#     possède, donc `is_owner` est faux pour tout le monde ;
#   · la langue — anglais seul, décidé et non rouvert.
# --------------------------------------------------------------------------


def to_theme_out(conn: sqlite3.Connection, t: dict, user: dict | None) -> ThemeOut:
    subscribed = False
    if user is not None:
        subscribed = (
            row(
                conn,
                "SELECT 1 FROM user_chapter WHERE user_id = ? AND chapter_id = ?",
                (user["id"], t["id"]),
            )
            is not None
        )
    return ThemeOut(
        id=t["id"],
        slug=t["slug"],
        code=t["code"],
        # La traduction si elle existe, l'anglais sinon.
        title=t["title_traduit"] or t["title"],
        description=t["description_traduite"] or t["description"],
        # Le chapitre n'a pas de couleur : il prend celle de son thème,
        # ce qui donne au feed la couleur du jour dont il relève.
        color=t["category_color"],
        category_id=t["theme_id"],
        category_label=t["category_label_traduit"] or t["category_label"],
        visibility=t["visibility"],
        lang="en",
        exercise_count=t["exercise_count"],
        subscriber_count=t["subscriber_count"],
        prompt_count=t["prompt_count"] or 0,
        learner_count=t["learner_count"] or 0,
        child_count=t["child_count"] or 0,
        depth=t["depth"],
        parent_id=t["parent_id"],
        tags=[],
        is_owner=False,
        subscribed=subscribed,
    )


_SELECT = """
SELECT ch.*,
       th.title AS category_label,
       th.color AS category_color,
       -- Les titres dans la langue du lecteur, quand ils existent :
       -- ceux des chapitres viennent des liens de langue de Wikipédia,
       -- ceux des jours de la création sont écrits à la main (migration
       -- 025). `NULL` veut dire « pas d'article dans cette langue », et
       -- l'anglais reprend la main — un titre anglais juste vaut mieux
       -- qu'un titre français inventé.
       ct.title       AS title_traduit,
       ct.description AS description_traduite,
       tt.title       AS category_label_traduit,
       -- Combien de consignes de rédaction ce chapitre porte : une par
       -- section d'article qui a assez de matière pour une question. Les
       -- sections à zéro question entrent quand même, pour documenter le
       -- plan de l'article — les compter gonflerait le chiffre.
       (SELECT COUNT(*) FROM exercise_prompt p
         WHERE p.chapter_id = ch.id AND p.requested_count > 0) AS prompt_count,
       -- « Réalisé » veut dire « répondu ». Un exercice balayé sans
       -- réponse laisse une tentative à `chosen_index` nul : la compter
       -- gonflerait le chiffre de gens qui n'ont rien fait.
       (SELECT COUNT(DISTINCT a.user_id) FROM attempt a
         WHERE a.chapter_id = ch.id AND a.chosen_index IS NOT NULL) AS learner_count,
       -- Combien d'articles descendent directement de celui-ci. C'est le
       -- poids du sujet dans l'arbre : Wikipédia relie un article à
       -- d'autant plus d'articles qu'il en couvre. « Optics » en a 12,
       -- « Quantum optics » aucun — et c'est ce qui les range.
       --
       -- Les enfants DIRECTS, pas la descendance entière. Les deux ordres
       -- se défendent : « Land » a 13 enfants pour 48 descendants, « Ocean »
       -- 35 pour 35, et compter la descendance les inverserait.
       (SELECT COUNT(*) FROM chapter k
         WHERE k.parent_id = ch.id
           AND k.status != 'rejected'
           AND k.visibility = 'public') AS child_count
FROM chapter ch
JOIN theme th ON th.id = ch.theme_id
LEFT JOIN chapter_translation ct ON ct.chapter_id = ch.id AND ct.lang = ?
LEFT JOIN theme_translation   tt ON tt.theme_id   = th.id AND tt.lang = ?
"""
# CE SELECT PREND DEUX PARAMÈTRES, ET ILS VIENNENT EN PREMIER : la langue,
# deux fois, pour les deux jointures de traduction. Tout appelant doit
# donc passer `lang, lang` AVANT les paramètres de son propre WHERE.
# Oublier cette règle ne casse rien bruyamment — SQLite décale simplement
# les valeurs — d'où l'insistance.


def _lang(user: dict | None) -> str:
    return user["lang"] if user and user["lang"] in ("fr", "en") else "en"


def _load(conn: sqlite3.Connection, theme_id: int, lang: str = "en") -> dict:
    t = row(conn, _SELECT + " WHERE ch.id = ?", (lang, lang, theme_id))
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Apprentissage introuvable.")
    return t


def _caches(conn: sqlite3.Connection, chapter_id: int) -> list[int]:
    """La descendance QUE LE CATALOGUE NE MONTRE PAS.

    Tout ce qui pend sous ce chapitre en dessous de `PROFONDEUR_MAX` —
    donc jamais la racine d'un thème ni ses piliers, qui ont chacun leur
    ligne à l'écran.

    C'EST TOUTE LA RÈGLE : on ne coche jamais à la place de quelqu'un une
    ligne qu'il peut cocher lui-même.

    Avant, l'abonnement prenait la branche entière — les ancêtres et
    toute la descendance. Cliquer « Soleil » emportait ses 20 piliers et
    207 articles cachés : 228 abonnements d'un geste, et les 20 piliers
    s'affichaient cochés sans que personne les ait choisis. Cliquer
    « Océan » cochait « Terre », qui est juste au-dessus dans la même
    liste.

    Ce qui est caché, en revanche, doit bien être pris par quelqu'un :
    sans ça les 2 004 chapitres sous l'étage 1 seraient injoignables, et
    le feed n'aurait rien à servir passé les piliers. D'où la coupure
    exactement à `PROFONDEUR_MAX`, la même que celle du catalogue — une
    seule frontière, pas deux qui se contredisent.
    """
    return [
        r["id"]
        for r in rows(
            conn,
            "WITH RECURSIVE bas(id) AS ("
            "  SELECT id FROM chapter WHERE parent_id = ?"
            "  UNION"
            "  SELECT c.id FROM chapter c JOIN bas ON c.parent_id = bas.id)"
            " SELECT ch.id FROM bas JOIN chapter ch ON ch.id = bas.id"
            " WHERE ch.status != 'rejected' AND ch.visibility = 'public'"
            "   AND ch.depth > ?",
            (chapter_id, PROFONDEUR_MAX),
        )
    ]


def _recompter(conn: sqlite3.Connection, ids: list[int]) -> None:
    """Remet `subscriber_count` d'aplomb sur les chapitres touchés."""
    if not ids:
        return
    conn.execute(
        "UPDATE chapter SET subscriber_count ="
        " (SELECT COUNT(*) FROM user_chapter WHERE chapter_id = chapter.id)"
        f" WHERE id IN ({','.join('?' * len(ids))})",
        ids,
    )


def _require_owner(t: dict, user: dict) -> None:
    """Un chapitre n'appartient à personne : seul un admin passe.

    L'ancien modèle avait un auteur par thème, et c'est lui qui pouvait
    modifier, publier ou effacer. Le catalogue est désormais semé par
    script — `chapter` n'a pas de colonne `owner_id`, et il n'y aurait
    personne à y mettre. La garde reste, avec le seul droit qui subsiste.
    """
    if not user["is_admin"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Le catalogue est semé par script : personne n'en est propriétaire.",
        )


@router.get("/themes", response_model=list[ThemeOut])
def list_themes(
    conn: DbDep,
    user: OptionalUser,
    mine: bool = Query(default=False, description="Seulement mes apprentissages"),
) -> list[ThemeOut]:
    """Le catalogue : un apprentissage par chapitre publié.

    `mine` ne veut plus dire « ceux que j'ai créés » — personne ne crée,
    tout est semé par script. Il veut dire « ceux que je suis », lus dans
    `user_chapter`. C'est ce que l'écran « Mes apprentissages » demande,
    et c'est la seule lecture qui ait encore un sens.
    """
    lang = _lang(user)
    where = ["ch.status != 'rejected'", "ch.visibility = 'public'"]
    # La langue d'abord : les deux jointures de traduction sont en tête
    # du SELECT, donc leurs paramètres aussi.
    params: list = [lang, lang]
    if mine:
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Connexion requise.")
        where.append(
            "EXISTS (SELECT 1 FROM user_chapter uc"
            " WHERE uc.chapter_id = ch.id AND uc.user_id = ?)"
        )
        params.append(user["id"])
    else:
        # Le haut de l'arbre, et RIEN D'AUTRE — voir PROFONDEUR_MAX.
        #
        # Il y avait une exception ici : les chapitres déjà suivis
        # passaient quelle que soit leur profondeur, pour ne pas décrocher
        # trois abonnements antérieurs à la coupe. Elle s'est retournée
        # contre le reste dès que l'abonnement a pris la descendance
        # cachée — suivre « Soleil » faisait remonter ses 207 articles
        # cachés dans la liste, et « Le Soleil · 21 » devenait 228.
        #
        # Deux frontières qui se contredisaient. Il n'en reste qu'une :
        # le catalogue montre l'étage 0 et l'étage 1. Ce qu'on suit plus
        # bas se lit par `mine`, qui ne filtre pas la profondeur, et se
        # joue par le feed.
        where.append("ch.depth <= ?")
        params.append(PROFONDEUR_MAX)
    # Le poids d'abord : le nombre d'articles qui descendent de celui-ci.
    # L'ordre alphabétique mettait « Corpuscular theory of light » devant
    # « Optics » — un cul-de-sac de l'arbre devant un pilier qui en porte
    # 76. À poids égal, le titre AFFICHÉ tranche, pas l'anglais : une
    # liste française rangée dans l'ordre alphabétique anglais se lit
    # comme un désordre.
    #
    # ET L'ÉTAGE AVANT LE POIDS : l'article racine du thème passe en tête,
    # quel que soit son nombre d'enfants. Il les contient tous — 300 pour
    # « Terre » — et rangé au poids il tombait DEUXIÈME, derrière
    # « Océan » : les deux ont 35 enfants directs et l'alphabet tranchait.
    # Un parent au milieu de ses propres enfants se lit comme une ligne en
    # double, et c'est ce que 027 corrige de l'autre bout, par le nom.
    #
    # `ThemeOut` sert donc `depth`, et le front trie sur lui d'abord.
    # Deux ordres pour une même liste font que l'écran ne montre pas ce
    # que l'API a rangé — c'est déjà arrivé une fois ici.
    sql = (
        _SELECT
        + " WHERE " + " AND ".join(where)
        + " ORDER BY th.position, ch.depth,"
          " child_count DESC, COALESCE(ct.title, ch.title)"
    )
    return [to_theme_out(conn, t, user) for t in rows(conn, sql, params)]


@router.get("/themes/by-code/{code}", response_model=ThemeOut)
def theme_by_code(code: str, conn: DbDep, user: OptionalUser) -> ThemeOut:
    """Retrouver une connaissance par son code de partage.

    C'est LE SEUL endroit où la visibilité est franchie : un quiz privé
    se laisse ouvrir par qui détient son code. C'est le contrat du
    partage — « voici mon code, jouez-le » — et il n'a de sens que si le
    privé cesse d'être un mur pour celui qui l'a reçu.
    
    Le code est normalisé avant la recherche : on le recopie depuis un
    message ou un tableau, il arrive avec des espaces, des tirets ou en
    minuscules.

    La route est déclarée AVANT `/themes/{theme_id}` : sans ça, FastAPI
    ferait correspondre `by-code` au paramètre entier et répondrait 422.
    """
    clean = normalize_code(code)
    if not clean:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Code introuvable.")
    t = row(conn, _SELECT + " WHERE ch.code = ?", (_lang(user), _lang(user), clean))
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Code introuvable.")
    return to_theme_out(conn, t, user)


@router.get("/themes/{theme_id}", response_model=ThemeOut)
def get_theme(theme_id: int, conn: DbDep, user: OptionalUser) -> ThemeOut:
    t = _load(conn, theme_id, _lang(user))
    # Plus de propriétaire pour ouvrir une porte dérobée : un chapitre non
    # publié n'est visible de personne, sauf par son code de partage.
    if t["visibility"] != "public":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Apprentissage introuvable.")
    return to_theme_out(conn, t, user)


@router.post("/themes", response_model=ThemeOut, status_code=status.HTTP_201_CREATED)
def create_theme(payload: ThemeIn, conn: DbDep, user: Author) -> ThemeOut:
    if row(conn, "SELECT id FROM category WHERE id = ?", (payload.category_id,)) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Catégorie inconnue.")

    with transaction(conn):
        cur = conn.execute(
            "INSERT INTO theme (category_id, owner_id, slug, title,"
            " description, color, source_markdown, lang, visibility, code)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'private', ?)",
            (
                payload.category_id,
                user["id"],
                unique_slug(conn, payload.title),
                payload.title,
                payload.description,
                payload.color,
                payload.source_markdown,
                payload.lang,
                unique_code(conn),
            ),
        )
        theme_id = cur.lastrowid
        _set_tags(conn, theme_id, payload.tags)
    return to_theme_out(conn, _load(conn, theme_id, _lang(user)), user)


@router.patch("/themes/{theme_id}", response_model=ThemeOut)
def update_theme(
    theme_id: int, payload: ThemePatch, conn: DbDep, user: Author
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
def delete_theme(theme_id: int, conn: DbDep, user: Author) -> None:
    t = _load(conn, theme_id, _lang(user))
    _require_owner(t, user)
    with transaction(conn):
        # Les exercices, tentatives et abonnements suivent en cascade.
        conn.execute("DELETE FROM theme WHERE id = ?", (theme_id,))


@router.post("/themes/{theme_id}/publish", response_model=ThemeOut)
def publish(theme_id: int, payload: PublishIn, conn: DbDep, user: Author) -> ThemeOut:
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
def subscribe(
    theme_id: int, conn: DbDep, user: CurrentUser, background: BackgroundTasks
) -> ThemeOut:
    """Suivre un apprentissage — et, s'il est vide, l'écrire dès maintenant.

    Choisir un apprentissage est la première fois qu'on sait lequel
    intéresse quelqu'un. Le catalogue s'écrit à la demande : autant que
    la demande parte d'ici, pendant qu'on continue à parcourir la liste,
    plutôt que d'attendre l'écran d'exercice pour découvrir qu'il n'y a
    rien. Le feed écrit lui aussi, mais lui fait attendre — voir
    `routers/feed.py` : les deux portes sont voulues, celle-ci prend de
    l'avance, l'autre rattrape ce qui n'a pas été pris d'avance.

    En tâche de fond : la réponse ne doit pas mettre trente secondes pour
    un bouton « suivre ». `topup` porte son propre plafond quotidien, et
    une deuxième demande sur le même chapitre ne produit rien de plus.

    ON SUIT LE CHAPITRE ET CE QUI EST CACHÉ SOUS LUI — voir `_caches`.
    Jamais les lignes que le catalogue affiche : ni les ancêtres, ni les
    piliers d'une racine. Une ligne cochée à l'écran est une ligne que
    quelqu'un a cochée.

    « Optique » emporte donc ses 74 articles cachés, mais pas la racine
    « Lumière » qui est juste au-dessus dans la même liste. Et « Terre »
    emporte ses 265 articles cachés, pas ses 35 piliers.

    L'écriture ne suit PAS la descendance : `topup` ne part que sur le
    chapitre cliqué. Lancer une écriture par descendant, c'est 265 lots
    d'un coup — le plafond global de 60 lots par jour brûlé par un seul
    clic, et payé. Le feed écrira les autres au fur et à mesure qu'il y
    arrivera, deux par passage.
    """
    _load(conn, theme_id, _lang(user))
    # L'écriture emporte sa traduction — `ecrire_et_traduire` et non
    # `topup`. Les deux étaient posées côte à côte ici, et ça marchait
    # tant que rien ne ratait ; le jour où Google a coupé, le lot est
    # resté anglais sans que rien ne repasse dessus.
    if unseen_count(conn, theme_id, user["id"], FEED_TYPES) <= LOW_WATER:
        background.add_task(ecrire_et_traduire, theme_id)
    elif user["lang"] != "en":
        # Rien à écrire, mais peut-être de l'ancien à traduire.
        background.add_task(traduire_chapitre, theme_id, user["lang"])
    pris = [theme_id, *_caches(conn, theme_id)]
    with transaction(conn):
        conn.executemany(
            "INSERT OR IGNORE INTO user_chapter (user_id, chapter_id) VALUES (?, ?)",
            [(user["id"], cid) for cid in pris],
        )
        _recompter(conn, pris)
    return to_theme_out(conn, _load(conn, theme_id, _lang(user)), user)


@router.delete("/themes/{theme_id}/subscribe", response_model=ThemeOut)
def unsubscribe(theme_id: int, conn: DbDep, user: CurrentUser) -> ThemeOut:
    """Quitter un chapitre, et ce qui est caché sous lui.

    La descendance cachée part avec lui, sinon on ne pourrait plus se
    défaire de ce qu'un seul clic avait pris — 265 chapitres pour
    « Terre », qu'il faudrait quitter un par un sans même les voir dans le
    catalogue.

    SAUF CE QU'UN AUTRE ABONNEMENT JUSTIFIE ENCORE. Les arbres se
    chevauchent : suivre « Terre » ET « Océan » prend deux fois les
    articles sous « Océan ». Quitter « Terre » ne doit pas les emporter,
    « Océan » les demande toujours. On retire donc la descendance cachée
    du chapitre MOINS celle des chapitres encore suivis.

    Ce que ça ne sait pas distinguer : un article caché coché tout seul —
    par le code de partage, ou parce qu'il était suivi avant la coupe du
    catalogue — d'un article ramassé par un abonnement. `user_chapter` ne
    porte pas la raison, seulement le fait.
    """
    _load(conn, theme_id, _lang(user))
    partants = {theme_id, *_caches(conn, theme_id)}
    # Ce que les autres abonnements réclament encore.
    #
    # SEULS LES ABONNEMENTS VISIBLES COMPTENT, et c'est le point délicat.
    # Un abonnement à l'étage 0 ou 1 est un choix : quelqu'un a coché la
    # ligne. Tout ce qui est plus bas a été ramassé par `_caches`, jamais
    # coché — c'est une conséquence, pas une demande.
    #
    # Interroger tous les abonnements, comme je l'ai d'abord fait, rend la
    # suppression impossible : chaque article caché protège sa propre
    # descendance, donc se justifie en chaîne lui-même. Quitter « Terre »
    # laissait 94 articles derrière, gardés par leurs propres parents qui
    # partaient pourtant avec.
    garde: set[int] = set()
    for autre in rows(
        conn,
        "SELECT uc.chapter_id FROM user_chapter uc"
        "  JOIN chapter ch ON ch.id = uc.chapter_id"
        " WHERE uc.user_id = ? AND uc.chapter_id != ? AND ch.depth <= ?",
        (user["id"], theme_id, PROFONDEUR_MAX),
    ):
        garde.update(_caches(conn, autre["chapter_id"]))
    partants -= garde - {theme_id}
    with transaction(conn):
        conn.executemany(
            "DELETE FROM user_chapter WHERE user_id = ? AND chapter_id = ?",
            [(user["id"], cid) for cid in partants],
        )
        _recompter(conn, list(partants))
    return to_theme_out(conn, _load(conn, theme_id, _lang(user)), user)
