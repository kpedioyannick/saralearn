"""La photo d'ambiance d'un exercice — la SCÈNE, jamais le phénomène.

Une question de ce catalogue part de quelque chose que l'élève a déjà vu :
une route brûlante, une paille dans un verre, des oies en vol. La photo
plante ce décor. Elle ne montre pas le mécanisme, et c'est toute la
différence :

  · une photo de la ROUTE DROITE ET VIDE aide — elle rappelle la scène
    que la question demande de se remémorer ;
  · une photo DU MIRAGE donne la réponse avant qu'on ait lu les options.

## Les mots ne viennent pas de la question, et c'est mesuré

Envoyer l'énoncé tel quel à une banque d'images ne marche pas. Essayé sur
Commons : « A straw in a glass of water looks bent at the surface. Why? »
rend *The water witch; or, The skimmer of the seas* — des livres du XIXe
siècle numérisés, parce qu'un fonds documentaire indexe du plein texte et
qu'une phrase longue accroche des pages, pas des photos. Trois ou quatre
noms communs rendent la bonne image du premier coup.

C'est donc LE MODÈLE qui fournit ces mots, au moment où il écrit
l'exercice : il a l'article sous les yeux et sait de quoi la question
parle. Voir `image_query` dans le contrat de sortie de `sections.py`.

## Le filtre, parce que la consigne ne suffit pas

Sur dix questions d'essai, sept requêtes étaient parfaites. Mais pour la
route brûlante, le modèle a écrit **« hot road mirage »** — alors que la
consigne lui interdisait nommément d'écrire « mirage ». Sur la question
où l'image aurait le plus vendu la mèche.

D'où `revele()` : une requête qui partage un mot avec la bonne réponse ou
avec l'explication est refusée, et l'exercice reste sans photo. La règle
ne demande aucune liste à tenir à jour, elle se règle sur l'exercice
lui-même. Pas de photo est le cas normal ; une photo qui donne la
réponse coûte l'exercice.

## Trois banques, et elles ne demandent pas la même chose

Unsplash d'abord, Pexels si elle est à sec, Pixabay en dernier ressort.
La chaîne existe parce que le mode démo d'Unsplash plafonne à cinquante
requêtes par heure — et qu'une photo retenue en coûte deux, l'appel
d'attribution étant facturé au même compteur. Vingt-trois photos par
heure, pour un catalogue qui en attend deux cents.

Ce que chacune exige, et ce n'est pas négociable :

  · **Unsplash** — lien direct vers leur CDN, donc AUCUNE copie locale ;
    crédit du photographe avec le lien ; et l'appel au point d'entrée
    `download_location` quand une photo est retenue. Ce dernier ne rend
    rien d'utile, il sert à leurs statistiques, et c'est la contrepartie
    du service gratuit. 50 requêtes/heure en démo, 5 000 une fois
    l'application approuvée.

  · **Pexels** — crédit du photographe et lien visible vers Pexels.
    Rien sur le lien direct, qui reste donc permis. 200 requêtes/heure
    et 20 000 par mois.

  · **Pixabay** — L'INVERSE D'UNSPLASH, et c'est le piège : « permanent
    hotlinking of images (using Pixabay URLs in your app) is not
    allowed. If you intend to use the images, please download them to
    your server first. » Sa photo est donc RAPATRIÉE dans `media/photos/`
    et c'est ce chemin qui va en base, jamais leur URL. 100 requêtes par
    minute — le fond est hors de portée.

D'où la colonne `image_source` (migration 031) : le nom de la banque
voyage avec la photo, parce que le front doit créditer la bonne. Il était
écrit en dur dans `PhaseBlocks.tsx` du temps où il n'y en avait qu'une.

Le débit, pas le prix, commande ici — d'où le même traitement que la
traduction : en tâche de fond, sérialisé, silencieux.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sqlite3
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from .db import connection, row, rows, transaction

# TROIS BANQUES, ESSAYÉES DANS CET ORDRE — et l'ordre est un jugement,
# pas un hasard. Unsplash d'abord parce que c'est la plus belle : sur les
# cinquante photos déjà posées, ça se voit — une vraie route vide dans un
# vrai désert, là où les deux autres rendent volontiers l'image de banque.
# Pexels ensuite, très proche en qualité et quatre fois plus large en
# débit. Pixabay en dernier, le filet : correct, et pratiquement sans
# plafond.
#
# Une banque sans clé est simplement sautée. Aucune n'est obligatoire, et
# le catalogue tourne avec zéro comme avec trois.
CLE = os.environ.get("UNSPLASH_ACCESS_KEY", "").strip()
CLE_PEXELS = os.environ.get("PEXELS_API_KEY", "").strip()
CLE_PIXABAY = os.environ.get("PIXABAY_API_KEY", "").strip()

RECHERCHE = "https://api.unsplash.com/search/photos"
RECHERCHE_PEXELS = "https://api.pexels.com/v1/search"
RECHERCHE_PIXABAY = "https://pixabay.com/api/"

# Ce qu'on demande : du paysage, parce que la carte est large et courte,
# et le filtre de contenu au maximum — l'app s'adresse à des enfants.
ORIENTATION = "landscape"

# Le plafond horaire de chacune, gardé sous le vrai chiffre. Il ne sert
# qu'à dimensionner une ronde AVANT le premier appel : ensuite c'est
# l'en-tête `X-Ratelimit-Remaining` qui fait foi, et les trois le
# renvoient. Voir `_RESTANT`.
#
#   Unsplash  50/heure en mode démo, 5 000 une fois approuvé
#   Pexels   200/heure et 20 000 par mois
#   Pixabay  100 par MINUTE — on n'en tirera jamais le fond
PLAFONDS = {"Unsplash": 45, "Pexels": 180, "Pixabay": 90}

# UNSPLASH COÛTE DEUX REQUÊTES PAR PHOTO RETENUE, et ça s'est vu à
# l'usage : une ronde dimensionnée sur 45 s'est arrêtée à 27 cartes.
# 27 recherches + 23 appels à `download_location` = 50, le plafond
# exact. L'appel d'attribution est facturé au même compteur que la
# recherche. Les deux autres banques n'ont pas cet appel.
DOUBLE_REQUETE = {"Unsplash"}


def banques_ouvertes() -> list[str]:
    """Les banques qui ont une clé, dans l'ordre d'essai."""
    return [n for n, c in (("Unsplash", CLE), ("Pexels", CLE_PEXELS),
                           ("Pixabay", CLE_PIXABAY)) if c]


# Le plafond de l'heure, toutes banques ouvertes confondues.
PAR_HEURE = int(
    os.environ.get("SARA_PHOTOS_PAR_HEURE")
    or sum(PLAFONDS[n] for n in banques_ouvertes())
    or PLAFONDS["Unsplash"]
)

# Un seul appel à la fois, comme pour la traduction : ce qui fait couper
# un service gratuit, c'est le parallélisme. Une seule garde pour les
# trois — on ne cherche jamais qu'une photo à la fois de toute façon.
_UNSPLASH = asyncio.Semaphore(1)

# CE QUE CHAQUE BANQUE DIT ELLE-MÊME QU'IL LUI RESTE, lu dans l'en-tête
# `X-Ratelimit-Remaining` de ses réponses. `None` tant qu'on ne lui a
# rien demandé.
#
# C'est la seule mesure juste, et il a fallu se tromper deux fois pour le
# voir. D'abord je comptais les photos POSÉES dans l'heure : une
# recherche qui ne rend rien consomme du quota sans rien poser, donc
# 45 tentatives pour 24 photos étaient comptées 24, et la fin de la ronde
# se prenait des 403. Ensuite, une fois le compteur tombé à zéro, plus
# rien ne le relevait jamais — voir `oublier_le_quota`.
_RESTANT: dict[str, int | None] = {"Unsplash": None, "Pexels": None, "Pixabay": None}

# Les mots qu'on ne compte pas comme révélateurs : ils sont partout, et
# les interdire viderait toutes les requêtes.
_VIDES = {
    "the", "a", "an", "of", "in", "on", "at", "to", "and", "or", "is", "are",
    "it", "its", "this", "that", "with", "from", "by", "as", "for", "into",
    "more", "than", "when", "why", "how", "what", "which", "does", "do",
    "light", "water", "air", "sun", "sky",
}


# La ceinture, en plus des bretelles. La règle qui se règle sur
# l'exercice laisse passer ce que la conjugaison sépare : l'énoncé dit
# « looks bent », la requête dit « bending », et les deux mots ne se
# ressemblent pas pour une comparaison exacte. Cette liste ne tient que
# les mots qui NOMMENT un phénomène — elle n'a pas à couvrir le monde,
# seulement à rattraper ce que la première règle manque.
#
# Le risque restant est petit et il faut le dire : Unsplash est une
# banque de PHOTOS, pas de schémas. Un mot de mécanisme qui passe rend
# une image moins pertinente, il ne rend presque jamais l'explication en
# dessin — ce qui aurait été le vrai danger sur Wikimedia Commons.
PHENOMENES = {
    "refraction", "reflection", "refract", "reflect", "diffraction",
    "dispersion", "scattering", "polarization", "interference", "bending",
    "wavelength", "frequency", "spectrum", "photon", "absorption",
    "emission", "convection", "conduction", "radiation", "evaporation",
    "condensation", "erosion", "gravity", "inertia", "momentum",
    "pressure", "density", "buoyancy", "thermal", "magnetic", "electric",
    "lift", "drag", "thrust", "vortex", "turbulence", "mirage", "halo",
    "eclipse", "orbit", "rotation", "tilt", "photosynthesis", "osmosis",
    "diagram", "illustration", "explained", "explanation", "physics",
}


def _mots(texte: str) -> set[str]:
    """Les mots significatifs d'un texte, réduits à leur forme comparable."""
    plat = unicodedata.normalize("NFD", (texte or "").lower())
    plat = "".join(c for c in plat if unicodedata.category(c) != "Mn")
    return {
        m for m in re.findall(r"[a-z]{4,}", plat) if m not in _VIDES
    }


