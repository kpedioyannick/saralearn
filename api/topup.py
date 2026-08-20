"""La recharge d'un apprentissage — « des exercices illimités ».

La promesse de l'app est un flux qui ne s'arrête pas. Elle n'était pas
tenue : quand le stock d'un chapitre était épuisé, le client écartait les
exercices déjà vus, le deck cessait de grandir, et l'écran restait sur
« on prépare tes exercices… » — un message juste devant une mécanique
absente.

L'ordre est celui du propriétaire :

  1. un exercice raté revient ;
  2. sinon on sert ce qui n'a jamais été vu ;
  3. sinon on en fabrique, à partir de l'article.

**LE CATALOGUE EST DÉSORMAIS VIDE PAR CONSTRUCTION.** Les 2 187 chapitres
ont leur source en base — 24 548 sections, 32 Mo de texte — et zéro
exercice. Écrire les 95 000 questions d'avance coûterait des dizaines
d'heures d'appels pour un catalogue que personne n'a encore joué. Le
point 3 cesse donc d'être un filet de secours : c'est LE mode de
fabrication. Un chapitre s'écrit le jour où quelqu'un l'ouvre.

Ce qui rend ça acceptable sans relecture humaine : **la source est
l'unité de confiance, pas la question**. L'article de Wikipédia est
là, en base, et la consigne interdit d'en sortir. Les questions entrent
en `validated` et non en `draft`.

Trois garde-fous, parce qu'ils ne remplacent pas un humain mais attrapent
ce qu'un humain aurait vu :

  · `api/critic.py` juge chaque exercice seul, et refuse par défaut ;
  · la comparaison des énoncés avec l'existant, sinon recharger donne la
    même question reformulée à l'infini. Elle est faite deux fois : dite
    au modèle dans la consigne, et vérifiée au retour ;
  · un plafond, parce qu'« illimité » côté élève ne peut pas vouloir dire
    « illimité » côté facture.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import sqlite3
import unicodedata

from . import sections
from .critic import review
from .db import connection, row, rows, scalar, transaction
from .llm import GenerationError, ask, validate
from .photos import illustrer_chapitre, illustrer_les_etapes
from .traduction import traduire_partout

# Sous ce nombre d'exercices encore servables, on recharge. Pas à zéro :
# la fabrication prend des secondes à des minutes, et déclencher sur la
# panne sèche rendrait l'écran d'attente aussi mort qu'avant.
LOW_WATER = 3

# Ce qu'on demande au modèle par recharge. Dix, et non les 43 que la
# somme des sections réclamerait : un modèle à qui on demande quarante
# questions d'un coup les bâcle, et le lot n'entre pas en JSON valide.
BATCH = int(os.environ.get("SARA_TOPUP_LOT", "10"))

# Et ce qu'on demande quand QUELQU'UN ATTEND — le chemin bloquant du
# feed, sur un chapitre qui n'a encore rien. Trois au lieu de dix, parce
# que l'écran de préparation dure le temps de l'écriture : 23 s mesurées
# pour dix questions, dont une bonne part n'est que la lecture des 5 à
# 6 000 jetons de l'article. Trois en rendent une dizaine de secondes.
#
# Ce petit lot ne suffit pas à tenir : `LOW_WATER` vaut 3, donc l'élève
# retomberait à sec au bout de trois questions et attendrait une seconde
# fois. C'est pour ça que `feed._ecrire_maintenant` enchaîne un lot
# PLEIN en tâche de fond derrière celui-ci. L'élève démarre en dix
# secondes et ne revoit plus jamais l'écran d'attente sur ce chapitre.
#
# Le prix est connu et assumé : l'article est renvoyé entier à chaque
# appel, donc la première ouverture d'un chapitre coûte deux lectures
# au lieu d'une — environ $0,002 de plus, une seule fois par chapitre.
BATCH_INLINE = int(os.environ.get("SARA_TOPUP_LOT_INLINE", "3"))

# Recharges autorisées par chapitre et par jour. Un swipe nerveux ne doit
# pas vider le solde du compte.
DAILY_CAP = 3

# Écritures menées de front, tous chapitres confondus. Le catalogue a
# 2 187 apprentissages et l'écran d'ajout a un bouton « suivre tout » :
# un clic peut en abonner cent quarante-six d'un coup, donc lancer cent
# quarante-six lots. Au-delà du plafond, la demande est simplement
# refusée — le flux sert alors ce qui existe, et l'écriture repartira à
# la prochaine ouverture.
MAX_EN_VOL = int(os.environ.get("SARA_TOPUP_PARALLELE", "3"))

# Et le même garde-fou sur la journée entière : ce qui protège la
# facture, ce n'est pas le plafond par chapitre — cent chapitres à trois
# lots font trois cents lots.
DAILY_CAP_GLOBAL = int(os.environ.get("SARA_TOPUP_JOUR", "60"))

# Le catalogue est en anglais seul, et `critic` comme `validate` prennent
# la langue pour choisir leurs titres de repli.
LANG = "en"

# Un seul type produit — vrai/faux et carte flash ont été abandonnés.
TYPE = "qcm"

# Ce qu'on dit au juge de `critic.py`, et ce n'est pas un détail : il
# refusait la totalité des lots. Ses deux valeurs par défaut datent du
# catalogue de français — `matiere='langue'` lui fait exiger que répondre
# demande d'appliquer une règle de grammaire, et `level='CM2'` lui fait
# mesurer la difficulté sur un élève de dix ans du programme français.
# Sur « comment un oiseau produit sa poussée », les dix questions d'un
# lot tombaient toutes sur « interroge le cours, pas la langue ».
MATIERE = "connaissance"
LEVEL = "beginner"


def _norm(text: str) -> str:
    """Un énoncé réduit à sa forme comparable : sans casse, sans accent,
    sans ponctuation. Deux questions qui ne diffèrent que par là sont la
    même question pour celui qui la lit."""
    flat = unicodedata.normalize("NFD", text.lower())
    flat = "".join(c for c in flat if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", flat).strip()


def servable_count(conn: sqlite3.Connection, chapter_id: int, types: tuple[str, ...]) -> int:
    """Combien d'exercices ce chapitre peut encore servir, tous élèves confondus."""
    sql = "SELECT COUNT(*) FROM exercise WHERE chapter_id = ? AND state = 'validated'"
    params: list = [chapter_id]
    if types:
        sql += f" AND type_question IN ({','.join('?' * len(types))})"
        params += list(types)
    return scalar(conn, sql, tuple(params)) or 0


