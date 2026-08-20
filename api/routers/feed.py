"""Le feed, et l'activité qui s'y rattache.

Sélection, dans l'ordre :
  1. les apprentissages suivis — à défaut, tout le catalogue public
     (l'app doit servir un exercice dès le premier lancement, sans
     réglage préalable) ;
  2. on écarte les N derniers exercices vus ;
  3. un raté revient d'abord, puis l'inédit, puis le déjà réussi ;
  4. on pondère vers les apprentissages les moins avancés ;
  5. tirage aléatoire.

**Un apprentissage est un CHAPITRE.** Le vocabulaire de l'API a une
génération de retard sur la base : `ExerciseOut.theme_id` porte un
`chapter_id`, et `theme` le titre du chapitre — c'est ce que le front
appelle « learning ». La « catégorie » du sélecteur, elle, est le thème :
l'un des jours de la création, qui donne sa couleur à la carte. Voir
`routers/taxonomy.py`, qui a posé cette correspondance.

Pas d'algorithme adaptatif : ça viendra si le besoin se montre.

## L'écriture à la demande, ici et pas ailleurs

Le catalogue est vide par construction — 2 187 chapitres, leur source en
base, et presque aucune question. Écrire les 20 000 exercices d'avance
coûterait des heures d'appels pour un catalogue que personne n'a joué :
un chapitre s'écrit le jour où quelqu'un l'ouvre. Voir `api/topup.py`.

Ce fichier est le seul endroit où ça se déclenche, et il le fait de deux
manières, qui ne se remplacent pas :

  · **en tâche de fond**, quand il reste peu d'inédit — l'élève ne voit
    rien, la recharge arrive avant qu'il touche le fond ;
  · **dans la requête, en attendant sa fin**, quand il n'y a RIEN
    d'inédit à servir. C'est le cas du premier lancement et celui de
    l'apprentissage qu'on vient de choisir : renvoyer une liste vide
    laissait l'écran sur « on prépare tes exercices… » pour toujours,
    puisque rien, côté client, ne redemande le flux. Alors on prépare
    vraiment, et le message dit enfin ce qui se passe. Une trentaine de
    secondes, derrière l'écran d'attente.

## La langue de la carte rendue

Le catalogue est écrit en anglais, le français est une traduction gardée
en cache (`api/traduction.py`). Ce fichier a longtemps servi ce qu'il
avait sous la main, l'anglais compris, et ça se voyait : on lisait en
français, le chapitre s'épuisait, le moteur en écrivait d'autres, et
l'écran basculait en anglais d'un coup. Le client garde ses cinq cartes
préchargées pour toute la session — la traduction qui arrivait quarante
secondes plus tard ne rattrapait rien.

Trois gestes, du moins cher au plus cher, et dans cet ordre :

  · le tri relègue en dernier ce qui n'est pas traduit (`_trad_order`) ;
  · `_garantir_les_premieres` traduit DANS LA REQUÊTE les deux premières
    cartes — celle qu'on affiche et celle qu'on précharge. Une dizaine
    de secondes chacune, et seulement quand elles manquent ;
  · `_seulement_lisibles` écarte de la page ce qui reste en anglais.

Sauf si tout est en anglais : on rend alors l'anglais plutôt que rien.
Un écran d'attente sans sortie est pire qu'une question qu'on comprend
mal — c'est la règle qui tient tout ce fichier.
"""

from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from ..codes import normalize as normalize_code
from ..config import FEED_RECENT_WINDOW, FEED_TYPES
from ..db import row, rows, scalar, transaction
from ..schemas import (
    AttemptIn,
    AttemptOut,
    CommentIn,
    CommentOut,
    ExerciseOut,
    StepOut,
    OptionOut,
    VoteIn,
)
from ..security import CurrentUser, DbDep
from ..topup import (
    BATCH_INLINE,
    DAILY_CAP,
    LOW_WATER,
    ecrire_et_traduire,
    topup,
    unseen_count,
)
from ..traduction import (
    LANGUE_SOURCE,
    manque_la_traduction,
    traduire_chapitre,
    traduire_exercices,
)

router = APIRouter(tags=["feed"])