def revele(requete: str, exercice: dict) -> str | None:
    """La requête donne-t-elle la réponse ? Rend le mot fautif, ou None.

    Le garde-fou, et il faut un garde-fou : la consigne dit au modèle de
    ne jamais nommer le phénomène, il a écrit « hot road mirage » — sur
    la question où l'image aurait le plus vendu la mèche. Une règle
    mécanique ne se laisse pas convaincre.

    LA RÈGLE : est refusé un mot de `PHENOMENES` qui n'est PAS dans
    l'énoncé. Deux moitiés, et chacune a été mesurée sur les 201 cartes.

    La liste fixe, parce que la règle qui se règle sur l'exercice ne
    marche pas. J'avais d'abord écrit celle-ci, plus élégante et sans
    rien à tenir à jour : « est révélateur un mot présent dans la réponse
    ou l'explication, et absent de l'énoncé ». Elle refusait **36 % des
    requêtes** — « prism sunlight WHITE wall » pour « white », « DISTANT
    galaxy photo » pour « distant ». La cause est de fond : une
    explication décrit la scène qu'elle explique, donc ses mots sont ceux
    du décor. Restreinte au seul libellé de la bonne réponse, elle
    refusait encore 16 %, toujours des noms de décor — « mountain »,
    « river », « onion ». **La liste fixe en refuse 5 %, et les douze
    sont de vrais noms de phénomène.**

    L'exemption de l'énoncé, parce que certaines questions NOMMENT le
    phénomène : « Vous voyez un halo de 22° autour du Soleil… ». La photo
    du halo est alors exactement la scène, et l'élève a déjà lu le mot.
    Sans cette moitié, les trois cartes du chapitre « 22° halo »
    perdaient leur image pour un mot qu'elles affichent elles-mêmes.

    Ce qui reste possible : une requête qui nomme un mécanisme absent de
    la liste. Le risque est petit et connu — Unsplash est une banque de
    PHOTOS, pas de schémas. Un mot de mécanisme qui passe rend une image
    moins pertinente, il ne rend presque jamais l'explication en dessin.
    """
    libres = _mots(exercice.get("prompt", ""))
    for mot in _mots(requete):
        if mot in PHENOMENES and mot not in libres:
            return mot
    return None