def unseen_count(conn: sqlite3.Connection, chapter_id: int, uid: int, types: tuple[str, ...]) -> int:
    """Ce que CET élève n'a pas encore vu — c'est ça qui décide de recharger."""
    sql = (
        "SELECT COUNT(*) FROM exercise e WHERE e.chapter_id = ? AND e.state = 'validated'"
        " AND NOT EXISTS (SELECT 1 FROM attempt a WHERE a.exercise_id = e.id AND a.user_id = ?)"
    )
    params: list = [chapter_id, uid]
    if types:
        sql += f" AND e.type_question IN ({','.join('?' * len(types))})"
        params += list(types)
    return scalar(conn, sql, tuple(params)) or 0


def source_de(conn: sqlite3.Connection, chapter_id: int) -> dict | None:
    """L'article entier, recomposé depuis ses sections.

    Les sections sont stockées à plat dans `exercise_prompt`, dans l'ordre
    où elles se lisent, et seules les feuilles portent du texte. On les
    recolle avec leur titre : le plan de l'article fait partie de ce qui
    s'enseigne, et le modèle s'en sert pour ordonner ses questions.

    Rend `None` si le chapitre n'a aucune section avec assez de matière —
    il reste alors dans le catalogue mais ne produira jamais rien, et
    c'est le bon comportement : mieux vaut un titre sans question qu'une
    question sans source.
    """
    ch = row(
        conn,
        "SELECT ch.id, ch.title, th.title AS theme FROM chapter ch"
        " JOIN theme th ON th.id = ch.theme_id WHERE ch.id = ?",
        (chapter_id,),
    )
    if ch is None:
        return None
    secs = rows(
        conn,
        "SELECT title, content FROM exercise_prompt"
        " WHERE chapter_id = ? AND content IS NOT NULL AND requested_count > 0"
        " ORDER BY position",
        (chapter_id,),
    )
    if not secs:
        return None
    texte = "\n\n".join(f"== {s['title']} ==\n{s['content']}" for s in secs)
    return {"chapter_id": ch["id"], "chapter": ch["title"], "theme": ch["theme"], "source": texte}


def topups_today(conn: sqlite3.Connection, chapter_id: int) -> int:
    return (
        scalar(
            conn,
            "SELECT COUNT(*) FROM exercise_prompt"
            " WHERE chapter_id = ? AND model = 'topup'"
            " AND date(created_at) = date('now')",
            (chapter_id,),
        )
        or 0
    )


def topups_today_total(conn: sqlite3.Connection) -> int:
    """Les recharges du jour, tout le catalogue confondu."""
    return (
        scalar(
            conn,
            "SELECT COUNT(*) FROM exercise_prompt"
            " WHERE model = 'topup' AND date(created_at) = date('now')",
        )
        or 0
    )


