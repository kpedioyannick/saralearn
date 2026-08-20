"""La traduction des exercices — anglais source, français en cache.

Le catalogue est écrit en anglais et le restera : c'est la langue de la
source Wikipédia, et un exercice n'existe qu'une fois, sous un seul
identifiant. Traduire ne fabrique donc pas un second exercice, ça pose
une ligne à côté du premier. C'est ce qui garde `attempt`, la
progression et les classements comparables d'une langue à l'autre.

## `translate_batch` n'est PAS un lot, et c'est ce qui a tout cassé

`deep-translator` pilote Google Traduction. Gratuit, sans clé, sans
solde à surveiller. Mais son `translate_batch` est une BOUCLE de requêtes
HTTP, une par morceau de texte — 15 morceaux par exercice, 135 pour un
chapitre de neuf. D'où les 82 secondes ; pas un aller-retour, cent
trente-cinq.

Et il suffisait qu'UN morceau parte en `TooManyRequests` pour que
l'exception remonte, que le chapitre entier soit abandonné et que les
130 traductions déjà obtenues soient jetées. Sans trace, sans reprise.
C'est exactement ce qui est arrivé le 17/08 à 20:56 : trois chapitres
suivis coup sur coup, trois boucles lancées de front, Google a coupé, et
35 exercices sont restés en anglais pour toujours.

Trois règles en sont sorties, et elles tiennent ce fichier :

  · **un exercice à la fois, écrit dès qu'il est prêt.** Un raté coûte
    un exercice, jamais le chapitre ;
  · **on réessaie** — 2 s, 5 s, 15 s. Une coupure Google est une pause,
    pas un verdict ;
  · **un seul appel à la fois pour tout le service** (`_GOOGLE`). Ce qui
    fait bannir l'adresse, ce n'est pas le volume, c'est le parallélisme.

Un exercice est traduit ENTIÈREMENT ou pas du tout : un morceau perdu
laisserait une carte moitié anglaise moitié française, ce qui est pire
que l'anglais.

## Quand ça part

Jamais dans la boucle d'événements sans fil — `translate` est un appel
réseau synchrone, appelé directement il gèle toute l'API. Toujours
`asyncio.to_thread`.

Deux moments :

  · **derrière chaque écriture** — `topup.ecrire_et_traduire` enchaîne la
    traduction sur ce qui vient d'être écrit, quelle que soit la langue
    de celui qui a déclenché l'écriture. Sept comptes anglophones sur dix
    remplissaient un catalogue que personne ne traduisait ;
  · **dans la requête, pour les premières cartes servies** — voir
    `feed._garantir_les_premieres`. Neuf secondes par carte, et
    seulement quand elle manque.

## Ce que la traduction casse, et qu'il faut rattraper

Chaque morceau part seul. Le traducteur ne voit ni la question quand il
traduit une option, ni les trois autres options quand il en traduit une.
Deux conséquences vues à l'essai :

  · l'accord se perd — « Elle ralentit / Elle accélère / Elle reste la
    même / **Il** disparaît », parce que rien ne dit que le sujet est la
    lumière ;
  · le sens se perd — « the metre is defined as… » est devenu « le
    **compteur** est défini comme… ». Google a pris l'autre sens du mot.

Le second est le vrai danger, et AUCUN contrôle mécanique ne l'attrape :
les options restent distinctes, la question garde son « ? », rien n'est
vide. `verifier()` ci-dessous refuse ce qui est cassé dans sa forme, pas
ce qui est devenu faux dans son sens. Il n'y a pas de garde-fou contre
ça, et il faut le savoir plutôt que de croire le contraire.

## Ce qui n'est jamais traduit

`correct_index`. C'est une POSITION dans le tableau d'options, elle
appartient à l'original. On traduit les libellés à leur place, on ne
touche pas à l'ordre, et l'index se lit toujours dans `exercise`.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3

from . import titres
from .db import connection, row, rows, scalar, transaction

# Les champs de texte plat d'un exercice. `body` est toujours nul dans ce
# catalogue mais reste dans la liste : le jour où il porte quelque chose,
# il doit suivre.
CHAMPS = (
    "prompt",
    "body",
    "ok_title",
    "ok_line",
    "ko_title",
    "ko_line",
    "exp_title",
    "exp_text",
)

# Combien d'exercices un appel de chapitre prend en charge. Ils sont
# traduits l'un après l'autre et écrits l'un après l'autre : ce nombre ne
# décide plus de ce qu'on perd en cas d'échec, seulement de la durée de
# la tâche de fond.
BATCH = 10

# Traductions par jour. Google ne facture rien et ne promet rien non
# plus : le débit se coupe sans prévenir, et une boucle malheureuse fait
# bannir l'adresse du serveur. Le plafond est là pour ça, pas pour la
# facture.
#
# Sept cents et non deux cents : la traduction suit désormais chaque
# écriture, et le plafond d'écriture — 60 lots de 10 — peut produire
# 600 exercices dans la journée. À 200, la traduction s'arrêtait au tiers
# du chemin et le reste repartait en anglais.
DAILY_CAP = int(os.environ.get("SARA_TRAD_JOUR", "700"))

LANGUE_SOURCE = "en"

# Les langues gardées en cache, indépendamment de qui lit. Une écriture
# déclenchée par un anglophone doit produire le français quand même :
# sinon le catalogue se remplit d'un côté et reste vide de l'autre.
LANGUES_CACHE = ("fr",)

# Les attentes entre deux essais d'un même morceau, en secondes.
REPRISES = (2, 5, 15)

# UN SEUL APPEL À GOOGLE À LA FOIS, pour tout le service. Trois chapitres
# traduits de front, c'est trois boucles de 135 requêtes en parallèle —
# et c'est là que Google coupe. Sérialiser ne ralentit rien d'utile : le
# travail est en tâche de fond, et la carte servie passe par
# `feed._garantir_les_premieres`, qui prend son tour comme les autres.
_GOOGLE = asyncio.Semaphore(1)

# Les traductions en vol, par exercice — même raison que dans `topup` :
# deux appelants ne doivent pas payer deux fois le même travail. Le
# second attend le premier au lieu de repartir, ce qui compte pour le
# chemin bloquant du feed : abandonner lui ferait servir l'anglais.
_EN_VOL: dict[tuple[int, str], asyncio.Task] = {}


def _traducteur(lang: str):
    """Importé ici et non en tête de fichier : l'API doit démarrer même
    si la bibliothèque manque, la traduction se contentant alors de ne
    rien faire."""
    from deep_translator import GoogleTranslator

    return GoogleTranslator(source=LANGUE_SOURCE, target=lang)


def traduites_aujourdhui(conn: sqlite3.Connection) -> int:
    return (
        scalar(
            conn,
            "SELECT COUNT(*) FROM exercise_translation"
            " WHERE date(created_at) = date('now')",
        )
        or 0
    )


def manque_la_traduction(conn: sqlite3.Connection, exercise_id: int, lang: str) -> bool:
    return not scalar(
        conn,
        "SELECT 1 FROM exercise_translation WHERE exercise_id = ? AND lang = ?",
        (exercise_id, lang),
    )


def a_traduire(conn: sqlite3.Connection, chapter_id: int, lang: str) -> list[int]:
    """Les exercices servables de ce chapitre qui n'ont pas leur version.

    On ne traduit que le `validated` : le reste ne sera jamais servi, et
    traduire ce qu'on ne montre pas est du débit dépensé pour rien.
    """
    return [
        r["id"]
        for r in rows(
            conn,
            "SELECT e.id FROM exercise e"
            " WHERE e.chapter_id = ? AND e.state = 'validated'"
            "   AND NOT EXISTS (SELECT 1 FROM exercise_translation t"
            "                    WHERE t.exercise_id = e.id AND t.lang = ?)"
            " ORDER BY e.id LIMIT ?",
            (chapter_id, lang, BATCH),
        )
    ]


def verifier(exercice: dict) -> str | None:
    """Ce qui rend une traduction inservable. Rend le motif, ou None.

    Ce sont les mêmes refus que `critic.check_rules` sur l'original —
    une traduction n'est pas dispensée de la règle, et elle produit des
    fautes que l'anglais n'avait pas. Le cas réel : deux options qui
    disent la même chose une fois traduites, et la bonne réponse devient
    indécidable.
    """
    options = exercice["options"]
    if len(options) != 4:
        return f"{len(options)} options au lieu de 4"
    labels = [str(o.get("label", "")).strip() for o in options]
    if any(not label for label in labels):
        return "une option vide"
    if len({label.casefold() for label in labels}) != len(labels):
        return "deux options identiques"
    if not str(exercice.get("prompt", "")).rstrip().endswith("?"):
        return "l'énoncé ne finit pas par « ? »"
    if not str(exercice.get("exp_text", "")).strip():
        return "explication vide"
    return None


def _decouper(exercice: dict, lang: str) -> tuple[list[str], list[tuple], dict]:
    """L'exercice à plat, le plan pour le recomposer, et les champs déjà connus.

    Le plan garde, pour chaque morceau, à quel champ il appartient — et
    pour une option, à quel RANG. C'est ce rang qui garantit que rien ne
    change de place.

    LES DEUX TITRES DE RÉPONSE NE PARTENT PAS CHEZ GOOGLE quand ils sont
    au catalogue de `api/titres.py`. Ils font un ou deux mots : le
    traducteur les prend seuls, sans phrase autour, et n'a rien pour
    choisir le bon sens. Il rendait « Droite ! » pour « Right! » sur
    trente-sept cartes, et « Fermer » pour « Close » — sur l'écran ET
    dans la voix de synthèse, qui les lit. Ce qui n'est pas dans la table
    suit le chemin normal : c'est un raccourci sûr, pas un mur.
    """
    morceaux: list[str] = []
    plan: list[tuple] = []
    connus: dict = {}
    for champ in CHAMPS:
        if not exercice.get(champ):
            continue
        if champ in ("ok_title", "ko_title"):
            fixe = titres.traduire(exercice[champ], lang)
            if fixe is not None:
                connus[champ] = fixe
                continue
        morceaux.append(exercice[champ])
        plan.append((champ, None))
    for i, o in enumerate(json.loads(exercice["options"])):
        if o.get("label"):
            morceaux.append(o["label"])
            plan.append(("label", i))
        if o.get("feedback"):
            morceaux.append(o["feedback"])
            plan.append(("feedback", i))
    return morceaux, plan, connus


def _recomposer(exercice: dict, plan: list[tuple], rendus: list[str]) -> dict:
    """Le plan à l'envers : des morceaux traduits vers un exercice."""
    sortie: dict = {
        "options": [dict(o) for o in json.loads(exercice["options"])],
        **{champ: exercice.get(champ) for champ in CHAMPS},
    }
    for (champ, rang), texte in zip(plan, rendus):
        if rang is None:
            sortie[champ] = texte
        else:
            sortie["options"][rang][champ] = texte
    return sortie