def to_exercise_out(
    conn: sqlite3.Connection, e: dict, user_id: int | None, lang: str = "en"
) -> ExerciseOut:
    e = _dans_la_langue(conn, e, lang)
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
        # `theme_id` côté client = le chapitre, l'unité qu'on suit et qu'on
        # partage. C'est ce que renvoie déjà `/themes`.
        theme_id=e["chapter_id"],
        theme=e["chapter_title"],
        # Le chapitre n'a pas de couleur : il prend celle de son jour.
        color=e["day_color"] or "#0A5C2C",
        type_question=e["type_question"],
        prompt=e["prompt"],
        body=e["body"],
        # La photo d'ambiance passe DEVANT le pictogramme : `sign` est le
        # vestige du catalogue de panneaux routiers, vide depuis que ses
        # SVG ont été perdus, et `image_url` est ce qui se remplit
        # aujourd'hui. Voir `api/photos.py`.
        image=e["image_url"] or e["sign_image"],
        image_alt=e["image_alt"] if e["image_url"] else e["sign_alt"],
        image_credit=e["image_credit"],
        image_credit_url=e["image_credit_url"],
        image_source=e["image_source"],
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
        steps=_etapes(conn, e["id"], lang),
        up_count=e["up_count"],
        down_count=e["down_count"],
        my_vote=my_vote,
        comment_count=comment_count or 0,
        state=e["state"],
    )


def _etapes(conn: sqlite3.Connection, exercise_id: int, lang: str) -> list[StepOut]:
    """Les étapes de l'explication, traduites quand elles le sont.

    LA TRADUCTION EST JOINTE, PAS CHERCHÉE À PART : une étape non
    traduite tomberait sinon en anglais au milieu d'une carte française,
    et c'est précisément la bascule dont se plaignait le lecteur. Ici le
    repli est explicite et se voit — `COALESCE` sur le texte source.

    L'IMAGE, ELLE, NE SE TRADUIT PAS. Elle est la même dans toutes les
    langues, ce qui suppose qu'aucun mot ne soit écrit dessus : c'est
    une règle du titre d'image, pas un hasard.
    """
    lignes = rows(
        conn,
        "SELECT COALESCE(t.texte, s.texte) AS texte, s.image_url, s.image_alt,"
        "       s.image_credit, s.image_credit_url, s.image_source"
        "  FROM exercise_step s"
        "  LEFT JOIN exercise_step_translation t"
        "    ON t.exercise_id = s.exercise_id AND t.rang = s.rang AND t.lang = ?"
        " WHERE s.exercise_id = ?"
        " ORDER BY s.rang",
        (lang, exercise_id),
    )
    return [
        StepOut(
            text=r["texte"],
            image=r["image_url"],
            image_alt=r["image_alt"],
            image_credit=r["image_credit"],
            image_credit_url=r["image_credit_url"],
            image_source=r["image_source"],
        )
        for r in lignes
    ]


# Les champs qu'une traduction remplace. `correct_index` n'y est pas, et
# ne doit jamais y être : c'est une position dans le tableau d'options,
# elle appartient à l'original — voir `api/traduction.py`.
_CHAMPS_TRADUITS = (
    "prompt",
    "body",
    "options",
    "ok_title",
    "ok_line",
    "ko_title",
    "ko_line",
    "exp_title",
    "exp_text",
)


def _lang(user: dict | None) -> str:
    """La langue de lecture. Anglais par défaut : c'est celle du catalogue."""
    if user is None:
        return "en"
    return user["lang"] if user["lang"] in ("fr", "en") else "en"


def _dans_la_langue(conn: sqlite3.Connection, e: dict, lang: str) -> dict:
    """L'exercice dans la langue du lecteur, ou tel quel.

    Une requête par carte plutôt qu'une jointure dans le grand SELECT :
    ce SELECT sert quatre appelants avec des paramètres positionnels
    différents, et y glisser la langue rendait chaque liste de paramètres
    dépendante de l'ordre des jointures. Cinq lectures par index sur une
    base locale ne se mesurent pas ; une erreur de décalage de paramètre,
    si.

    Le repli sur l'anglais est le DERNIER recours, et il ne se voit plus
    guère : `_garantir_les_premieres` traduit dans la requête ce qui
    manque aux premières cartes, et `_seulement_lisibles` écarte le
    reste. Il ne reste debout que pour le cas où tout a échoué — mieux
    vaut la question en anglais que pas de question.
    """
    if lang == "en":
        return e
    # Le titre du chapitre voyage avec la carte : c'est la pastille
    # affichée sous la question, et elle jurait en anglais au milieu d'un
    # exercice français.
    titre = row(
        conn,
        "SELECT title FROM chapter_translation WHERE chapter_id = ? AND lang = ?",
        (e["chapter_id"], lang),
    )
    if titre is not None:
        e = {**e, "chapter_title": titre["title"]}
    t = row(
        conn,
        "SELECT prompt, body, options, ok_title, ok_line, ko_title, ko_line,"
        "       exp_title, exp_text"
        "  FROM exercise_translation WHERE exercise_id = ? AND lang = ?",
        (e["id"], lang),
    )
    if t is None:
        return e
    return {**e, **{champ: t[champ] for champ in _CHAMPS_TRADUITS}}