# LE PUBLIC EST SCOLAIRE, ET LES TROIS BANQUES NE FILTRENT PAS PAREIL.
# Unsplash reçoit `content_filter=high`, Pixabay `safesearch=true` — les
# deux l'offrent dans leur API. **Pexels n'offre rien de tel** : ses
# paramètres de recherche sont query, orientation, size, color, locale,
# page et per_page, point. Sa modération est humaine et en amont, ce qui
# tient pour la nudité mais laisse passer ce qui est simplement hors de
# propos pour des enfants — casino, alcool, boîte de nuit.
#
# D'où ce dernier filet, posé sur le TEXTE ALTERNATIF que la banque
# rend avec la photo. Il ne voit pas l'image : ce qu'il attrape, c'est
# ce que la banque a elle-même nommé. Imparfait par construction, et
# c'est assumé — il coûte zéro appel, et une photo écartée à tort ne
# coûte qu'une photo, jamais une carte.
INTERDITS = {
    "nude", "nudity", "naked", "topless", "lingerie", "underwear",
    "bikini", "swimsuit", "erotic", "sensual", "seductive", "boudoir",
    "sexy", "cleavage", "stripper", "casino", "roulette", "gambling",
    "poker", "betting", "slot", "jackpot", "beer", "wine", "whisky",
    "vodka", "cocktail", "alcohol", "alcoholic", "drunk", "nightclub",
    "smoking", "cigarette", "cigar", "vape", "tobacco", "hookah",
    "shisha", "weapon", "pistol", "rifle", "gun", "shotgun", "ammo",
    "blood", "bloody", "wound", "corpse", "syringe", "cocaine",
    "cannabis", "marijuana", "drug",
}


