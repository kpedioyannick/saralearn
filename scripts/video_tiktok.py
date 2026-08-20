#!/usr/bin/env python3
"""Fabrique une vidéo verticale à partir d'exercices en base.

    python3 scripts/video_tiktok.py --categorie animals --lang en
    python3 scripts/video_tiktok.py --theme the-oceans --lang en --nb 1

Le rendu est en 1080×1920 plein ; `--apercu` donne le 540×960 rapide.

SIX ÉCRANS, ceux de la maquette Claude Design « SaraLearn — Design
moderne RWD », section « Six écrans pour une vidéo TikTok » :

    5a accroche · 5b question · 5c réponse · 5d explication
    5e score du public · 5f appel

Les écrans 5b à 5d sont l'app rejouée telle quelle — bandeau audio,
barre d'avancement, cadres de réponse. 5c ne change RIEN à la mise en
page de 5b : seuls les cadres changent d'état, et l'œil compare sans
être déplacé.

CE SCRIPT NE FAIT AUCUN RENDU. Il ne fait que le pont entre la base et
`sara-video`, le service Remotion déjà en place sur la machine (pm2
`sara-video`, port 3457). C'est lui qui sait rendre du 1080×1920,
parler, et incruster des sous-titres ; le réécrire aurait été refaire
un travail existant, et deux moteurs vidéo à maintenir. Les six écrans
vivent chez lui dans `src/remotion/SaraExerciseScene.jsx`.

LE RYTHME SUIT LA VOIX. La maquette donne des durées d'écran (1,5 s
pour l'accroche, 5 s pour la question, 4 à 5 s pour l'explication) ;
elles sont ici des PLANCHERS. Chaque texte est synthétisé d'abord,
mesuré, et l'écran dure au moins le temps qu'on met à le lire. Une
durée figée coupait la dernière syllabe dès qu'un énoncé était long.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = Path(os.environ.get("SARA_DB", ROOT / "data" / "sara.db"))
VIDEO_API = os.environ.get("SARA_VIDEO_URL", "http://127.0.0.1:3457")

# Les planchers, en secondes. Un écran ne descend jamais sous ces
# valeurs ; il s'allonge si la voix a besoin de plus.
PLANCHER = {
    "accroche": 1.5,
    # Douze secondes : l'énoncé lu, puis les dix secondes de réflexion que
    # l'accroche promet à voix haute. Le plancher est ce qui rend la
    # promesse vraie même quand la question est courte — sans lui, une
    # question de deux mots tiendrait huit secondes et la vidéo mentirait
    # sur sa propre règle du jeu.
    "question": 12.0,
    "reponse": 2.5,
    "explication": 4.5,
    "score": 4.0,
    "appel": 4.5,
}

# Le temps laissé APRÈS la dernière syllabe, avant que l'écran ne change.
# Un écran dure `max(plancher, voix + attente)` : la voix donne le départ,
# elle ne décide plus de la sortie.
#
# Ces valeurs sont calées sur CE QUI RESTE À LIRE quand la voix s'arrête,
# et sur rien d'autre. Un forfait unique de 5 s partout a été essayé : la
# moitié de la vidéo devenait du silence, et surtout du silence sur des
# écrans où la voix venait de tout dire — « la bonne réponse : X », puis
# cinq secondes sur une ligne déjà entendue. C'est là qu'on décroche.
ATTENTE = {
    "accroche": 1.5,     # la ligne du dessous est courte
    "question": 10.0,    # le seul écran qui demande quelque chose : ce
                         # silence est le temps de lire les quatre
                         # réponses et d'en choisir une. C'est aussi les
                         # « dix secondes » annoncées par l'accroche —
                         # les deux chiffres doivent rester d'accord.
    "reponse": 1.0,      # une ligne, déjà dite
    "explication": 2.0,  # le texte est lu pendant qu'il s'affiche
    "score": 2.0,        # un chiffre
    "appel": 3.0,        # le temps de noter l'adresse
}

# Le volume de la musique de fond passé au service. Il la met à 0,4 quand
# il croit la vidéo muette — ce qu'il croit ici, puisque c'est nous qui
# fournissons la voix — et à 0,20 quand il sait qu'une voix parle. On
# passe SOUS son réglage « voix » : à 0,25 la musique couvrait encore
# l'énoncé, et c'est l'énoncé qu'on vient écouter. Descendu deux fois le
# 14/08 — 0,15 puis 0,07, tous deux jugés à l'oreille encore trop forts,
# la musique passait devant les paroles. À 0,03 elle est à 30 dB sous la
# voix : on l'entend dans les respirations, jamais par-dessus un mot.
# Elle est là pour que le silence ne s'entende pas, pas pour être suivie.
# `--musique 0` la coupe tout à fait.
MUSIQUE = 0.03

SITE = os.environ.get("SARA_SITE", "learn.sara.education")
API = os.environ.get("SARA_API_URL", f"https://{SITE}/api")

# Les pistes fabriquées ici. `media/` est déjà servi par Apache
# (Alias /media), donc le service vidéo peut les récupérer par URL sans
# qu'on ait à lui ouvrir un accès disque.
VOIX_DIR = ROOT / "media" / "tts-video"

# Tout ce qui est écrit à l'écran ou dit à voix haute, dans les deux
# langues. Rien de tout cela ne vit dans les scènes Remotion : la même
# scène sert les deux vidéos, et une chaîne oubliée en français au milieu
# d'une vidéo anglaise se verrait tout de suite.
TEXTES = {
    "fr": {
        "types": {
            "qcm": "QCM",
            "true_false": "Vrai ou faux",
            "complete": "Complète",
            "find_error": "Trouve l'erreur",
            "short_answer": "Réponse courte",
            "cloze": "Texte à trous",
        },
        "defaut": "Question",
        "nombres": {1: "Une", 2: "Deux", 3: "Trois", 4: "Quatre", 5: "Cinq", 6: "Six"},
        "accroche": "Teste tes connaissances en {sujet}.",
        "regle": "{n} question{s}, {k} réponses, dix secondes.",
        "commentaire": "Ta réponse en commentaire",
        "question_n": "{type} · question {i} sur {n}",
        "revele": "La bonne réponse",
        "dit_revele": "La bonne réponse : {bonne}.",
        "pourquoi": "Pourquoi {bonne}",
        "explication": "Explication",
        "lu": "Lu à voix haute dans l'app",
        "sur_n": "Sur {n} réponses",
        "trouve": "seulement ont trouvé {bonne}.",
        "trouve_haut": "ont trouvé {bonne}.",
        "dit_score": "Sur {n} réponses, {p} pour cent {seulement}ont trouvé {bonne}.",
        "seulement": "seulement ",
        "dans_les": "Tu étais dans les {p} % ?",
        "la_bonne": "{o} · la bonne",
        "le_piege": "{o} · le piège",
        "les_autres": "les autres",
        "appel_titre": "Viens te défier.",
        "appel_ligne": ("Apprends, réussis, crée, partage. Avec une communauté "
                        "qui écrit ses propres apprentissages."),
        "appel_points": ["Sans compte pour commencer",
                         "Aucune note, aucun classement scolaire"],
        # On ne lit PAS la ligne affichée : dite en entier, la fermeture
        # durait onze secondes, deux fois l'écran le plus long de la
        # maquette. Elle se lit à l'écran, la voix ne garde que l'appel.
        # La dernière phrase de toute la vidéo. Elle finit sur le lien :
        # c'est la seule consigne qu'on veut laisser dans l'oreille, et
        # ce qu'on entend en dernier est ce qu'on retient.
        "dit_appel": "Viens te défier sur {site}. Le lien est en commentaire.",
        # L'adresse À DIRE, pas celle à afficher. Google lit
        # « learn.sara.education » à la française — « lé-arne » — et
        # avale les points. On lui donne donc la version prononcée ;
        # l'écran, lui, garde l'URL vraie (`url` dans l'écran 5f).
        "site_dit": "leurne point sara point éducation",
        # Le code et où trouver le lien. Deux lignes courtes : l'écran
        # dure quatre secondes et demie, et le code doit y tenir seul.
        "code_titre": "Rejoue ce quiz — code",
        "code_note": "Lien en commentaire",
    },
    "en": {
        "types": {
            "qcm": "MCQ",
            "true_false": "True or false",
            "complete": "Complete",
            "find_error": "Spot the mistake",
            "short_answer": "Short answer",
            "cloze": "Fill the gaps",
        },
        "defaut": "Question",
        "nombres": {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"},
        "accroche": "Test what you know about {sujet}.",
        "regle": "{n} question{s}, {k} answers, ten seconds.",
        "commentaire": "Drop your answer in the comments",
        "question_n": "{type} · question {i} of {n}",
        "revele": "The right answer",
        "dit_revele": "The right answer: {bonne}.",
        "pourquoi": "Why {bonne}",
        "explication": "Explanation",
        "lu": "Read aloud in the app",
        "sur_n": "Out of {n} answers",
        "trouve": "only got {bonne}.",
        "trouve_haut": "got {bonne}.",
        "dit_score": "Out of {n} answers, {seulement}{p} per cent got {bonne}.",
        "seulement": "only ",
        "dans_les": "Were you in that {p} %?",
        "la_bonne": "{o} · correct",
        "le_piege": "{o} · the trap",
        "les_autres": "the others",
        "appel_titre": "Come and challenge yourself.",
        "appel_ligne": ("Learn, succeed, create, share. With a community that "
                        "writes its own lessons."),
        "appel_points": ["No account needed to start",
                         "No grades, no school ranking"],
        "dit_appel": "Come and challenge yourself on {site}. The link is in the comments.",
        "site_dit": "learn dot sara dot education",
        "code_titre": "Replay this quiz — code",
        "code_note": "Link in the comments",
    },
}


# ------------------------------------------------------------------ #
# La base                                                             #
# ------------------------------------------------------------------ #

def choisir_theme(conn: sqlite3.Connection, *, categorie: str | None,
                  theme: str | None, nb: int, lang: str) -> dict | None:
    """L'apprentissage sur lequel la vidéo va porter — un seul.

    La vidéo tirait dans TOUTE une catégorie, à travers des
    apprentissages différents. Deux raisons de resserrer :

      · l'accroche annonçait déjà un seul apprentissage — `lot[0]` —
        alors que les questions pouvaient venir de cinq. Elle disait
        donc faux une fois sur deux ;
      · le dernier écran donne maintenant un code de partage, et un code
        appartient à UN apprentissage (`feed._by_code` filtre sur
        `theme_id`). Sans ce resserrement, il n'y a rien à donner qui
        rejoue les questions vues.

    On ne retient que les apprentissages qui ont de quoi remplir la
    vidéo ET un code : sans code, le lien promis n'existe pas.
    """
    where = ["e.state = 'validated'", "e.exp_text IS NOT NULL",
             "length(e.exp_text) > 40", "t.lang = ?", "t.code IS NOT NULL"]
    params: list = [lang]
    if categorie:
        where.append("(c.slug = ? OR c.id = ?)")
        params += [categorie, categorie if categorie.isdigit() else -1]
    if theme:
        where.append("(t.slug = ? OR t.id = ? OR t.code = ?)")
        params += [theme, theme if theme.isdigit() else -1, theme.upper()]

    conn.row_factory = sqlite3.Row
    sql = (
        "SELECT t.id, t.title, t.code, COUNT(*) AS n"
        " FROM exercise e"
        " JOIN theme t ON t.id = e.theme_id"
        " JOIN category c ON c.id = t.category_id"
        " WHERE " + " AND ".join(where) +
        " GROUP BY t.id HAVING n >= ?"
        " ORDER BY RANDOM() LIMIT 1"
    )
    r = conn.execute(sql, [*params, nb]).fetchone()
    return dict(r) if r else None


def exercises(conn: sqlite3.Connection, *, theme_id: int,
              nb: int, lang: str) -> list[dict]:
    """Tire des exercices validés, au hasard, dans l'apprentissage retenu.

    On ne prend que des exercices dont l'explication tient : l'écran 5d
    est bâti sur elle, et une vidéo dont le quatrième écran est vide n'a
    pas d'intérêt.

    Le filtre de langue porte sur le THÈME et non sur la catégorie :
    `permis` existe dans les deux langues sous le même slug, avec des
    thèmes séparés. Filtrer sur la catégorie aurait fait lire des
    énoncés français par la voix anglaise.
    """
    where = ["e.state = 'validated'", "e.exp_text IS NOT NULL",
             "length(e.exp_text) > 40", "t.lang = ?", "t.id = ?"]
    params: list = [lang, theme_id]

    sql = (
        "SELECT e.*, t.title AS theme_title, c.label AS cat_label,"
        "       c.label_en AS cat_label_en"
        " FROM exercise e"
        " JOIN theme t ON t.id = e.theme_id"
        " JOIN category c ON c.id = t.category_id"
        " WHERE " + " AND ".join(where) +
        " ORDER BY RANDOM() LIMIT ?"
    )
    conn.row_factory = sqlite3.Row
    # On tire large puis on écarte les énoncés identiques : le catalogue
    # contient des questions qui ne se distinguent que par leurs options
    # (« Quelle phrase est correctement écrite ? » revient des dizaines de
    # fois), et deux d'affilée dans une même vidéo donnent l'impression
    # d'un bug plutôt que d'un exercice.
    vus: set[str] = set()
    gardes: list[dict] = []
    for r in conn.execute(sql, [*params, nb * 8]).fetchall():
        e = dict(r)
        cle = " ".join(e["prompt"].casefold().split())
        if cle in vus:
            continue
        vus.add(cle)
        gardes.append(e)
        if len(gardes) == nb:
            break
    return gardes


def score_public(conn: sqlite3.Connection, exercice_id: int, options: list[str],
                 correct: int, seuil: int, lang: str) -> dict | None:
    """Ce que le public a répondu à CETTE question — ou rien.

    L'écran 5e affiche un pourcentage en 300 px de haut. Un pourcentage
    calculé sur trois réponses est un chiffre inventé avec une décimale :
    en dessous de `seuil` réponses, la fonction rend `None` et l'écran ne
    part pas. Il s'allumera tout seul quand le trafic sera là — rien à
    rebrancher.

    Rend aussi l'option la plus choisie parmi les fausses : c'est le
    piège, le seul cadre que 5c passe au rouge.
    """
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT chosen_index, COUNT(*) AS n FROM attempt"
        " WHERE exercise_id = ? AND chosen_index IS NOT NULL"
        " GROUP BY chosen_index",
        (exercice_id,),
    ).fetchall()

    compte = {int(r["chosen_index"]): int(r["n"]) for r in rows}
    total = sum(compte.values())
    if total < seuil:
        return None

    juste = compte.get(correct, 0)
    part = juste / total
    faux = sorted(
        ((i, n) for i, n in compte.items() if i != correct and 0 <= i < len(options)),
        key=lambda x: -x[1],
    )
    piege = faux[0][0] if faux else None
    reste = sum(n for i, n in faux[1:])

    T = TEXTES[lang]
    bars = [{"label": T["la_bonne"].format(o=options[correct]), "share": part}]
    if piege is not None:
        bars.append({"label": T["le_piege"].format(o=options[piege]),
                     "share": compte[piege] / total})
    if reste:
        autres = [options[i] for i, _ in faux[1:] if i < len(options)]
        joint = " & " if lang == "en" else " et "
        bars.append({"label": joint.join(autres[:2]) or T["les_autres"],
                     "share": reste / total})

    return {
        "total": total,
        "percent": round(part * 100),
        "trapIndex": piege,
        "bars": bars,
    }


# ------------------------------------------------------------------ #
# La voix                                                             #
# ------------------------------------------------------------------ #

def session(lang: str = "fr") -> str:
    """Une session anonyme, pour appeler /tts. La voix est authentifiée."""
    req = urllib.request.Request(
        f"{API}/auth/anonymous",
        data=json.dumps({"device_id": "video-tiktok-0001", "lang": lang}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["token"]


def dire(texte: str, token: str, lang: str = "fr") -> bytes:
    """Un MP3, par la voix du site.

    On passe par `POST /tts` de SaraLearn plutôt que par un fournisseur
    du service vidéo : c'est la MÊME voix que celle qu'entendent les
    visiteurs, le cache disque de la route sert les deux usages, et la
    clé Google ne vit qu'à un seul endroit.
    """
    req = urllib.request.Request(
        f"{API}/tts",
        data=json.dumps({"text": texte, "lang": lang}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def duree(fichier: Path) -> float:
    """La durée réelle d'un MP3, en secondes.

    ATTENTION au niveau de verbosité : `-v error` sur ffmpeg supprime la
    sortie de plusieurs filtres de mesure. Ici on interroge ffprobe, dont
    la valeur sort sur stdout et non dans le journal — c'est ce qui rend
    la mesure fiable.
    """
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(fichier)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def srt(entries: list[tuple[float, float, str]]) -> str:
    """Le SRT que le service attend, et sur lequel il cale la voix."""
    def stamp(sec: float) -> str:
        h, rest = divmod(sec, 3600)
        m, s = divmod(rest, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"

    out = []
    for i, (start, end, text) in enumerate(entries, start=1):
        out.append(f"{i}\n{stamp(start)} --> {stamp(end)}\n{text.strip()}\n")
    # La ligne vide FINALE n'est pas décorative : sans elle, le lecteur du
    # service ne referme pas le dernier bloc et l'affiche tel quel — on
    # lisait « 3 00:00:25,000 --> 00:00:45,000 Au présent, » à l'écran.
    return "\n".join(out) + "\n"


def morceau(texte: str, token: str, lang: str) -> Path:
    """Une phrase synthétisée, gardée sur disque.

    Les morceaux sont cachés SÉPARÉMENT de la piste assemblée, et sur le
    seul texte : le montage dépend des temps d'attente, la synthèse non.
    Changer le rythme d'une vidéo ne doit pas re-payer la synthèse — ni,
    accessoirement, faire varier la voix d'un rendu à l'autre.
    """
    p = VOIX_DIR / f"dit-{lang}-{hashlib.sha1(texte.encode()).hexdigest()[:16]}.mp3"
    if not p.exists():
        p.write_bytes(dire(texte, token, lang))
    return p


def voix(textes: list[str], planchers: list[float], attentes: list[float],
         token: str | None, cle: str, lang: str = "fr") -> tuple[list[float], dict]:
    """Synthétise, mesure, assemble — et rend les durées d'écran.

    Chaque texte est fabriqué à part, puis décalé à sa seconde d'entrée
    et mélangé aux autres. Sans ce décalage, les textes s'enchaîneraient
    à la suite et la voix parlerait de l'explication pendant qu'on
    affiche encore la question.

    Les durées rendues sont `max(plancher, voix + attente)` : l'écran
    tient au moins le temps qu'il faut pour le lire, et s'allonge quand
    la phrase est longue.

    Sans jeton (`--voix` autre que `sara`), on ne synthétise rien et on
    rend les planchers tels quels.
    """
    if not token:
        return list(planchers), {}

    VOIX_DIR.mkdir(parents=True, exist_ok=True)
    # L'empreinte porte le rythme autant que le texte : les silences sont
    # montés DANS la piste, deux rythmes différents ne sont pas le même
    # fichier. Sans cela, baisser ou monter une attente ne changerait
    # rien — on reservirait le montage précédent.
    empreinte = hashlib.sha1(
        "|".join(textes + [f"{p}/{a}" for p, a in zip(planchers, attentes)]).encode()
    ).hexdigest()[:12]
    base = VOIX_DIR / f"{cle}-{empreinte}"
    mp3, fiche = base.with_suffix(".mp3"), base.with_suffix(".json")

    # Le cache porte AUSSI les durées : sans la fiche, on retrouverait la
    # piste mais plus le découpage qu'elle suppose, et les écrans
    # tomberaient à côté de la voix.
    if mp3.exists() and fiche.exists():
        d = json.loads(fiche.read_text())
        return d["phases"], {
            "audioSrc": f"https://{SITE}/media/tts-video/{mp3.name}",
            "audioDurationSec": d["total"],
        }

    morceaux = [morceau(t, token, lang) for t in textes]
    phases = [max(p, duree(m) + a)
              for p, m, a in zip(planchers, morceaux, attentes)]
    departs, curseur = [], 0.0
    for p in phases:
        departs.append(curseur)
        curseur += p
    total = curseur

    entrees, filtres = [], []
    for i, (m, start) in enumerate(zip(morceaux, departs)):
        entrees += ["-i", str(m)]
        filtres.append(f"[{i}:a]adelay={int(start * 1000)}|{int(start * 1000)}[a{i}]")
    filtre = (
        ";".join(filtres)
        + ";" + "".join(f"[a{i}]" for i in range(len(morceaux)))
        + f"amix=inputs={len(morceaux)}:normalize=0,apad,atrim=0:{total}[out]"
    )
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", *entrees,
         "-filter_complex", filtre, "-map", "[out]", str(mp3)],
        check=True,
    )

    fiche.write_text(json.dumps({"phases": phases, "total": total}))
    return phases, {
        "audioSrc": f"https://{SITE}/media/tts-video/{mp3.name}",
        "audioDurationSec": total,
    }


# ------------------------------------------------------------------ #
# Les six écrans                                                      #
# ------------------------------------------------------------------ #

def phrases_de(texte: str) -> list[str]:
    """Le texte coupé sur ses phrases. Utilisé par l'écran ET par la voix."""
    out = [p.strip() for p in
           re.split(r"(?<=[.!?…])\s+(?=[«\"(A-ZÀ-ÖØ-Þ])", (texte or "").strip())
           if p.strip()]
    return out or ([texte.strip()] if texte else [])