# Ce que CET élève a déjà fait de chaque exercice : combien de fois, et
# combien de fois juste. C'est ce qui permet de faire revenir un raté.
# `MAX(id)` et non un décompte : ce qui compte est le DERNIER passage,
# pas l'historique. « Si exercice ko on ressert » veut dire « je viens de
# me tromper », pas « je me suis trompé un jour ». Un exercice raté puis
# réussi quatre fois n'a plus rien à réviser — avec un décompte de
# réussites il restait pourtant classé « déjà su », et avec un décompte
# d'échecs il serait revenu pour toujours.
#
# SQLite rend les colonnes nues de la ligne qui porte le MAX : `last_ok`
# est donc bien la correction de la dernière tentative.
_SEEN = (
    " LEFT JOIN (SELECT exercise_id, COUNT(*) AS n, MAX(id) AS last_id,"
    " is_correct AS last_ok"
    " FROM attempt WHERE user_id = ? GROUP BY exercise_id) seen"
    " ON seen.exercise_id = e.id"
)

_SELECT = """
SELECT e.*, ch.title AS chapter_title, ch.visibility AS chapter_visibility,
       th.color AS day_color,
       s.image_path AS sign_image, s.image_alt AS sign_alt
FROM exercise e
JOIN chapter ch ON ch.id = e.chapter_id
JOIN theme   th ON th.id = ch.theme_id
LEFT JOIN sign s ON s.id = e.sign_id
"""


# Combien de cartes on garantit traduites AVANT de répondre. Deux : le
# client affiche la première et précharge la suivante, et une carte coûte
# une quinzaine d'appels à Google, soit une dizaine de secondes.
#
# C'est le dernier filet, et il ne sert presque jamais : l'écriture
# traduit derrière elle (`topup.ecrire_et_traduire`) et le tri relègue le
# non-traduit en dernier. Il ne se déclenche donc que sur le chemin
# bloquant — un chapitre écrit et servi dans la même requête — ou après
# une coupure de Google. C'est justement là que l'élève basculait en
# anglais sans comprendre pourquoi.
TRAD_INLINE_MAX = 2


def _trad_join(lang: str) -> str:
    """La jointure qui dit si la carte est lisible par ce lecteur.

    Elle prend UN paramètre, et il vient juste après ceux de `_SEEN` :
    l'ordre des `?` suit l'ordre des jointures dans le SQL, et ce fichier
    a déjà payé une fois pour l'avoir oublié.
    """
    if lang == LANGUE_SOURCE:
        return ""
    return " LEFT JOIN exercise_translation tr ON tr.exercise_id = e.id AND tr.lang = ?"


def _trad_params(lang: str) -> list:
    return [] if lang == LANGUE_SOURCE else [lang]


def _trad_order(lang: str) -> str:
    """Le non-traduit en dernier — APRÈS la clé pédagogique, jamais avant.

    Un exercice raté doit revenir même s'il n'est pas encore traduit :
    ce qu'on révise passe avant ce qui se lit bien. La langue ne
    départage qu'à statut égal.
    """
    if lang == LANGUE_SOURCE:
        return ""
    return " CASE WHEN tr.exercise_id IS NULL THEN 1 ELSE 0 END,"


# LA CARTE ILLUSTRÉE PASSE DEVANT LA CARTE NUE — et jamais plus que ça.
#
# La photo arrive EN DERNIER dans la chaîne d'écriture : le lot est
# écrit, puis traduit, puis illustré. Trois minutes séparent la première
# étape de la dernière, et pendant ces trois minutes le feed servait les
# cartes fraîches telles quelles. Le 20/08/2026, un lecteur est tombé
# sur la carte 420 à cet instant précis et a demandé pourquoi elle
# n'avait pas d'image : elle en a eu une quatre minutes plus tard.
#
# On NE LES ÉCARTE PAS, contrairement au non-traduit. Une carte sans
# photo se lit et s'y répond ; c'est le décor qui manque, pas la
# question. Les reléguer en fin de tri suffit à refermer la fenêtre :
# tant qu'il reste une carte illustrée à servir, c'est elle qui part, et
# les fraîches attendent leur photo. Quand il n'en reste plus, elles
# passent quand même — un écran d'attente serait pire, c'est la règle de
# tout ce fichier.
#
# Ce fragment vient APRÈS la langue, donc après la clé pédagogique : ce
# qu'on révise passe avant ce qui se lit bien, qui passe avant ce qui
# est joli.
_PHOTO_ORDER = " CASE WHEN e.image_url IS NULL THEN 1 ELSE 0 END,"