async def _morceau(traducteur, texte: str) -> str | None:
    """Un morceau traduit, ou None après toutes les reprises.

    DANS UN FIL, et c'est vital : `translate` est un appel réseau
    SYNCHRONE, et cette fonction tourne dans la boucle d'événements de
    l'API. Appelée directement, elle gèle tout le service — plus une
    seule requête servie, pour personne, pendant qu'une traduction de
    fond travaille.

    L'attente entre deux essais se fait hors du fil, en `asyncio.sleep` :
    dormir dans le fil garderait un ouvrier du pool immobilisé.
    """
    for attente in (0, *REPRISES):
        if attente:
            await asyncio.sleep(attente)
        try:
            rendu = await asyncio.to_thread(traducteur.translate, texte)
        except Exception:  # noqa: BLE001 — réseau, quota, biblio absente
            continue
        if rendu and rendu.strip():
            return rendu
    return None


async def _ecrire_traduction(exercise_id: int, lang: str) -> bool:
    """Traduit UN exercice et l'écrit. Tout ou rien.

    Le tout ou rien n'est pas de la prudence de principe : un exercice
    dont trois morceaux sur quinze sont restés en anglais est une carte
    bilingue, et c'est moins lisible qu'une carte anglaise.
    """
    with connection() as conn:
        if traduites_aujourdhui(conn) >= DAILY_CAP:
            return False
        if not manque_la_traduction(conn, exercise_id, lang):
            return False
        e = row(
            conn,
            "SELECT id, prompt, body, options, ok_title, ok_line, ko_title,"
            "       ko_line, exp_title, exp_text"
            "  FROM exercise WHERE id = ? AND state = 'validated'",
            (exercise_id,),
        )
    if e is None:
        return False

    try:
        traducteur = _traducteur(lang)
    except Exception:  # noqa: BLE001 — la bibliothèque peut manquer
        return False

    morceaux, plan, connus = _decouper(e, lang)
    if not morceaux:
        return False

    rendus: list[str] = []
    # Le verrou tient le temps d'un exercice — une quinzaine de requêtes,
    # une dizaine de secondes. Le prendre par morceau laisserait deux
    # chapitres s'entrelacer, ce qui est exactement ce qu'on évite.
    async with _GOOGLE:
        for m in morceaux:
            rendu = await _morceau(traducteur, m)
            if rendu is None:
                return False
            rendus.append(rendu)

    traduit = {**_recomposer(e, plan, rendus), **connus}
    if verifier(traduit) is not None:
        return False  # inservable : on laisse l'anglais

    with connection() as conn:
        with transaction(conn):
            conn.execute(
                "INSERT OR IGNORE INTO exercise_translation"
                " (exercise_id, lang, prompt, body, options, ok_title, ok_line,"
                "  ko_title, ko_line, exp_title, exp_text)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    exercise_id,
                    lang,
                    traduit["prompt"],
                    traduit["body"],
                    json.dumps(traduit["options"], ensure_ascii=False),
                    traduit["ok_title"],
                    traduit["ok_line"],
                    traduit["ko_title"],
                    traduit["ko_line"],
                    traduit["exp_title"],
                    traduit["exp_text"],
                ),
            )
    return True