def etapes(texte: str) -> list[str]:
    """L'explication en étapes numérotées, comme sur l'écran 5d.

    La maquette montre trois étapes courtes ; la base ne stocke qu'un
    paragraphe. On le coupe sur ses phrases, on plafonne à trois — au
    delà l'écran déborde — et on verse le surplus dans la dernière. Deux
    phrases donnent deux étapes : la troisième place reste vide plutôt
    que d'être comblée par autre chose. `exp_tip` la remplissait avant
    d'être retiré (migration 017).
    """
    phrases = phrases_de(texte)

    if len(phrases) > 3:
        phrases = phrases[:2] + [" ".join(phrases[2:])]
    return phrases


def ecran_accroche(cat: str, theme: str, nb: int, nb_options: int,
                   token: str | None, lang: str) -> dict:
    """5a — le sujet, la règle du jeu, et la demande de commentaire."""
    T = TEXTES[lang]
    titre = T["accroche"].format(sujet=cat.lower())
    ligne = T["regle"].format(
        n=T["nombres"].get(nb, str(nb)),
        s="s" if nb > 1 else "",
        k=T["nombres"].get(nb_options, str(nb_options)).lower(),
    )
    # On ne lit QUE le titre. La ligne du dessous se lit à l'écran en
    # moins de temps qu'il n'en faut pour la dire, et l'accroche doit
    # rester courte : c'est elle qui décide si l'on reste.
    phases, audio = voix([titre], [PLANCHER["accroche"]], [ATTENTE["accroche"]],
                         token, f"accroche-{lang}", lang)
    return {
        "type": "sara-intro",
        "title": titre,
        "eyebrow": f"{cat} · {theme}",
        "line": ligne,
        "cta": T["commentaire"],
        "holdSec": phases[0],
        "subtitlesSrt": srt([(0, phases[0], titre)]),
        **audio,
    }