def _types_clause(prefix: str = "e.") -> str:
    """Le filtre de type, ou rien s'il n'y a pas de filtre."""
    if not FEED_TYPES:
        return ""
    return f" AND {prefix}type_question IN ({','.join('?' * len(FEED_TYPES))})"


def _by_code(
    conn: sqlite3.Connection,
    chapter_id: int,
    uid: int,
    n: int,
    exclude: list[int],
    lang: str = LANGUE_SOURCE,
) -> list[dict]:
    """Les exercices d'un seul apprentissage, ouvert par son code.

    Le filtre de type s'applique ici aussi : ce qu'on a décidé de ne pas
    servir ne doit pas revenir par la porte du partage.
    """
    clauses = ["e.state = 'validated'", "e.chapter_id = ?"]
    params: list = [chapter_id]
    if FEED_TYPES:
        clauses.append(f"e.type_question IN ({','.join('?' * len(FEED_TYPES))})")
        params += list(FEED_TYPES)
    if exclude:
        clauses.append(f"e.id NOT IN ({','.join('?' * len(exclude))})")
        params += exclude
    # Le même ordre que le flux normal — raté, puis inédit, puis réussi.
    # Il manquait ici, et c'est justement sur un quiz partagé qu'il
    # compte le plus : quatre questions, on repasse dessus tout de suite,
    # et sans cet ordre on retombe au hasard sur ce qu'on savait déjà.
    sql = (
        _SELECT
        + _SEEN
        + _trad_join(lang)
        + " WHERE " + " AND ".join(clauses)
        + " ORDER BY CASE"
        + "   WHEN seen.exercise_id IS NULL THEN 1"
        + "   WHEN seen.last_ok = 0 THEN 0"
        + "   ELSE 2 END,"
        + _trad_order(lang)
        + _PHOTO_ORDER
        + " ABS(RANDOM() % 1000) LIMIT ?"
    )
    return rows(conn, sql, [uid, *_trad_params(lang), *params, n])