def convient(photo: dict | None) -> str | None:
    """Le mot qui fait écarter cette photo, ou None si elle passe.

    Lit `alt`, jamais l'image. Une photo sans texte alternatif passe :
    l'absence d'information n'est pas une information.
    """
    if not photo:
        return None
    for mot in _mots(photo.get("alt", "")):
        if mot in INTERDITS:
            return mot
    return None


def _appel(nom: str, url: str, entetes: dict | None = None, **params) -> dict | None:
    """Un appel à une banque. Rend None sur n'importe quel ennui.

    Synchrone : appelé dans un fil par `chercher`, comme le traducteur.
    Met à jour le compteur de CETTE banque, et d'elle seule.
    """
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SaraLearn/1.0 (learn.sara.education)",
            **(entetes or {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            corps = r.read()
            reste = r.headers.get("X-Ratelimit-Remaining")
        if reste is not None and str(reste).isdigit():
            _RESTANT[nom] = int(reste)
            if _RESTANT[nom] <= 2:
                _VIDE_DEPUIS.setdefault(nom, time.monotonic())
            else:
                _VIDE_DEPUIS.pop(nom, None)
        return json.loads(corps) if corps else {}
    except Exception as exc:  # noqa: BLE001 — quota, réseau, clé absente
        # 403 chez Unsplash, 429 chez les deux autres : dans les trois cas
        # ça veut dire « plus de quota » et rien d'autre. On pose le
        # compteur à zéro pour que l'appelant passe à la banque suivante
        # au lieu d'enchaîner quarante refus.
        if getattr(exc, "code", None) in (403, 429):
            _RESTANT[nom] = 0
            _VIDE_DEPUIS.setdefault(nom, time.monotonic())
        return None


def _unsplash(requete: str) -> dict | None:
    """La photo d'Unsplash, avec l'appel d'attribution qu'ils imposent."""
    d = _appel(
        "Unsplash",
        RECHERCHE,
        {"Authorization": f"Client-ID {CLE}", "Accept-Version": "v1"},
        query=requete,
        per_page=1,
        orientation=ORIENTATION,
        content_filter="high",
    )
    if not d or not d.get("results"):
        return None
    p = d["results"][0]
    # L'appel exigé par leurs conditions quand une photo est retenue. Il
    # ne rend rien d'utile et son échec n'empêche rien : on ne le laisse
    # pas bloquer l'exercice. Il coûte une requête — voir DOUBLE_REQUETE.
    lien = (p.get("links") or {}).get("download_location")
    if lien:
        _appel("Unsplash", lien, {"Authorization": f"Client-ID {CLE}",
                                  "Accept-Version": "v1"})
    utm = "?utm_source=SaraLearn&utm_medium=referral"
    return {
        # `regular` fait 1080 px de large : la carte n'en montre jamais
        # plus, et `small` pixellise sur un écran dense.
        "url": p["urls"]["regular"],
        "alt": (p.get("alt_description") or p.get("description") or "").strip()[:200],
        "credit": (p.get("user") or {}).get("name") or "Unsplash",
        "credit_url": ((p.get("user") or {}).get("links") or {}).get("html", "") + utm,
        "source": "Unsplash",
    }


def _pexels(requete: str) -> dict | None:
    """La photo de Pexels. Même contrat, sans l'appel d'attribution.

    Leurs conditions demandent le crédit du photographe ET un lien
    visible vers Pexels : « Always credit our photographers » et « show a
    prominent link to Pexels ». Le front pose les deux.
    """
    d = _appel(
        "Pexels",
        RECHERCHE_PEXELS,
        {"Authorization": CLE_PEXELS},
        query=requete,
        per_page=1,
        orientation="landscape",
    )
    if not d or not d.get("photos"):
        return None
    p = d["photos"][0]
    return {
        # `large` fait 940 px — le pendant du `regular` d'Unsplash.
        "url": (p.get("src") or {}).get("large") or p.get("url"),
        "alt": (p.get("alt") or "").strip()[:200],
        "credit": p.get("photographer") or "Pexels",
        "credit_url": p.get("photographer_url") or p.get("url") or "",
        "source": "Pexels",
    }


def _pixabay(requete: str) -> dict | None:
    """La photo de Pixabay. Son URL est PROVISOIRE — voir `_rapatrier`.

    Leurs conditions d'API disent l'inverse exact de celles d'Unsplash :
    « permanent hotlinking of images (using Pixabay URLs in your app) is
    not allowed. If you intend to use the images, please download them to
    your server first. » L'URL rendue ici ne va donc pas en base telle
    quelle ; `illustrer` en fait une copie dans `media/photos/`.
    """
    d = _appel(
        "Pixabay",
        RECHERCHE_PIXABAY,
        None,
        key=CLE_PIXABAY,
        q=requete,
        image_type="photo",
        orientation="horizontal",
        safesearch="true",
        # Leur minimum est 3, pas 1 : `per_page=1` est refusé.
        per_page=3,
    )
    if not d or not d.get("hits"):
        return None
    p = d["hits"][0]
    return {
        "url": p.get("largeImageURL") or p.get("webformatURL"),
        # Pas de texte alternatif chez eux : les mots-clés en tiennent
        # lieu, et ils décrivent bien la scène.
        "alt": (p.get("tags") or "").strip()[:200],
        "credit": p.get("user") or "Pixabay",
        "credit_url": p.get("pageURL") or "",
        "source": "Pixabay",
    }


BANQUES = {"Unsplash": _unsplash, "Pexels": _pexels, "Pixabay": _pixabay}


def restant() -> int | None:
    """Ce qui reste ce cycle, toutes banques ouvertes confondues.

    `None` avant le premier appel, et seulement dans ce cas : c'est le
    signal qui dit à l'appelant de dimensionner sa ronde sur `PAR_HEURE`.
    Une banque qu'on n'a pas encore interrogée compte pour son plafond.
    """
    ouvertes = banques_ouvertes()
    if not ouvertes:
        return 0
    if all(_RESTANT[n] is None for n in ouvertes):
        return None
    return sum(
        PLAFONDS[n] if _RESTANT[n] is None else _RESTANT[n] for n in ouvertes
    )


def quota_epuise() -> bool:
    """Vrai quand PLUS AUCUNE banque n'a de marge.

    C'est tout l'intérêt de la chaîne : Unsplash à sec ne suffit plus à
    arrêter la ronde. Deux de garde par banque — une traduction de lot et
    une illustration de chapitre peuvent partir en même temps, et il vaut
    mieux perdre deux requêtes que finir sur un refus.
    """
    return all(
        _RESTANT[n] is not None and _RESTANT[n] <= 2 for n in banques_ouvertes()
    ) if banques_ouvertes() else True


# CHAQUE BANQUE SE RENOUVELLE À SON PROPRE RYTHME, et les confondre coûte
# cher. Unsplash et Pexels comptent à l'HEURE ; Pixabay compte à la
# MINUTE — cent requêtes, soit six mille par heure.
#
# Le veilleur dormait une heure dès que les trois compteurs étaient à
# zéro, Pixabay compris. Mesuré le 20/08/2026 : 348 images d'étapes en
# attente, un rythme de 83 par heure, quatre heures annoncées — quand
# Pixabay seul pouvait les poser en dix minutes. On attend donc le
# renouvellement LE PLUS COURT, et on ne rouvre que les banques dont le
# délai est écoulé : rouvrir Unsplash toutes les minutes lui ferait
# dépenser son quota horaire en refus.
RENOUVELLEMENT = {"Unsplash": 3660, "Pexels": 3660, "Pixabay": 65}

# Quand chaque compteur est tombé à sec. Vide tant qu'aucune banque ne
# l'est.
_VIDE_DEPUIS: dict[str, float] = {}


def prochaine_reprise() -> int:
    """Combien de secondes attendre avant que quelque chose se rouvre.

    La plus courte des attentes restantes, jamais moins de cinq
    secondes. Une heure s'il n'y a rien à attendre — le cas ne devrait
    pas se présenter, mais un veilleur qui tourne à vide vaut mieux
    qu'un veilleur qui tourne en rond.
    """
    maintenant = time.monotonic()
    restants = [
        RENOUVELLEMENT[n] - (maintenant - depuis)
        for n, depuis in _VIDE_DEPUIS.items()
        if n in RENOUVELLEMENT
    ]
    if not restants:
        return 3660
    return max(5, int(min(restants)) + 2)


def oublier_le_quota() -> None:
    """Rendre leur compteur aux banques dont le délai est écoulé.

    Un compteur tombé à zéro est un cul-de-sac : l'appelant dimensionne
    sa ronde sur `restant()`, une ronde de zéro carte ne fait aucun
    appel, et seul un appel rafraîchit l'en-tête. La boucle
    d'illustration s'est endormie quatorze heures là-dessus le
    20/08/2026, quota plein, 173 cartes en attente.

    Ce qui n'a pas fini d'attendre reste à zéro : c'est ce qui empêche
    de brûler le quota horaire d'Unsplash en le rappelant chaque minute
    pour la seule raison que Pixabay, lui, est prêt.
    """
    maintenant = time.monotonic()
    for n in list(_RESTANT):
        depuis = _VIDE_DEPUIS.get(n)
        if depuis is None or maintenant - depuis >= RENOUVELLEMENT.get(n, 3660):
            _RESTANT[n] = None
            _VIDE_DEPUIS.pop(n, None)


async def chercher(requete: str) -> dict | None:
    """La première photo qui répond à ces mots, avec son crédit.

    Les banques sont essayées dans l'ordre, et **on passe à la suivante
    dès que celle-ci ne rend rien** — qu'elle soit à sec, en panne, ou
    simplement sans résultat pour ces mots-là. Les trois cas se
    ressemblent de l'extérieur et méritent la même suite.

    Rend None quand aucune des trois n'a rien : l'exercice reste sans
    photo, ce qui est le cas normal du catalogue.
    """
    if not requete.strip():
        return None
    async with _UNSPLASH:
        for nom in banques_ouvertes():
            marge = _RESTANT[nom]
            if marge is not None and marge <= 2:
                continue
            photo = await asyncio.to_thread(BANQUES[nom], requete)
            fautif = convient(photo)
            if fautif:
                print(f"  photo écartée ({fautif}) chez {nom}"
                      f" pour « {requete} »")
                continue
            if photo and photo.get("url"):
                return photo
    return None


def _rapatrier(url: str, exercise_id: int | str) -> str | None:
    """Copie une photo chez nous et rend son chemin public.

    L'identifiant peut être un rang composé — « 412-2 » pour la
    troisième étape de la carte 412 : deux étapes d'une même carte se
    rapatrieraient sinon dans le même fichier.

    Pour Pixabay seul, dont les conditions interdisent le lien direct
    permanent. Rend None si la copie échoue — l'exercice reste alors sans
    photo, ce qui vaut mieux qu'une URL qu'on n'a pas le droit d'afficher.
    """
    dossier = Path(__file__).resolve().parent.parent / "media" / "photos"
    dossier.mkdir(parents=True, exist_ok=True)
    suffixe = ".jpg" if ".png" not in url.lower() else ".png"
    fichier = dossier / f"{exercise_id}{suffixe}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "SaraLearn/1.0 (learn.sara.education)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            corps = r.read()
        if not corps:
            return None
        fichier.write_bytes(corps)
    except Exception:  # noqa: BLE001 — réseau, disque, 404
        return None
    # Apache sert `media/` sous `/media` — voir la configuration du site.
    return f"/media/photos/{fichier.name}"


async def illustrer(exercise_id: int) -> bool:
    """Pose la photo d'un exercice à partir de sa requête. Silencieuse."""
    with connection() as conn:
        e = conn.execute(
            "SELECT id, image_query, image_url, options, correct_index,"
            "       prompt, exp_title, exp_text"
            "  FROM exercise WHERE id = ?",
            (exercise_id,),
        ).fetchone()
        if e is None or e["image_url"] or not e["image_query"]:
            return False
        exercice = dict(e)
    if quota_epuise():
        return False

    fautif = revele(exercice["image_query"], exercice)
    if fautif:
        # On efface la requête plutôt que de la réessayer indéfiniment :
        # elle est fautive par nature, pas par accident.
        with connection() as conn:
            with transaction(conn):
                conn.execute(
                    "UPDATE exercise SET image_query = NULL WHERE id = ?", (exercise_id,)
                )
        return False

    photo = await chercher(exercice["image_query"])
    if photo is None:
        return False

    # Pixabay interdit le lien direct permanent : sa photo devient un
    # fichier chez nous, et c'est ce chemin-là qui va en base. Un
    # rapatriement raté vaut pas de photo — jamais une URL hors règles.
    if photo["source"] == "Pixabay":
        chemin = await asyncio.to_thread(_rapatrier, photo["url"], exercise_id)
        if chemin is None:
            return False
        photo["url"] = chemin

    with connection() as conn:
        with transaction(conn):
            conn.execute(
                "UPDATE exercise SET image_url = ?, image_alt = ?,"
                " image_credit = ?, image_credit_url = ?, image_source = ?"
                " WHERE id = ?",
                (
                    photo["url"],
                    photo["alt"] or exercice["image_query"],
                    photo["credit"],
                    photo["credit_url"],
                    photo["source"],
                    exercise_id,
                ),
            )
    return True


async def illustrer_chapitre(chapter_id: int) -> int:
    """Les exercices de ce chapitre qui attendent leur photo."""
    if not banques_ouvertes():
        return 0
    with connection() as conn:
        attente = [
            r["id"]
            for r in rows(
                conn,
                "SELECT id FROM exercise WHERE chapter_id = ? AND state = 'validated'"
                "   AND image_url IS NULL AND image_query IS NOT NULL"
                " ORDER BY id",
                (chapter_id,),
            )
        ]
    n = 0
    for eid in attente:
        if await illustrer(eid):
            n += 1
    return n


# ==========================================================================
# LES IMAGES DES ÉTAPES DE L'EXPLICATION
#
# Deux différences avec la photo de la carte, et elles vont dans le même
# sens : ici l'élève a déjà répondu.
#
#   · `revele()` NE S'APPLIQUE PAS. Il interdit de nommer le phénomène
#     sur la question, parce que l'image donnerait la réponse. Sur
#     l'explication, la réponse est donnée depuis deux écrans — cacher
#     le mécanisme n'a plus de sens, c'est lui qu'on veut montrer.
#   · La recherche part du TITRE écrit par le modèle (`image_title`),
#     pas de mots-clés fabriqués après coup. Il nomme ce qu'il faut
#     montrer pour cette étape-là.
#
# Le reste est partagé : les trois banques dans l'ordre, le quota, le
# filtre de contenu, le rapatriement de Pixabay.
# ==========================================================================


async def illustrer_etape(exercise_id: int, rang: int) -> bool:
    """Pose la photo d'une étape. Silencieuse, comme `illustrer`."""
    with connection() as conn:
        e = row(
            conn,
            "SELECT image_title, image_url FROM exercise_step"
            " WHERE exercise_id = ? AND rang = ?",
            (exercise_id, rang),
        )
    if e is None or e["image_url"] or not (e["image_title"] or "").strip():
        return False
    if quota_epuise():
        return False

    photo = await chercher(e["image_title"])
    if photo is None:
        return False

    if photo["source"] == "Pixabay":
        # Le nom du fichier porte le rang : deux étapes de la même carte
        # se rapatrieraient sinon l'une sur l'autre.
        chemin = await asyncio.to_thread(
            _rapatrier, photo["url"], f"{exercise_id}-{rang}"
        )
        if chemin is None:
            return False
        photo["url"] = chemin

    with connection() as conn:
        with transaction(conn):
            conn.execute(
                "UPDATE exercise_step SET image_url = ?, image_alt = ?,"
                " image_credit = ?, image_credit_url = ?, image_source = ?"
                " WHERE exercise_id = ? AND rang = ?",
                (
                    photo["url"],
                    photo["alt"] or e["image_title"],
                    photo["credit"],
                    photo["credit_url"],
                    photo["source"],
                    exercise_id,
                    rang,
                ),
            )
    return True


async def illustrer_les_etapes(chapter_id: int) -> int:
    """Les étapes de ce chapitre qui attendent leur image."""
    if not banques_ouvertes():
        return 0
    with connection() as conn:
        attente = [
            (r["exercise_id"], r["rang"])
            for r in rows(
                conn,
                "SELECT s.exercise_id, s.rang FROM exercise_step s"
                "  JOIN exercise e ON e.id = s.exercise_id"
                " WHERE e.chapter_id = ? AND e.state = 'validated'"
                "   AND s.image_url IS NULL AND s.image_title IS NOT NULL"
                "   AND TRIM(s.image_title) <> ''"
                " ORDER BY s.exercise_id, s.rang",
                (chapter_id,),
            )
        ]
    n = 0
    for eid, rang in attente:
        if await illustrer_etape(eid, rang):
            n += 1
    return n