def ecran_exercice(e: dict, rang: int, sur: int, stats: dict | None,
                   token: str | None, lang: str) -> dict:
    """5b · 5c · 5d — la question, la réponse, l'explication.

    Une seule slide pour trois écrans : la mise en page de 5b et 5c est
    la MÊME, et les faire basculer à l'intérieur d'une slide est ce qui
    garantit qu'aucun pixel ne bouge entre les deux.
    """
    T = TEXTES[lang]
    options = [o.get("label", "") for o in json.loads(e["options"])]
    correct = e["correct_index"] if 0 <= e["correct_index"] < len(options) else 0
    # `rstrip` sur la ponctuation : les libellés d'options finissent
    # souvent par un point, et « … heures.. » s'entend à la lecture.
    bonne = options[correct].rstrip(" .;:")

    # LA VOIX NE LIT PLUS LES OPTIONS, seulement l'énoncé. Les lire coûtait
    # douze secondes sur une vidéo de soixante-et-onze, et les disait à un
    # rythme que personne ne suit : quatre réponses de vingt mots à la
    # file, sans pouvoir revenir en arrière. Elles sont écrites en gros à
    # l'écran, l'œil les compare mieux que l'oreille ne les retient. La
    # voix pose la question, puis se tait — et ce silence EST le temps de
    # réflexion.
    parle = [
        e["prompt"],
        T["dit_revele"].format(bonne=bonne),
        e["exp_text"],
    ]
    # L'attente longue ne vaut QUE pour la question : c'est le seul écran
    # où l'on demande quelque chose à l'élève. Depuis que les options ne
    # sont plus lues, elle porte SEULE le temps de choisir — d'où dix
    # secondes pleines, et non plus six par-dessus une lecture.
    phases, audio = voix(
        parle,
        [PLANCHER["question"], PLANCHER["reponse"], PLANCHER["explication"]],
        [ATTENTE["question"], ATTENTE["reponse"], ATTENTE["explication"]],
        token, f"ex-{e['id']}", lang,
    )
    q, a, x = phases
    total = q + a + x

    return {
        "type": "sara-exercise",
        "title": e["theme_title"],
        "theme": e["theme_title"],
        "typeLabel": T["question_n"].format(
            type=T["types"].get(e["type_question"], T["defaut"]), i=rang, n=sur),
        "revealLabel": T["revele"],
        "audioNote": T["lu"],
        "statement": e["prompt"],
        "body": e["body"],
        "options": options,
        "correctIndex": correct,
        # Le piège vient des vraies réponses. Sans données, il est absent
        # et aucun cadre ne passe au rouge : on ne désigne pas un piège
        # au jugé, ce serait mentir sur ce que les gens ont répondu.
        **({"trapIndex": stats["trapIndex"]} if stats and stats["trapIndex"] is not None else {}),
        # « Pourquoi 36 » marche parce que la réponse est courte. Quand
        # elle est longue ou qu'elle commence par une ponctuation — les
        # exercices « trouve l'erreur » désignent parfois une virgule —
        # la formule devient illisible et on retombe sur le mot simple.
        "explanationLabel": (T["pourquoi"].format(bonne=bonne)
                             if len(bonne) <= 24 and bonne[:1].isalnum()
                             else T["explication"]),
        "explanationTitle": e["exp_title"] or "",
        "explanation": e["exp_text"],
        "steps": etapes(e["exp_text"]),
        "progressFrom": (rang - 1 + 0.45) / sur,
        "progressTo": (rang - 1 + 0.85) / sur,
        # holdSec doit valoir la somme des phases : c'est lui que la
        # timeline du service lit pour réserver la place de la slide.
        "holdSec": total,
        "phases": {"question": q, "answer": a, "explanation": x},
        "subtitlesSrt": srt([(0, q, parle[0]), (q, q + a, parle[1]), (q + a, total, parle[2])]),
        **audio,
    }