# Les écritures en vol, par chapitre. Deux portes mènent ici — le bouton
# « suivre » et l'écran d'exercice — et rien n'empêchait qu'elles visent
# le même chapitre en même temps : le plafond du jour se compte en base
# AVANT l'appel au modèle, mais les énoncés déjà connus se lisent au même
# instant, donc deux lots partaient avec la même liste et écrivaient deux
# fois la même question. C'est exactement ce qui a laissé 50 doublons sur
# le thème 229. Le second appelant n'écrit pas : il attend le premier et
# rend son compte.
_EN_VOL: dict[int, asyncio.Task] = {}


async def topup(chapter_id: int, lang: str = LANG, count: int = BATCH) -> int:
    """Fabrique un lot pour ce chapitre. Rend le nombre d'exercices insérés.

    Silencieuse par construction : elle tourne aussi en tâche de fond
    pendant que l'élève répond. Un échec ne doit jamais remonter jusqu'à
    lui — au pire le flux ressert ce qu'il connaît déjà, ce qui est le
    comportement d'avant, pas une panne.
    """
    en_vol = _EN_VOL.get(chapter_id)
    if en_vol is None and len(_EN_VOL) >= MAX_EN_VOL:
        return 0
    if en_vol is not None:
        # `shield` : celui qui attend peut lâcher — un onglet qu'on ferme
        # annule sa requête — sans emporter l'écriture avec lui.
        try:
            return await asyncio.shield(en_vol)
        except Exception:  # noqa: BLE001 — l'écriture d'un autre ne nous regarde pas
            return 0

    tache = asyncio.ensure_future(_ecrire_un_lot(chapter_id, lang, count))
    _EN_VOL[chapter_id] = tache
    try:
        return await asyncio.shield(tache)
    except Exception:  # noqa: BLE001 — silencieuse, c'est le contrat
        return 0
    finally:
        if tache.done():
            _EN_VOL.pop(chapter_id, None)
        else:
            # On a lâché avant la fin : la tâche continue, et c'est elle
            # qui retirera son entrée en terminant.
            tache.add_done_callback(lambda _t: _EN_VOL.pop(chapter_id, None))


async def _ecrire_un_lot(chapter_id: int, lang: str, count: int = BATCH) -> int:
    """Le travail lui-même — un seul en vol par chapitre, voir `topup`."""
    with connection() as conn:
        if topups_today(conn, chapter_id) >= DAILY_CAP:
            return 0
        if topups_today_total(conn) >= DAILY_CAP_GLOBAL:
            return 0
        src = source_de(conn, chapter_id)
        if src is None:
            return 0
        deja = [
            r["prompt"]
            for r in rows(
                conn, "SELECT prompt FROM exercise WHERE chapter_id = ?", (chapter_id,)
            )
        ]
        known = {_norm(q) for q in deja}
        # La ligne est posée AVANT l'appel au modèle : c'est elle qui
        # compte pour le plafond, et deux recharges lancées coup sur coup
        # ne doivent pas passer toutes les deux.
        #
        # `position` prend la suite des sections : la contrainte
        # UNIQUE (chapter_id, position) refuserait un doublon, et les
        # recharges se rangent naturellement après le plan de l'article.
        with transaction(conn):
            cur = conn.execute(
                "INSERT INTO exercise_prompt (chapter_id, position, title,"
                " model, requested_count, status)"
                " VALUES (?, (SELECT COALESCE(MAX(position), 0) + 1"
                "             FROM exercise_prompt WHERE chapter_id = ?),"
                " ?, 'topup', ?, 'running')",
                (chapter_id, chapter_id, f"Recharge — {src['chapter']}", count),
            )
            run_id = cur.lastrowid

    consigne = sections.article(src["theme"], src["chapter"], src["source"], count, deja)

    try:
        raw = await ask(consigne)
        items = validate(raw, TYPE, lang)
    except Exception as exc:  # noqa: BLE001 — on trace tout, on ne remonte rien
        with connection() as conn:
            conn.execute(
                "UPDATE exercise_prompt SET status = 'failed', error = ?,"
                " finished_at = datetime('now') WHERE id = ?",
                (str(exc)[:1000], run_id),
            )
        return 0

    kept: list[dict] = []
    for item in items:
        if _norm(item["prompt"]) in known:
            continue
        verdict = await review(item, lang, level=LEVEL, kind=TYPE, matiere=MATIERE)
        if not verdict.ok:
            continue
        known.add(_norm(item["prompt"]))
        kept.append(_melanger(item))

    with connection() as conn:
        with transaction(conn):
            for item in kept:
                cur = conn.execute(
                    "INSERT INTO exercise (chapter_id, exercise_prompt_id, type_question,"
                    " prompt, body, options, correct_index, ok_title, ok_line,"
                    " ko_title, ko_line, exp_title, exp_text, image_query, state)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'validated')",
                    (
                        chapter_id,
                        run_id,
                        TYPE,
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
                        item.get("image_query"),
                    ),
                )
                # LES ÉTAPES DANS LA MÊME TRANSACTION QUE LA CARTE. Un
                # exercice sans ses étapes serait à moitié écrit, et
                # c'est le genre de moitié qu'on ne retrouve jamais :
                # rien ne repasse derrière pour les poser.
                for rang, etape in enumerate(item.get("steps") or []):
                    conn.execute(
                        "INSERT INTO exercise_step (exercise_id, rang, texte, image_title)"
                        " VALUES (?,?,?,?)",
                        (cur.lastrowid, rang, etape["text"], etape.get("image_title")),
                    )
            conn.execute(
                "UPDATE exercise_prompt SET status = 'done', produced_count = ?,"
                " finished_at = datetime('now') WHERE id = ?",
                (len(kept), run_id),
            )
            # Le compteur affiché dans le catalogue suit la production.
            conn.execute(
                "UPDATE chapter SET exercise_count ="
                " (SELECT COUNT(*) FROM exercise WHERE chapter_id = ? AND state = 'validated')"
                " WHERE id = ?",
                (chapter_id, chapter_id),
            )
    return len(kept)