@router.get("/feed", response_model=list[ExerciseOut])
async def feed(
    conn: DbDep,
    user: CurrentUser,
    background: BackgroundTasks,
    n: int = Query(default=5, ge=1, le=20),
    code: str | None = Query(default=None, max_length=32),
) -> list[ExerciseOut]:
    uid = user["id"]
    lang = _lang(user)

    # Un code de partage ferme le flux sur un seul apprentissage, même
    # privé. Il court-circuite tout le reste — abonnements, catalogue
    # public, replis : on a demandé CE quiz, on ne sert que lui, et on
    # renvoie une liste vide plutôt que d'y glisser autre chose.
    if code:
        clean = normalize_code(code)
        ch = row(conn, "SELECT id FROM chapter WHERE code = ?", (clean,)) if clean else None
        if ch is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Code introuvable.")
        seen = _recent(conn, uid)
        only = _by_code(conn, ch["id"], uid, n, seen, lang)
        # Le stock d'un seul quiz est vite plus petit que la fenêtre
        # anti-répétition : on rouvre plutôt que de rendre le vide.
        if not only:
            only = _by_code(conn, ch["id"], uid, n, [], lang)
        # Un quiz partagé qui n'a pas encore de questions s'écrit ici, tout
        # de suite : celui qui a suivi le lien n'a rien d'autre à voir.
        if not only and await _ecrire_maintenant(conn, [ch["id"]]):
            only = _by_code(conn, ch["id"], uid, n, [], lang)
        await _garantir_les_premieres(conn, only, lang)
        only = _seulement_lisibles(conn, only, lang)
        _maybe_topup(conn, background, ch["id"], uid)
        _maybe_traduire(background, ch["id"], lang)
        return [to_exercise_out(conn, e, uid, lang) for e in only]

    # Les apprentissages suivis. `user_chapter` porte des chapitres — plus
    # de filtre par langue : le catalogue est en anglais seul.
    subscribed = [
        r["chapter_id"]
        for r in rows(conn, "SELECT chapter_id FROM user_chapter WHERE user_id = ?", (uid,))
    ]

    recent = _recent(conn, uid)

    where = ["e.state = 'validated'"]
    params: list = []

    # Les types servis. On filtre plutôt que de supprimer : les exercices
    # écartés restent en base et reviennent en changeant `FEED_TYPES`.
    if FEED_TYPES:
        where.append(f"e.type_question IN ({','.join('?' * len(FEED_TYPES))})")
        params += list(FEED_TYPES)
    if subscribed:
        where.append(f"e.chapter_id IN ({','.join('?' * len(subscribed))})")
        params += subscribed
    else:
        # Premier lancement : rien n'est encore choisi, on sert le public.
        where.append("ch.visibility = 'public'")

    def query(exclude: list[int]) -> list[dict]:
        clauses = list(where)
        local = list(params)
        if exclude:
            clauses.append(f"e.id NOT IN ({','.join('?' * len(exclude))})")
            local += exclude
        # La pondération : moins un apprentissage est avancé, plus il
        # remonte. COALESCE parce qu'un chapitre jamais commencé n'a pas
        # de ligne dans la vue de progression — et c'est justement
        # celui-là qu'on veut proposer en premier.
        #
        # Le bruit va jusqu'à 999 et non jusqu'à 3 : avec seulement
        # quatre valeurs possibles, presque tous les exercices avaient la
        # même clé de tri, et SQLite départageait dans l'ordre de la
        # table. Le feed servait donc toujours les mêmes.
        # L'ordre demandé : un exercice raté revient d'abord, puis ce
        # qui n'a jamais été vu, puis le reste. Avant, tout était tiré au
        # hasard pondéré par l'avancement — une question ratée avait
        # exactement autant de chances de revenir qu'une réussie, ce qui
        # n'apprend rien à personne.
        sql = (
            _SELECT
            + " LEFT JOIN v_user_chapter_progress p"
            + "   ON p.chapter_id = e.chapter_id AND p.user_id = ?"
            + _SEEN
            + _trad_join(lang)
            + " WHERE " + " AND ".join(clauses)
            + " ORDER BY CASE"
            + "   WHEN seen.exercise_id IS NULL THEN 1"      # jamais vu
            + "   WHEN seen.last_ok = 0 THEN 0"              # raté au dernier passage
            + "   ELSE 2 END,"                               # déjà réussi
            + _trad_order(lang)                              # lisible d'abord
            + _PHOTO_ORDER                                   # illustrée ensuite
            + " (COALESCE(p.pct, 0) / 25) * 250 + ABS(RANDOM() % 1000)"
            + " LIMIT ?"
        )
        return rows(conn, sql, [uid, uid, *_trad_params(lang), *local, n])

    def complete(picked: list[dict]) -> list[dict]:
        """Compléter avec du déjà-vu quand l'inédit ne suffit pas.

        Le stock est plus petit que la fenêtre anti-répétition : on
        rouvre plutôt que de renvoyer une liste courte.
        """
        if len(picked) >= n:
            return picked
        seen = {e["id"] for e in picked}
        for e in query([]):
            if e["id"] not in seen:
                picked.append(e)
                seen.add(e["id"])
            if len(picked) >= n:
                break
        return picked

    picked = complete(query(recent))

    # L'écriture à la demande. La condition n'est pas « la liste est
    # vide » mais « il ne reste RIEN d'inédit » : servir pour la
    # cinquième fois les mêmes neuf questions n'est pas plus un flux
    # qu'un écran blanc, et c'est exactement ce que vit celui qui vient
    # de choisir un apprentissage jamais écrit.
    if _reste_a_voir(conn, uid, subscribed) == 0:
        cibles = _chapitres_a_ecrire(conn, uid, subscribed)
        if await _ecrire_maintenant(conn, cibles):
            picked = complete(query(recent))

    # Le repli quand les abonnements ne donnent RIEN.
    #
    # On peut suivre des apprentissages qui n'ont aucun exercice — c'est
    # même l'état normal du catalogue, qui s'écrit à la demande. Le feed
    # partait alors sur une liste vide sans jamais en sortir, et l'app
    # restait sur « on prépare tes exercices… » pour toujours. Suivre un
    # apprentissage ne doit pas pouvoir éteindre le flux : on sert le
    # catalogue public en attendant que l'écriture aboutisse.
    if not picked and subscribed:
        sql = (
            _SELECT
            + " LEFT JOIN v_user_chapter_progress p"
            + "   ON p.chapter_id = e.chapter_id AND p.user_id = ?"
            + " WHERE e.state = 'validated' AND ch.visibility = 'public'"
            + _types_clause()
            + " ORDER BY"
            + _PHOTO_ORDER
            + " (COALESCE(p.pct, 0) / 25) * 250 + ABS(RANDOM() % 1000)"
            + " LIMIT ?"
        )
        picked = rows(conn, sql, [uid, *FEED_TYPES, n])

    # « Des exercices illimités » : quand un apprentissage n'a presque
    # plus rien d'inédit pour cet élève, on en fabrique pendant qu'il
    # répond. Le déclenchement se fait sur le chapitre de la PROCHAINE
    # carte : c'est celui qu'il va épuiser, et attendre la panne sèche
    # rendrait l'attente visible.
    if picked:
        _maybe_topup(conn, background, picked[0]["chapter_id"], uid)
        # La traduction, elle, part sur TOUS les chapitres de la page, et
        # pas seulement celui de la prochaine carte. Le flux saute d'un
        # apprentissage à l'autre — cinq cartes viennent couramment de
        # trois ou quatre chapitres — donc ne préparer que le premier
        # laissait le lecteur en anglais indéfiniment : le chapitre
        # traduit ne revenait presque jamais. `traduire_chapitre` se
        # garde des doublons et porte son plafond quotidien, donc
        # demander quatre fois ne coûte pas quatre fois.
        for chapter_id in dict.fromkeys(e["chapter_id"] for e in picked):
            _maybe_traduire(background, chapter_id, lang)

    # Les deux derniers filets, et les seuls qui portent sur LES CARTES
    # QU'ON REND : garantir les premières, écarter celles qui ne le sont
    # pas encore.
    await _garantir_les_premieres(conn, picked, lang)
    picked = _seulement_lisibles(conn, picked, lang)
    return [to_exercise_out(conn, e, uid, lang) for e in picked]