def ecran_score(e: dict, stats: dict, options: list[str], correct: int,
                token: str | None, lang: str) -> dict:
    """5e — le score du public. Vert plein cadre, le chiffre porte l'écran."""
    T = TEXTES[lang]
    bonne = options[correct].rstrip(" .;:")
    p = stats["percent"]
    # « seulement » n'a de sens que si le chiffre est bas. Au-dessus de la
    # moitié, la phrase se retourne — sinon on félicite le public d'avoir
    # échoué.
    bas = p < 50
    ligne = (T["trouve"] if bas else T["trouve_haut"]).format(bonne=bonne)
    dit = T["dit_score"].format(n=stats["total"], p=p, bonne=bonne,
                                seulement=T["seulement"] if bas else "")
    phases, audio = voix([dit], [PLANCHER["score"]], [ATTENTE["score"]],
                         token, f"score-{e['id']}-{lang}", lang)
    return {
        "type": "sara-stats",
        "eyebrow": T["sur_n"].format(n=stats["total"]),
        "headline": f"{p} %",
        "line": ligne,
        "bars": stats["bars"],
        "cta": T["dans_les"].format(p=p),
        "holdSec": phases[0],
        "subtitlesSrt": srt([(0, phases[0], dit)]),
        **audio,
    }


def ecran_appel(token: str | None, lang: str, code: str | None = None) -> dict:
    """5f — la promesse produit, le code, et où trouver le lien.

    Pas de classement : la maquette l'a retiré. C'était le bon choix —
    le palmarès réel n'aurait affiché que des comptes de test, tous
    nommés « Smoke », ce qui ressemble à une panne plutôt qu'à un
    classement.

    Le CODE prend le premier rôle, l'adresse passe derrière. Six
    caractères se retiennent le temps d'ouvrir l'app ; une URL non
    cliquable se retape mal, et le commentaire qui la porte s'enterre
    sous les autres. Le code, lui, survit aux deux.

    La voix ne le dit pas : elle épellerait « K7F2QM » lettre à lettre
    sur trois secondes, et ce n'est pas une chose à écouter.
    """
    T = TEXTES[lang]
    titre, ligne = T["appel_titre"], T["appel_ligne"]
    dit = T["dit_appel"].format(titre=titre, ligne=ligne,
                                site=T.get("site_dit", SITE))
    phases, audio = voix([dit], [PLANCHER["appel"]], [ATTENTE["appel"]],
                         token, f"appel-{lang}", lang)
    return {
        "type": "sara-outro",
        "title": titre,
        "line": ligne,
        "points": T["appel_points"],
        # Pas de bouton : dans une vidéo il n'est pas cliquable. L'écran
        # ne garde que l'adresse, en grand — c'est elle qu'on retape.
        "url": SITE,
        # Les deux champs sont facultatifs côté rendu : sans code, l'écran
        # est celui d'avant, à l'identique.
        "code": code,
        "codeLabel": T["code_titre"] if code else None,
        "note": T["code_note"] if code else None,
        "holdSec": phases[0],
        "subtitlesSrt": srt([(0, phases[0], dit)]),
        **audio,
    }