async def traduire_exercice(exercise_id: int, lang: str) -> bool:
    """Un exercice traduit, sans jamais le traduire deux fois de front.

    Le second appelant ATTEND le premier au lieu d'abandonner : sur le
    chemin bloquant du feed, abandonner voudrait dire servir l'anglais
    alors que la traduction arrive dans huit secondes.
    """
    if lang == LANGUE_SOURCE:
        return False
    cle = (exercise_id, lang)
    en_vol = _EN_VOL.get(cle)
    if en_vol is not None:
        # `shield` : celui qui attend peut lâcher — un onglet qu'on ferme
        # annule sa requête — sans emporter la traduction avec lui.
        try:
            return await asyncio.shield(en_vol)
        except Exception:  # noqa: BLE001 — le travail d'un autre ne nous regarde pas
            return False

    tache = asyncio.ensure_future(_ecrire_traduction(exercise_id, lang))
    _EN_VOL[cle] = tache
    try:
        return await asyncio.shield(tache)
    except Exception:  # noqa: BLE001 — silencieuse, c'est le contrat
        return False
    finally:
        if tache.done():
            _EN_VOL.pop(cle, None)
        else:
            tache.add_done_callback(lambda _t: _EN_VOL.pop(cle, None))


async def traduire_exercices(exercise_ids: list[int], lang: str) -> int:
    """Une liste d'exercices, l'un après l'autre. Rend le compte écrit.

    L'un après l'autre et non en parallèle : le verrou les sérialiserait
    de toute façon, et les lancer ensemble ne ferait qu'empiler des
    tâches qui attendent.
    """
    if lang == LANGUE_SOURCE:
        return 0
    n = 0
    for eid in exercise_ids:
        if await traduire_exercice(eid, lang):
            n += 1
    return n


async def traduire_chapitre(chapter_id: int, lang: str) -> int:
    """Traduit ce qui manque au chapitre. Rend le nombre de lignes écrites.

    Silencieuse comme `topup` : elle tourne en fond, et son échec ne doit
    jamais remonter à l'élève — au pire il lit l'anglais, ce qui est le
    comportement d'avant, pas une panne.
    """
    if lang == LANGUE_SOURCE:
        return 0
    with connection() as conn:
        if traduites_aujourdhui(conn) >= DAILY_CAP:
            return 0
        manquants = a_traduire(conn, chapter_id, lang)
    if not manquants:
        return 0
    return await traduire_exercices(manquants, lang)


async def traduire_partout(chapter_id: int) -> int:
    """Le chapitre dans toutes les langues gardées en cache."""
    return sum([await traduire_chapitre(chapter_id, lang) for lang in LANGUES_CACHE])