def _recent(conn: sqlite3.Connection, uid: int) -> list[int]:
    """Les derniers exercices vus, qu'on écarte du tirage."""
    return [
        r["exercise_id"]
        for r in rows(
            conn,
            "SELECT DISTINCT exercise_id FROM attempt WHERE user_id = ?"
            " ORDER BY created_at DESC LIMIT ?",
            (uid, FEED_RECENT_WINDOW),
        )
    ]


def _reste_a_voir(conn: sqlite3.Connection, uid: int, subscribed: list[int]) -> int:
    """Combien d'exercices cet élève n'a JAMAIS vus, dans son périmètre.

    Le périmètre est celui du flux : ses apprentissages s'il en suit,
    tout le public sinon. À zéro, il n'y a plus rien à lui montrer — et
    c'est là, et seulement là, qu'on paye une écriture dans la requête.
    """
    sql = (
        "SELECT COUNT(*) FROM exercise e JOIN chapter ch ON ch.id = e.chapter_id"
        " WHERE e.state = 'validated'"
        " AND NOT EXISTS (SELECT 1 FROM attempt a"
        "                  WHERE a.exercise_id = e.id AND a.user_id = ?)"
    )
    params: list = [uid]
    if subscribed:
        sql += f" AND e.chapter_id IN ({','.join('?' * len(subscribed))})"
        params += subscribed
    else:
        sql += " AND ch.visibility = 'public'"
    sql += _types_clause()
    params += list(FEED_TYPES)
    return scalar(conn, sql, tuple(params)) or 0


# Combien de chapitres on accepte d'essayer dans une même requête. Deux :
# une écriture prend une trentaine de secondes, et Apache coupe à 300.
# Le premier qui produit quelque chose arrête la boucle.
INLINE_MAX = 2