# ------------------------------------------------------------------ #

def post(path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        VIDEO_API + path,
        data=json.dumps(body).encode() if body is not None else None,
        method="POST" if body is not None else "GET",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main() -> None:
    # Les écrans lisent le rythme dans cette table ; la ligne de commande
    # la remplace plutôt que de traverser quatre signatures pour des
    # valeurs qui ne changent pas en cours de vidéo.
    global ATTENTE

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--categorie", help="slug ou identifiant de catégorie")
    ap.add_argument("--theme", help="slug, identifiant ou code d'un apprentissage précis ; "
                                    "sinon un est tiré au hasard dans la catégorie")
    ap.add_argument("--nb", type=int, default=2, help="exercices par vidéo (défaut 2)")
    ap.add_argument("--lang", default="fr", choices=["fr", "en"],
                    help="langue des exercices ET de la voix (défaut fr)")
    # LA PLEINE QUALITÉ EST LE DÉFAUT. L'aperçu à 540×960 servait à
    # régler vite ; il ne sert plus à rien maintenant que la mise en page
    # est calée, et il donnait un texte flou qu'on prenait pour un défaut
    # de police. `--hd` reste accepté pour ne casser aucune commande
    # déjà écrite — il ne fait simplement plus rien.
    ap.add_argument("--apercu", action="store_true",
                    help="qualité d'aperçu 540×960 plutôt que le 1080×1920 plein")
    ap.add_argument("--hd", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--voix", default="sara",
                    help="sara (la voix du site, Google), piper, elevenlabs, suno, none")
    ap.add_argument("--seuil-stats", dest="seuil_stats", type=int, default=30,
                    help="réponses minimum avant d'afficher l'écran 5e (défaut 30)")
    ap.add_argument("--attente", type=float, default=1.0, metavar="FACTEUR",
                    help="multiplie TOUTES les pauses d'un coup : 0.7 pour "
                         "resserrer, 1.4 pour laisser souffler (défaut 1)")
    ap.add_argument("--attente-question", dest="attente_question", type=float,
                    metavar="SECONDES",
                    help=f"impose la pause de l'écran de question, en secondes "
                         f"(défaut {ATTENTE['question']:g})")
    ap.add_argument("--musique", type=float, default=MUSIQUE,
                    help=f"volume de la musique de fond, 0 à 1 (défaut {MUSIQUE:g})")
    ap.add_argument("--json", action="store_true",
                    help="écrit le payload sur la sortie et n'appelle pas le service")
    ap.add_argument("--attendre", type=int, default=600, help="secondes avant d'abandonner")
    args = ap.parse_args()

    ATTENTE = {k: v * args.attente for k, v in ATTENTE.items()}
    if args.attente_question is not None:
        ATTENTE["question"] = args.attente_question

    # `--theme` désigne déjà un apprentissage : exiger la catégorie en
    # plus reviendrait à faire retrouver le rayon d'un livre qu'on tient
    # dans la main.
    if not args.categorie and not args.theme:
        sys.exit("Précise --categorie ou --theme.")

    lang = args.lang
    with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as conn:
        # Un seul apprentissage par vidéo : c'est ce qui rend le lot
        # rejouable par un code. Voir `choisir_theme`.
        sujet = choisir_theme(conn, categorie=args.categorie, theme=args.theme,
                              nb=args.nb, lang=lang)
        if sujet is None:
            sys.exit(f"Aucun apprentissage en « {lang} » avec {args.nb} exercice(s) "
                     f"validé(s) et expliqués, ET un code de partage, dans ce "
                     f"périmètre. Baisse --nb, ou vise un autre --theme.")
        lot = exercises(conn, theme_id=sujet["id"], nb=args.nb, lang=lang)
        if not lot:
            sys.exit(f"Aucun exercice validé en « {lang} » avec une explication "
                     f"dans ce périmètre.")

        scores = {}
        for e in lot:
            opts = [o.get("label", "") for o in json.loads(e["options"])]
            c = e["correct_index"] if 0 <= e["correct_index"] < len(opts) else 0
            scores[e["id"]] = score_public(conn, e["id"], opts, c, args.seuil_stats, lang)

    if len(lot) < args.nb:
        print(f"  seulement {len(lot)} exercice(s) trouvé(s) sur {args.nb} demandés")

    # La voix du site : on synthétise nous-mêmes et on fournit les
    # pistes au service, qui ne parle alors plus de lui-même.
    token = session(lang) if args.voix == "sara" else None
    fournisseur = "none" if args.voix == "sara" else args.voix

    # `permis` n'a pas de libellé anglais distinct en base ; on retombe
    # alors sur le libellé français plutôt que d'afficher un vide.
    cat = (lot[0]["cat_label_en"] or lot[0]["cat_label"]) if lang == "en" else lot[0]["cat_label"]
    theme = lot[0]["theme_title"]
    nb_options = len(json.loads(lot[0]["options"]))

    slides = [ecran_accroche(cat, theme, len(lot), nb_options, token, lang)]
    for i, e in enumerate(lot, start=1):
        stats = scores[e["id"]]
        slides.append(ecran_exercice(e, i, len(lot), stats, token, lang))
        if stats:
            opts = [o.get("label", "") for o in json.loads(e["options"])]
            c = e["correct_index"] if 0 <= e["correct_index"] < len(opts) else 0
            slides.append(ecran_score(e, stats, opts, c, token, lang))
    slides.append(ecran_appel(token, lang, sujet["code"]))

    payload = {
        "title": cat,
        "format": "portrait",          # 1080×1920, le format de la plateforme
        "quality": "preview" if args.apercu else "hd",
        "voiceProvider": fournisseur,
        # Pas de sous-titres incrustés : l'app n'en a pas, et la vidéo
        # doit lui ressembler. Le SRT continue de partir — c'est lui qui
        # porte le texte que la voix lit et qui cale son minutage — mais
        # il ne s'affiche plus.
        "showSubtitles": False,
        # Sans cette ligne, le service applique le volume « vidéo muette »
        # (0,4) : il ne sait pas que les pistes qu'on lui donne parlent.
        "bgMusicVolume": args.musique,
        "slides": slides,
    }

    duree_totale = sum(s["holdSec"] for s in slides)
    avec_score = sum(1 for s in slides if s["type"] == "sara-stats")
    print(f"  {lang} · {len(lot)} exercice(s) · {len(slides)} écrans · "
          f"{duree_totale:.0f} s · voix {args.voix}")
    # Le lien à coller en commentaire ou en description. Il est imprimé
    # même en `--json` : c'est la moitié de la boucle « je regarde, je
    # rejoue », et la chercher à la main dans le payload serait absurde.
    print(f"  apprentissage : {sujet['title']}")
    print(f"  code : {sujet['code']}")
    print(f"  lien : https://{SITE}/?code={sujet['code']}")
    if avec_score:
        print(f"  score du public : {avec_score} écran(s)")
    else:
        print(f"  score du public : aucun écran — moins de {args.seuil_stats} "
              f"réponses par exercice en base")
    for e in lot:
        print(f"     {e['prompt'][:64]}")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    try:
        job = post("/api/videos", payload)
    except urllib.error.HTTPError as exc:
        sys.exit(f"Le service vidéo refuse : {exc.read().decode()[:300]}")
    except urllib.error.URLError as exc:
        sys.exit(f"Service vidéo injoignable sur {VIDEO_API} : {exc.reason}\n"
                 f"Vérifie `pm2 describe sara-video`.")

    vid = job["videoId"]
    print(f"  rendu lancé : {vid}")

    started = time.time()
    while time.time() - started < args.attendre:
        time.sleep(5)
        state = post(f"/api/videos/{vid}")
        if state["status"] == "done":
            print(f"  prêt : {state['videoUrl']}")
            return
        if state["status"] == "error":
            sys.exit(f"Rendu en échec : {state.get('error')}")
        print(f"  … {state['status']} ({int(time.time() - started)} s)")

    sys.exit(f"Toujours pas prêt après {args.attendre} s. Suivi : {VIDEO_API}/api/videos/{vid}")


if __name__ == "__main__":
    main()