def _melanger(item: dict) -> dict:
    """La bonne réponse change de place avant d'entrer en base.

    LE MODÈLE LA MET DEVANT, toujours. Mesuré sur les 261 premières
    cartes : bonne réponse en position 1 ou 2 dans 223 d'entre elles, en
    position 4 dans cinq. Il écrit la vraie d'abord et invente les
    fausses ensuite ; l'ordre du JSON suit l'ordre de sa pensée. Un
    élève qui joue les deux premières cases gagne sans lire, et le taux
    de réussite ne mesure plus rien.

    Le mélange est ici et non dans la consigne : on a demandé au modèle
    de varier la position, il ne s'y tient pas — c'est une contrainte de
    forme, elle se règle en Python. `correct_index` est recalculé depuis
    la nouvelle place, jamais recopié, et chaque libellé emporte son
    `feedback` avec lui.

    La traduction n'est pas concernée : elle est écrite APRÈS, depuis
    ces options-ci, donc dans cet ordre-ci. Voir `scripts/melanger_options.py`
    pour le rattrapage de ce qui était déjà en ligne.
    """
    options = item.get("options") or []
    correct = item.get("correct_index")
    if len(options) < 2 or not isinstance(correct, int) or not 0 <= correct < len(options):
        return item
    ordre = list(range(len(options)))
    random.shuffle(ordre)
    item = dict(item)
    item["options"] = [options[i] for i in ordre]
    item["correct_index"] = ordre.index(correct)
    return item


async def ecrire_et_traduire(chapter_id: int, count: int = BATCH) -> int:
    """Un lot, puis sa traduction. C'est la porte normale de l'écriture de fond.

    Les deux gestes n'en font qu'un, et les séparer coûtait cher : un lot
    écrit sans traduction attendait qu'un francophone tombe dessus dans
    son flux pour être traduit — et il le voyait alors EN ANGLAIS, la
    traduction ne partant qu'après la réponse. Le chapitre 36 est resté
    vingt heures dans cet état avant d'être servi en anglais à son
    lecteur français.

    La traduction ne regarde PAS la langue de celui qui a déclenché
    l'écriture : sept comptes sur dix sont anglophones, et leur laisser
    remplir un catalogue que personne ne traduit revenait au même trou.
    On traduit dans les langues du cache, point — voir `LANGUES_CACHE`.

    Elle part même quand rien n'a été écrit : `topup` rend zéro dès que
    le plafond du jour est atteint ou qu'une autre écriture tenait déjà
    le chapitre, et il reste alors souvent de l'ancien à traduire. Ça ne
    coûte qu'une requête quand il n'y a rien.
    """
    produits = await topup(chapter_id, count=count)
    await traduire_partout(chapter_id)
    # La photo APRÈS la traduction, et pas avant : l'élève peut lire une
    # carte sans image, il ne peut pas lire une carte en anglais quand il
    # a demandé le français. L'ordre suit ce qui manque le plus.
    await illustrer_chapitre(chapter_id)
    # Puis les étapes de l'explication, qui ont leur propre titre
    # d'image. Après la photo de la carte : celle-là se voit dès la
    # question, les autres seulement quand l'élève a répondu.
    await illustrer_les_etapes(chapter_id)
    return produits