def _chapitres_a_ecrire(
    conn: sqlite3.Connection, uid: int, subscribed: list[int]
) -> list[int]:
    """Les chapitres à écrire en premier, dans l'ordre où on les essaiera.

    Trois conditions, toutes nécessaires :

      · une source en base — sans article, `topup` ne produira rien et on
        aurait attendu pour rien ;
      · le plafond du jour pas atteint, sinon on relance une écriture qui
        rendra zéro ;
      · rien d'inédit à servir dessus, sinon il n'y avait pas besoin
        d'écrire.

    L'ordre met devant l'apprentissage le moins fourni : celui qu'on
    vient de choisir et qui n'a rien passe avant celui qui a déjà de quoi
    tenir. À égalité, l'ordre du catalogue — les jours de la création
    dans leur ordre, et l'arbre du thème dans le sien.
    """
    sql = (
        "SELECT ch.id FROM chapter ch JOIN theme th ON th.id = ch.theme_id"
        " WHERE ch.status = 'validated'"
        " AND EXISTS (SELECT 1 FROM exercise_prompt p WHERE p.chapter_id = ch.id"
        "              AND p.content IS NOT NULL AND p.requested_count > 0)"
        " AND (SELECT COUNT(*) FROM exercise_prompt p2 WHERE p2.chapter_id = ch.id"
        "       AND p2.model = 'topup' AND date(p2.created_at) = date('now')) < ?"
        " AND NOT EXISTS (SELECT 1 FROM exercise e WHERE e.chapter_id = ch.id"
        "                  AND e.state = 'validated'"
        "                  AND NOT EXISTS (SELECT 1 FROM attempt a"
        "                                   WHERE a.exercise_id = e.id AND a.user_id = ?))"
    )
    params: list = [DAILY_CAP, uid]
    if subscribed:
        sql += f" AND ch.id IN ({','.join('?' * len(subscribed))})"
        params += subscribed
    else:
        sql += " AND ch.visibility = 'public'"
    sql += " ORDER BY ch.exercise_count, th.position, ch.depth, ch.position, ch.id LIMIT ?"
    params.append(INLINE_MAX)
    return [r["id"] for r in rows(conn, sql, params)]


async def _ecrire_maintenant(conn: sqlite3.Connection, cibles: list[int]) -> int:
    """Écrit un lot et n'en sort qu'une fois qu'il est en base.

    C'est le seul appel bloquant de l'API. Il est assumé : l'écran
    d'attente du client dit « on prépare tes exercices », et il n'a
    aucune façon de redemander le flux tout seul — répondre vide, c'est
    l'y laisser pour de bon.

    IL DEMANDE UN PETIT LOT, `BATCH_INLINE`, et non les dix du chemin de
    fond. Quelqu'un attend derrière : trois questions se rendent en une
    dizaine de secondes contre vingt-trois pour dix, l'essentiel du
    temps n'étant que la lecture de l'article.

    Trois ne tiennent pas la session, et c'est voulu : `_maybe_topup`
    est appelé juste après, il voit l'inédit à trois — donc à
    `LOW_WATER` — et enchaîne un lot PLEIN en tâche de fond. L'élève
    démarre en dix secondes, répond à ses trois questions pendant que
    les dix suivantes s'écrivent, et ne revoit plus l'écran d'attente.

    Le prix : la première ouverture d'un chapitre paye l'article deux
    fois, et consomme deux des trois lots de `DAILY_CAP`.

    Si une écriture est déjà en vol sur ce chapitre — le bouton
    « suivre » l'a lancée il y a dix secondes — `topup` ne la double pas :
    il attend celle-là et rend son compte. On ne paye jamais deux fois le
    même lot. C'est aussi pourquoi le lot de fond ne peut pas partir
    d'ici : lancé maintenant, il s'accrocherait à l'écriture en vol au
    lieu d'écrire. `BackgroundTasks` le lance après la réponse, une fois
    celle-ci terminée.
    """
    for chapter_id in cibles:
        produits = await topup(chapter_id, count=BATCH_INLINE)
        if produits:
            return produits
    return 0


def _maybe_traduire(
    background: BackgroundTasks, chapter_id: int, lang: str
) -> None:
    """Fait traduire ce chapitre en fond, si le lecteur n'est pas anglophone.

    En fond, et jamais dans la requête : la traduction prend 82 secondes
    pour neuf exercices, contre 30 pour en écrire dix. Faire attendre
    l'élève ce temps-là pour une carte qu'il peut déjà lire en anglais
    serait un mauvais échange. Il lit donc l'anglais sur sa première
    carte du chapitre, et le français ensuite — voir
    `api/traduction.py`, qui porte aussi son propre plafond.
    """
    if lang == "en":
        return
    background.add_task(traduire_chapitre, chapter_id, lang)


async def _garantir_les_premieres(
    conn: sqlite3.Connection, picked: list[dict], lang: str
) -> None:
    """Les premières cartes rendues sont traduites AVANT de répondre.

    C'est la réponse au défaut le plus visible de l'app : on lit en
    français, le chapitre s'épuise, le moteur en écrit d'autres — et
    l'écran bascule en anglais d'un coup, sans que rien ne l'explique.
    Trois mécaniques s'additionnaient pour ça :

      · le chemin bloquant écrit et sert dans la MÊME requête, donc ce
        qu'il vient d'écrire n'a par définition pas de traduction ;
      · la traduction de fond ne part qu'APRÈS la réponse, donc toujours
        une réponse trop tard — et le client garde ses cinq cartes
        préchargées pour toute la session ;
      · une coupure de Google laissait un chapitre en anglais pour
        toujours, sans reprise.

    Les deux premières cartes seulement : le client en affiche une et
    précharge la suivante, et chacune coûte une quinzaine d'appels, une
    dizaine de secondes. Le reste part en fond et sera prêt bien avant
    qu'on y arrive.

    Ça ne se déclenche presque jamais — l'écriture traduit derrière elle
    et le tri relègue le non-traduit en dernier. Quand ça se déclenche,
    l'élève est déjà devant l'écran de préparation.
    """
    if lang == LANGUE_SOURCE or not picked:
        return
    manquants = [
        e["id"]
        for e in picked[:TRAD_INLINE_MAX]
        if manque_la_traduction(conn, e["id"], lang)
    ]
    if manquants:
        await traduire_exercices(manquants, lang)


def _seulement_lisibles(
    conn: sqlite3.Connection, picked: list[dict], lang: str
) -> list[dict]:
    """Écarte de la page ce qui n'est pas encore traduit.

    `_garantir_les_premieres` ne couvre que les deux premières cartes, et
    ça ne suffisait pas : le client garde EN MÉMOIRE les cinq cartes
    qu'on lui envoie, pour toute la session. Les trois dernières,
    parties en anglais, y restent en anglais même quand la traduction
    arrive quarante secondes plus tard. C'est exactement la bascule dont
    se plaignait le lecteur — deux questions en français, puis l'anglais
    d'un coup, sans rien qui l'explique.

    Rendre une page courte ne casse rien : le client recharge deux cartes
    avant la fin, et la traduction de fond aura fini d'ici là. Une page
    de deux cartes lisibles vaut mieux qu'une page de cinq dont trois
    sont illisibles.

    MAIS ON NE REND JAMAIS UNE PAGE VIDE. Si rien n'est traduit — Google
    coupé, traduction refusée par `verifier` —, l'anglais repasse devant :
    le client n'a aucune façon de redemander le flux de lui-même autre
    qu'un écran d'attente, et le laisser dessus est pire que le laisser
    lire l'anglais. C'est la règle qui tient tout ce fichier.
    """
    if lang == LANGUE_SOURCE or not picked:
        return picked
    lisibles = [e for e in picked if not manque_la_traduction(conn, e["id"], lang)]
    return lisibles or picked


def _maybe_topup(
    conn: sqlite3.Connection,
    background: BackgroundTasks,
    chapter_id: int,
    uid: int,
) -> None:
    """Lance une recharge en fond si le chapitre est à sec pour cet élève.

    Le compte porte sur l'INÉDIT : un chapitre dont tout a été vu est
    épuisé, même si ses exercices existent toujours. C'est ce qui fait la
    différence entre « on te remet ce que tu connais » et « on en
    prépare ».
    """
    if unseen_count(conn, chapter_id, uid, FEED_TYPES) > LOW_WATER:
        return
    # `ecrire_et_traduire` et non `topup` : un lot écrit sans sa
    # traduction est un lot qui sera servi en anglais à son premier
    # lecteur français. Les deux gestes ne se séparent plus.
    background.add_task(ecrire_et_traduire, chapter_id)


def _load_exercise(conn: sqlite3.Connection, exercise_id: int) -> dict:
    e = row(conn, _SELECT + " WHERE e.id = ?", (exercise_id,))
    if e is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exercice introuvable.")
    return e


@router.get("/exercises/{exercise_id}", response_model=ExerciseOut)
def get_exercise(exercise_id: int, conn: DbDep, user: CurrentUser) -> ExerciseOut:
    return to_exercise_out(conn, _load_exercise(conn, exercise_id), user["id"], _lang(user))


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
            "INSERT INTO attempt (user_id, exercise_id, chapter_id, chosen_index,"
            " is_correct, answer_ms) VALUES (?, ?, ?, ?, ?, ?)",
            (
                uid,
                e["id"],
                e["chapter_id"],
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
                "UPDATE chapter SET exercise_count ="
                " (SELECT COUNT(*) FROM exercise WHERE chapter_id = chapter.id"
                "  AND state = 'validated')"
                " WHERE id = (SELECT chapter_id FROM exercise WHERE id = ?)",
                (exercise_id,),
            )

    return to_exercise_out(conn, _load_exercise(conn, exercise_id), user["id"], _lang(user))


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
