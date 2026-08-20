#!/usr/bin/env python3
"""Sème l'arbre de connaissance depuis Wikipédia.

Deux arbres, deux étapes.

`--step arbre` construit `chapter`. Il part de `theme.seed_url`, lit les
renvois « Main article » de l'article, crée un chapitre par renvoi, et
recommence sur chacun.

    Pourquoi les renvois « Main article » et rien d'autre : c'est le seul
    lien de Wikipédia qui soit une décision éditoriale — quelqu'un a jugé
    qu'un sous-sujet méritait sa propre page. Les trois autres pistes ont
    été mesurées et écartées :

      · liens du corps de l'article — 8 462 candidats au niveau 1 sur les
        9 graines, dont des accidents de radiothérapie, sept biographies
        de physiciens et une déesse grecque pour le seul article « Light » ;
      · section « See also » — 71 liens pour les neuf thèmes réunis, dont
        deux revues scientifiques et une série télévisée ; « The Sky » en
        a deux ;
      · catégories — « Category:Light » contient un logiciel d'éclairage,
        du droit, de l'art et de la fiction, et ne contient pas « Rainbow ».

    Les renvois « Main article » donnent 218 sous-sujets au niveau 1, et
    surtout : L'ARBRE S'ÉPUISE. Mesuré depuis « Sky » — 5 sous-sujets au
    niveau 1, 31 au niveau 2, 198 au niveau 3, puis 8 au niveau 4, où
    quatre articles sur cinq n'ont plus aucun sous-sujet. Le graphe des
    liens du corps, lui, ne se referme jamais.

`--step sections` remplit `exercise_prompt`. Pour chaque chapitre, il lit
le plan de l'article et le recopie tel quel : une section sans
sous-section porte son contenu, une section qui en a n'est qu'un titre et
ses sous-sections deviennent ses enfants. Le contenu est donc toujours
sur une feuille.

    Le filtre s'applique À TOUS LES NIVEAUX, pas seulement aux sections de
    tête — sur « Heart », c'est au deuxième niveau que se cachent
    « Diseases », « Diagnosis », « Treatment » et « Cuisine ». Un parent
    écarté emporte ses enfants ; un parent dont tous les enfants sont
    écartés tombe à son tour, sinon il reste un titre creux.

Tout entre en `status='draft'`. Rien ne produit d'exercice avant relecture.

    python3 scripts/semer_wikipedia.py --step status
    python3 scripts/semer_wikipedia.py --step arbre --theme light --dry-run
    python3 scripts/semer_wikipedia.py --step arbre
    python3 scripts/semer_wikipedia.py --step sections
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "sara.db"
CACHE = ROOT / "data" / "cache_wikipedia"


def _charge_env() -> None:
    """`.env` n'est lu que par le service ; ce script part d'un shell."""
    fichier = ROOT / ".env"
    if not fichier.exists():
        return
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith("#") and "=" in ligne:
            cle, _, val = ligne.partition("=")
            __import__("os").environ.setdefault(cle.strip(), val.strip().strip("'\""))


_charge_env()
_env = __import__("os").environ
LLM_URL = _env.get("SARA_LLM_URL", "https://api.deepseek.com/chat/completions")
LLM_MODEL = _env.get("SARA_LLM_MODEL", "deepseek-chat")
API_KEY = _env.get("DEEPSEEK_API_KEY", "").strip()

API = "https://en.wikipedia.org/w/api.php"
# Wikipédia demande un agent identifiable avec un moyen de contact. Un
# agent anonyme se fait couper au bout de quelques centaines d'appels.
UA = {"User-Agent": "SaraLearn/1.0 (https://saralearn.fr; yannick.kpedio@gmail.com)"}
PAUSE = 0.2

# ---------------------------------------------------------------------
# Les filtres, tirés d'un relevé sur 41 articles et 381 sections
# ---------------------------------------------------------------------

# L'appareil de l'encyclopédie. Ces titres ne désignent jamais du
# contenu : à eux seuls ils retirent 35 % des sections (References dans
# 39 articles sur 41, External links dans 36, See also dans 34).
APPAREIL = {
    "references", "reference", "notes", "notes and references",
    "references and notes", "external links", "external link", "see also",
    "further reading", "bibliography", "citations", "cited sources",
    "general references", "explanatory notes", "footnotes", "works cited",
    "sources", "gallery", "additional images", "literature", "publications",
}

# L'outil, pas l'œuvre. La règle éditoriale du projet : on parle de ce qui
# a été créé et de la manière dont ça fonctionne, jamais de ce que l'homme
# fabrique, mesure ou nomme pour son usage.
OUTIL = {
    "history", "etymology", "naming", "terminology", "nomenclature",
    "in culture", "in popular culture", "popular culture", "cultural significance",
    "society and culture", "in fiction", "in art", "in religion", "in mythology",
    "symbolism", "mythology", "folklore", "cuisine",
    "measurement", "measurements", "units", "unit", "instruments",
    "applications", "application", "uses", "use", "human uses", "usage",
    "research", "exploration", "discovery", "observation",
    "clinical significance", "diseases", "disease", "disorders", "diagnosis",
    "treatment", "medicine", "medical uses", "health", "health effects", "safety",
    "economics", "industry", "technology", "conservation", "conservation status",
    "legal status", "law", "regulation", "standards", "politics", "economy",
    "human impact", "human interaction", "human activity", "relationship with humans",
}

# Un titre composé échappe à l'égalité exacte : « Etymology and
# terminology », « Scientific history », « Religion, culture and
# mythology », « Volcanoes and humans » passaient tous au travers. On
# teste donc aussi MOT À MOT — un seul de ces mots dans le titre suffit.
OUTIL_MOTS = {
    "history", "historical", "etymology", "terminology", "nomenclature",
    "mythology", "folklore", "legend", "legends", "religion", "religious",
    "culture", "cultural", "art", "arts", "literature", "fiction",
    "symbolism", "symbolic", "poetry", "music", "cinema",
    "mathematical", "mathematics", "equation", "equations", "formula",
    "derivation", "calculation", "experiment", "experiments",
    "measurement", "measuring", "unit", "units", "instrument", "instruments",
    "safety", "hazard", "hazards", "risk", "risks", "benefit", "benefits",
    "economy", "economic", "economics", "industry", "industrial",
    "medicine", "medical", "disease", "diseases", "disorder", "disorders",
    "treatment", "diagnosis", "therapy", "surgery", "vaccine", "drug",
    "technology", "engineering", "manufacture", "manufacturing",
    "exploration", "mission", "missions", "spacecraft", "telescope",
    "law", "legal", "legislation", "politics", "political", "war", "military",
    "sport", "sports", "economics", "trade", "commercial",
}

# « human » seul est piégeux : le thème « The Human Being » l'emploie
# légitimement partout. On ne l'attrape qu'en tournure — c'est là qu'il
# désigne l'impact ou l'usage, pas le corps.
OUTIL_TOURNURES = (
    "and humans", "and people", "humans and", "people and",
    "human impact", "human use", "human activity", "human interaction",
    "human influence", "in humans", "for humans", "by humans",
    "relationship with", "interaction with",
)

# Motifs de début de titre.
OUTIL_DEBUT = (
    "history of", "in popular", "in the arts", "cultural ",
    "exploration of", "study of", "research on", "use in", "uses in",
    "measurement of", "applications in", "list of", "timeline of",
)

# Articles à ne pas prendre pour chapitres : ce sont des annuaires, pas
# des sujets. Relevés dans les renvois eux-mêmes — « List of light
# sources », « List of natural satellites », « Lists of animals »,
# « Outline of human anatomy ».
CHAPITRE_REFUSE_DEBUT = (
    "list of", "lists of", "outline of", "index of", "timeline of",
    "glossary of", "comparison of", "bibliography of", "history of",
)


def sans_accent(t: str) -> str:
    plat = unicodedata.normalize("NFD", t)
    return "".join(c for c in plat if unicodedata.category(c) != "Mn")


def slugifie(titre: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", sans_accent(titre).lower()).strip("-")
    return s[:80] or "sans-titre"


MOTS = re.compile(r"[a-z]+")


def titre_ecarte(titre: str) -> str | None:
    """Rend la raison du rejet, ou None si la section est gardée."""
    bas = sans_accent(titre).strip().lower()
    if bas in APPAREIL:
        return "appareil"
    if bas in OUTIL or bas.startswith(OUTIL_DEBUT):
        return "outil"
    if any(t in bas for t in OUTIL_TOURNURES):
        return "outil"
    mots = set(MOTS.findall(bas))
    touche = mots & OUTIL_MOTS
    if touche:
        return f"outil ({sorted(touche)[0]})"
    return None


def chapitre_ecarte(titre: str) -> str | None:
    bas = titre.strip().lower()
    if bas.startswith(CHAPITRE_REFUSE_DEBUT):
        return "annuaire"
    if ":" in titre.split(" ")[0]:          # Portal:, Category:, Template:
        return "hors espace principal"
    if titre_ecarte(titre):
        return titre_ecarte(titre)
    return None


# ---------------------------------------------------------------------
# Le juge — l'étage qu'aucune liste de mots ne remplace
#
# Mesuré : « The Sky », le plus petit des neuf thèmes, donne 213
# chapitres à profondeur 3 et finit sur « Airport crash tender », un
# camion de pompiers d'aéroport. Le filtre par nom n'en avait écarté
# que 21 — ni « Aviation », ni « Thrust », ni « Ballistics » ne
# ressemblent à un mot d'une liste.
#
# La cause est structurelle : l'article « Flight » de Wikipédia traite
# du vol des oiseaux ET de l'aéronautique dans la même page. Le renvoi
# est bon, ce qu'il ouvre est à moitié hors sujet.
#
# LE JUGE NE TRIE PAS, IL EMPÊCHE D'OUVRIR. Un candidat refusé n'est
# jamais exploré, donc les 180 articles qui pendent sous « Aviation »
# ne sont jamais visités. C'est la différence entre un arbre de 200
# chapitres et un arbre de 8 000.
#
# Le motif — la recherche propose, le modèle décide, avec le droit de
# refuser — est repris de `wikipedia_source.py`, où il avait déjà fait
# ses preuves sur le choix des articles.
# ---------------------------------------------------------------------

JUGE = """You are sorting Wikipedia articles for a children's general-knowledge \
quiz about the natural world — what exists and how it works.

KEEP an article if any substantial part of it is about a thing that exists \
in nature: a creature, a substance, a place, a natural process, a part of a \
living body, something in the sky or under the ground.

KEEP IT EVEN IF it also covers machines, measurement or human history. \
Mixed articles are kept: the human sections are stripped out later, and \
its sub-topics are judged one by one. Only the article itself is being \
judged here, not what it might lead to.

REJECT an article only when it is ENTIRELY about something people made, \
measured, named, organised or told stories about — a machine, a vehicle, \
an instrument, a unit, a formula, a technique, an industry, a treatment, \
a law, a war, a person, a book, a belief, a sport, a named human project.

REJECT it as well if it could not be explained to a ten-year-old at all — \
anything that needs formal mathematics or specialist vocabulary even to \
state what it is about.

When you hesitate, KEEP. A wrong keep is deleted in one click; a wrong \
reject silently loses every sub-topic beneath it.

Theme being filled: {theme}
Parent subject: {parent}
Candidate article: {titre}
First lines of the article:
{extrait}

Answer with JSON only: {{"keep": true or false, "why": "six words at most"}}"""


def _extrait(titre: str, n: int = 600) -> str:
    """Les premières lignes de l'article — juger sur le titre seul rate.

    « Cesia », « Te lapa », « Selenography » : le titre ne dit rien. Le
    résumé de tête dit tout, et il tient en quelques centaines de
    caractères.
    """
    d = _appel({"action": "query", "titles": titre, "prop": "extracts",
                "explaintext": 1, "exintro": 1, "redirects": 1})
    pages = d.get("query", {}).get("pages", [])
    return (pages[0].get("extract", "") if pages else "")[:n]


def juge(titre: str, theme: str, parent: str) -> tuple[bool, str]:
    """Rend (garder, raison). En cas de panne du modèle : on garde.

    Refuser par défaut couperait des branches entières sur un incident
    réseau, et un `DELETE` en base rattrape un faux positif — rien ne
    rattrape une branche jamais explorée.
    """
    if not API_KEY:
        return True, "sans juge (clé absente)"

    question = JUGE.format(theme=theme, parent=parent, titre=titre,
                           extrait=_extrait(titre))
    # La clé porte sur la QUESTION ENTIÈRE, consigne comprise : retoucher
    # la consigne invalide le cache tout seul, sans qu'on ait à y penser.
    cle = hashlib.sha1(question.encode()).hexdigest()
    fichier = CACHE / "juge" / cle[:2] / f"{cle}.json"
    if fichier.exists():
        d = json.loads(fichier.read_text(encoding="utf-8"))
        return bool(d["keep"]), d["why"]

    def retiens(keep: bool, why: str) -> tuple[bool, str]:
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text(json.dumps({"keep": keep, "why": why}, ensure_ascii=False),
                           encoding="utf-8")
        return keep, why

    corps = json.dumps({
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": question}],
        "max_tokens": 120, "stream": False, "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        LLM_URL, data=corps,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {API_KEY}", **UA})
    for essai in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                brut = json.load(r)["choices"][0]["message"]["content"]
            debut = brut.find("{")
            if debut == -1:
                return retiens(True, "réponse illisible")
            d, _ = json.JSONDecoder().raw_decode(brut[debut:])
            return retiens(bool(d.get("keep", True)), str(d.get("why", ""))[:40])
        except Exception:
            if essai < 2:
                time.sleep(2 ** essai)
    # Panne réseau : on ne met PAS en cache, la prochaine passe réessaiera.
    return True, "juge injoignable"


# ---------------------------------------------------------------------
# L'accès à Wikipédia, avec cache disque
#
# Une reprise après interruption ne doit pas re-télécharger ce qui l'a
# déjà été : un arbre à profondeur 4 fait des milliers d'appels, et
# refaire le chemin depuis le début à chaque essai est intenable — pour
# nous comme pour Wikipédia.
# ---------------------------------------------------------------------

def _appel(params: dict) -> dict:
    params = {**params, "format": "json", "formatversion": 2}
    cle = hashlib.sha1(urllib.parse.urlencode(sorted(params.items())).encode()).hexdigest()
    fichier = CACHE / cle[:2] / f"{cle}.json"
    if fichier.exists():
        return json.loads(fichier.read_text(encoding="utf-8"))

    url = f"{API}?{urllib.parse.urlencode(params)}"
    for essai in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                d = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and essai < 3:
                time.sleep(2 ** essai); continue
            raise
        except Exception:
            if essai < 3:
                time.sleep(2 ** essai); continue
            raise
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    time.sleep(PAUSE)
    return d


def page(titre: str) -> dict | None:
    """Titre canonique, identifiants, révision. None si la page n'existe pas.

    Les renvois « Main article » pointent souvent sur une redirection :
    on la suit ici pour que `source_url` porte toujours l'adresse finale,
    sans quoi la contrainte d'unicité laisserait passer le même article
    sous deux noms.
    """
    d = _appel({"action": "query", "titles": titre, "prop": "info",
                "redirects": 1, "inprop": "url"})
    pages = d.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing") or pages[0].get("invalid"):
        return None
    p = pages[0]
    if p.get("ns") != 0:
        return None
    return {"titre": p["title"], "pageid": p["pageid"],
            "revision": p.get("lastrevid"), "url": p.get("fullurl")}


MOTIF_MAIN = re.compile(r"\{\{\s*(?:main|main article|further)\s*\|([^{}]+)\}\}", re.I)


def sous_sujets(titre: str) -> list[str]:
    """Les renvois « Main article » de l'article, dans l'ordre du texte."""
    d = _appel({"action": "parse", "page": titre, "prop": "wikitext"})
    if "parse" not in d:
        return []
    out, vus = [], set()
    for bloc in MOTIF_MAIN.findall(d["parse"]["wikitext"]):
        for part in bloc.split("|"):
            part = part.strip()
            # `l1=`, `selfref=` … sont des paramètres du modèle, pas des cibles.
            if not part or "=" in part or "{" in part:
                continue
            part = part.split("#")[0].strip()
            if part and part not in vus:
                vus.add(part); out.append(part)
    return out


MOTIF_TITRE = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$", re.M)


def plan(titre: str) -> list[dict]:
    """Le plan de l'article en texte brut : niveau, titre, contenu.

    `prop=extracts&explaintext` rend l'article entier débarrassé du
    balisage, avec les titres sous la forme `== Titre ==`. Un seul appel
    donne la structure ET le contenu ; passer par `prop=sections` puis un
    appel par section coûterait dix fois plus cher pour le même résultat.
    """
    d = _appel({"action": "query", "titles": titre, "prop": "extracts",
                "explaintext": 1, "redirects": 1})
    pages = d.get("query", {}).get("pages", [])
    if not pages or "extract" not in pages[0]:
        return []
    texte = pages[0]["extract"]

    marques = [(m.start(), m.end(), len(m.group(1)) - 1, m.group(2)) for m in MOTIF_TITRE.finditer(texte)]
    out = []
    # Le résumé de tête n'a pas de titre : il devient la première section.
    tete = texte[: marques[0][0]].strip() if marques else texte.strip()
    if tete:
        out.append({"niveau": 1, "titre": "Overview", "contenu": tete})
    for i, (_, fin, niveau, nom) in enumerate(marques):
        debut_suivant = marques[i + 1][0] if i + 1 < len(marques) else len(texte)
        out.append({"niveau": niveau, "titre": nom,
                    "contenu": texte[fin:debut_suivant].strip()})
    return out


def elague(sections: list[dict]) -> tuple[list[dict], list[tuple[str, str]]]:
    """Retire l'appareil et l'outil, à tous les niveaux, parents compris."""
    gardees, ecartees = [], []
    niveau_coupe = None
    for s in sections:
        # On est sous un parent écarté tant qu'on ne remonte pas.
        if niveau_coupe is not None:
            if s["niveau"] > niveau_coupe:
                ecartees.append((s["titre"], "sous un parent écarté")); continue
            niveau_coupe = None
        raison = titre_ecarte(s["titre"])
        if raison:
            ecartees.append((s["titre"], raison)); niveau_coupe = s["niveau"]; continue
        gardees.append(s)

    # Un nœud dont tous les enfants sont tombés et qui n'a pas de contenu
    # propre n'est plus qu'un titre creux : il tombe à son tour.
    change = True
    while change:
        change = False
        for i, s in enumerate(gardees):
            a_enfant = i + 1 < len(gardees) and gardees[i + 1]["niveau"] > s["niveau"]
            if not a_enfant and not s["contenu"].strip():
                ecartees.append((s["titre"], "titre creux")); gardees.pop(i)
                change = True; break
    return gardees, ecartees


# ---------------------------------------------------------------------
# Étape « arbre » — construire `chapter`
# ---------------------------------------------------------------------

def slug_libre(conn: sqlite3.Connection, base: str) -> str:
    s, n = base, 2
    while conn.execute("SELECT 1 FROM chapter WHERE slug = ?", (s,)).fetchone():
        s, n = f"{base}-{n}", n + 1
    return s


def semer_arbre(conn, theme, profondeur, plafond, blanc, bavard,
                greffe: str | None = None) -> tuple[int, int]:
    """Sème l'arbre d'un thème depuis sa graine.

    Avec `greffe`, part d'un autre article et l'accroche en branche de
    niveau 1 sous la racine déjà posée. C'est le seul moyen de donner
    plusieurs points de départ à un thème : `theme.seed_url` n'en tient
    qu'un, et `ux_chapter_root` interdit deux racines. « Terrestrial
    animal » n'a que quatre voisins — des limaces ; ses vrais enfants
    sont Mammal, Insect, Reptile, qui viennent en greffe.
    """
    poses = ecartes = 0
    # Le déjà-vu est PROPRE AU THÈME depuis la 021 : un article pris par
    # un autre thème reste disponible pour celui-ci. « Tide » appartient
    # à la Lune comme à la Terre.
    vus: set[str] = {r[0] for r in conn.execute(
        "SELECT source_url FROM chapter"
        " WHERE theme_id = ? AND source_url IS NOT NULL", (theme["id"],))}

    demande = greffe or theme["seed_url"].rsplit("/", 1)[-1].replace("_", " ")
    graine = page(demande)
    if graine is None:
        print(f"  {theme['title']} : « {demande} » introuvable — ignoré")
        return 0, 0

    def pose(p, parent_id, depth, position, relies):
        nonlocal poses
        if blanc:
            poses += 1
            print(f"    {'  ' * depth}+ {p['titre']}")
            return None
        meta = json.dumps({"wikipedia": p["url"], "pageid": p["pageid"],
                           "revision": p["revision"], "related": relies,
                           "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                          ensure_ascii=False)
        cur = conn.execute(
            "INSERT INTO chapter (theme_id, parent_id, depth, position, slug, title,"
            " source_url, meta, status) VALUES (?,?,?,?,?,?,?,?,'draft')",
            (theme["id"], parent_id, depth, position,
             slug_libre(conn, slugifie(p["titre"])), p["titre"], p["url"], meta))
        poses += 1
        return cur.lastrowid

    # Où accrocher la graine, et à quelle profondeur elle commence.
    parent, depart, rang = None, 0, 0
    if greffe is not None:
        r = conn.execute(
            "SELECT id FROM chapter WHERE theme_id = ? AND parent_id IS NULL",
            (theme["id"],)).fetchone()
        if r is None:
            print(f"  {theme['title']} : pas de racine — semer l'arbre avant de greffer")
            return 0, 0
        if graine["url"] in vus:
            print(f"  {graine['titre']} : déjà dans ce thème — greffe ignorée")
            return 0, 0
        parent, depart = r["id"], 1
        rang = conn.execute("SELECT COUNT(*) FROM chapter WHERE parent_id = ?",
                            (parent,)).fetchone()[0]

    enfants_graine = sous_sujets(graine["titre"])
    racine = pose(graine, parent, depart, rang, enfants_graine)
    vus.add(graine["url"])

    # Le titre du parent voyage avec : le juge en a besoin pour
    # décider en contexte. « Buoyancy » sous « Flight » se garde ;
    # le même mot sous « Shipbuilding » ne se garderait pas.
    frontiere = [(racine, graine['titre'], depart, enfants_graine)]
    while frontiere:
        parent_id, parent_titre, depth, cibles = frontiere.pop(0)
        if depth >= profondeur:
            continue
        for position, cible in enumerate(cibles):
            if poses >= plafond:
                print(f"    plafond de {plafond} atteint — on s'arrête là")
                return poses, ecartes
            raison = chapitre_ecarte(cible)
            if raison:
                ecartes += 1
                continue
            p = page(cible)
            if p is None:
                ecartes += 1
                continue
            if p["url"] in vus:          # la règle du déjà-vu : doublons et cycles
                ecartes += 1
                continue
            raison = chapitre_ecarte(p["titre"])   # le titre canonique peut différer
            if raison:
                ecartes += 1
                continue
            # Le juge en dernier : c'est le seul filtre qui coûte un appel,
            # inutile de le payer pour ce que les listes écartent déjà.
            garder, pourquoi = juge(p["titre"], theme["title"], parent_titre)
            if not garder:
                ecartes += 1
                if bavard:
                    print(f"    {'  ' * (depth + 1)}✗ {p['titre']}  — {pourquoi}")
                continue
            vus.add(p["url"])
            petits = sous_sujets(p["titre"]) if depth + 1 < profondeur else []
            nid = pose(p, parent_id, depth + 1, position, petits)
            if petits:
                frontiere.append((nid, p['titre'], depth + 1, petits))
        if not blanc:
            conn.commit()
    return poses, ecartes


# ---------------------------------------------------------------------
# Étape « sections » — remplir `exercise_prompt`
# ---------------------------------------------------------------------

# Combien de questions une section peut porter. Dix partout n'a aucun
# sens : « Mutual planetary transits » fait 167 caractères, « Lava flows »
# en fait 4 692. Sous le seuil, la section entre quand même — elle
# documente le plan de l'article — mais elle ne produit rien.
SEUIL = 400          # en dessous, pas assez de matière pour une question
PAR_QUESTION = 300   # caractères de source par question demandée


def combien(contenu: str | None) -> int:
    n = len(contenu or "")
    if n < SEUIL:
        return 0
    return min(10, max(3, n // PAR_QUESTION))


def semer_sections(conn, chapitre, blanc) -> tuple[int, int]:
    sections = plan(chapitre["title"])
    if not sections:
        return 0, 0
    gardees, ecartees = elague(sections)

    def a_des_enfants(i: int) -> bool:
        return i + 1 < len(gardees) and gardees[i + 1]["niveau"] > gardees[i]["niveau"]

    if blanc:
        for i, s in enumerate(gardees):
            n = combien(s["contenu"])
            marque = f"  ({len(s['contenu'])} car. → {n} question(s))" if s["contenu"] else ""
            print(f"    {'  ' * (s['niveau'] - 1)}{s['titre']}{marque}")
        return len(gardees), len(ecartees)

    pile: dict[int, int] = {}
    for i, s in enumerate(gardees):
        position = i + 1
        a_enfant = a_des_enfants(i)
        parent = pile.get(s["niveau"] - 1)
        cur = conn.execute(
            "INSERT INTO exercise_prompt (chapter_id, parent_id, depth, position,"
            " title, content, requested_count, status) VALUES (?,?,?,?,?,?,?,'pending')",
            # Une section qui a des sous-sections porte quand même son
            # propre paragraphe d'introduction quand elle en a un : sur
            # « Rainbow », « Explanation » ouvre par un vrai texte avant
            # de se diviser, et la jeter perdait l'essentiel du sujet.
            (chapitre["id"], parent, s["niveau"] - 1, position, s["titre"],
             s["contenu"].strip() or None, combien(s["contenu"])))
        pile[s["niveau"]] = cur.lastrowid
        for k in [k for k in pile if k > s["niveau"]]:
            del pile[k]
    conn.commit()
    return len(gardees), len(ecartees)


# ---------------------------------------------------------------------

def etat(conn) -> None:
    print(f"{'thème':20} {'chapitres':>10} {'profondeur':>11} {'sections':>10} {'exercices':>10}")
    print('-' * 66)
    for t in conn.execute("SELECT id, title FROM theme ORDER BY position"):
        n = conn.execute("SELECT COUNT(*) FROM chapter WHERE theme_id = ?", (t[0],)).fetchone()[0]
        d = conn.execute("SELECT COALESCE(MAX(depth), 0) FROM chapter WHERE theme_id = ?", (t[0],)).fetchone()[0]
        s = conn.execute("SELECT COUNT(*) FROM exercise_prompt p JOIN chapter c ON c.id = p.chapter_id"
                         " WHERE c.theme_id = ?", (t[0],)).fetchone()[0]
        e = conn.execute("SELECT COUNT(*) FROM exercise e JOIN chapter c ON c.id = e.chapter_id"
                         " WHERE c.theme_id = ?", (t[0],)).fetchone()[0]
        print(f"{t[1]:20} {n:>10} {d:>11} {s:>10} {e:>10}")
    print('-' * 66)
    print(f"{'TOTAL':20} "
          f"{conn.execute('SELECT COUNT(*) FROM chapter').fetchone()[0]:>10} "
          f"{'':>11} "
          f"{conn.execute('SELECT COUNT(*) FROM exercise_prompt').fetchone()[0]:>10} "
          f"{conn.execute('SELECT COUNT(*) FROM exercise').fetchone()[0]:>10}")


def voir(conn, slug: str | None) -> None:
    """L'arbre, avec les identifiants — c'est par eux qu'on coupe."""
    where, params = ("", ()) if not slug else (" WHERE slug = ?", (slug,))
    for t in conn.execute(f"SELECT * FROM theme{where} ORDER BY position", params):
        n = conn.execute("SELECT COUNT(*) FROM chapter WHERE theme_id = ?", (t["id"],)).fetchone()[0]
        print(f"\n■ {t['title']}  ({n} chapitres)")

        def branche(pid, ind):
            for r in conn.execute(
                    "SELECT id, title FROM chapter WHERE theme_id = ? AND parent_id IS ?"
                    " ORDER BY position, id", (t["id"], pid)):
                fils = conn.execute(
                    "WITH RECURSIVE sous(id) AS (SELECT ? UNION ALL"
                    " SELECT c.id FROM chapter c JOIN sous s ON c.parent_id = s.id)"
                    " SELECT COUNT(*) - 1 FROM sous", (r["id"],)).fetchone()[0]
                suite = f"  ({fils} dessous)" if fils else ""
                print(f"  {r['id']:>5}  {'  ' * ind}{r['title']}{suite}")
                branche(r["id"], ind + 1)

        branche(None, 0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True,
                    choices=("status", "arbre", "sections", "voir", "couper"))
    ap.add_argument("--theme", help="slug d'un thème ; tous par défaut")
    ap.add_argument("--depth", type=int, default=4, help="profondeur maximale (défaut 4)")
    ap.add_argument("--cap", type=int, default=400, help="plafond de chapitres par thème")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true",
                    help="montre ce que le juge écarte, et pourquoi")
    ap.add_argument("--force", action="store_true",
                    help="refait un thème déjà semé, en effaçant son arbre d'abord")
    ap.add_argument("--ids", help="pour --step couper : les chapitres à retirer, séparés par des virgules")
    ap.add_argument("--graft", help="pour --step arbre : articles à greffer en branches de "
                                    "niveau 1 sous la racine du thème, séparés par des virgules")
    args = ap.parse_args()

    conn = sqlite3.connect(DB, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")

    if args.step == "status":
        etat(conn); return

    if args.step == "voir":
        voir(conn, args.theme); return

    if args.step == "couper":
        if not args.ids:
            raise SystemExit("--step couper attend --ids 12,34,56")
        ids = [int(x) for x in args.ids.replace(" ", "").split(",") if x]
        for cid in ids:
            r = conn.execute("SELECT title FROM chapter WHERE id = ?", (cid,)).fetchone()
            if r is None:
                print(f"  {cid} : inconnu"); continue
            # Compte AVANT, la cascade emporte tout d'un coup.
            n = conn.execute(
                "WITH RECURSIVE sous(id) AS ("
                "  SELECT ? UNION ALL"
                "  SELECT c.id FROM chapter c JOIN sous s ON c.parent_id = s.id)"
                " SELECT COUNT(*) FROM sous", (cid,)).fetchone()[0]
            conn.execute("DELETE FROM chapter WHERE id = ?", (cid,))
            print(f"  {cid} {r['title']} — {n} chapitre(s) retirés avec sa descendance")
        conn.commit(); return

    where, params = "", ()
    if args.theme:
        where, params = " WHERE slug = ?", (args.theme,)

    if args.step == "arbre" and args.graft:
        if not args.theme:
            raise SystemExit("--graft attend --theme : on greffe sur un arbre, pas sur tous")
        t = conn.execute("SELECT * FROM theme WHERE slug = ?", (args.theme,)).fetchone()
        if t is None:
            raise SystemExit(f"thème « {args.theme} » inconnu")
        total_p = total_e = 0
        for article in [a.strip() for a in args.graft.split(",") if a.strip()]:
            print(f"\n■ {t['title']} ← greffe {article}")
            p, e = semer_arbre(conn, t, args.depth, args.cap, args.dry_run,
                               args.verbose, greffe=article)
            print(f"    {p} chapitre(s) · {e} écarté(s)")
            total_p += p; total_e += e
        print(f"\n{total_p} chapitre(s) {'à greffer' if args.dry_run else 'greffés'} "
              f"· {total_e} écarté(s)")
        conn.close(); return

    if args.step == "arbre":
        total_p = total_e = 0
        for t in conn.execute(f"SELECT * FROM theme{where} ORDER BY position", params):
            if conn.execute("SELECT 1 FROM chapter WHERE theme_id = ?", (t["id"],)).fetchone():
                if not args.force:
                    print(f"\n■ {t['title']} — déjà semé, ignoré (--force pour refaire)")
                    continue
                n = conn.execute("DELETE FROM chapter WHERE theme_id = ?", (t["id"],)).rowcount
                conn.commit()
                print(f"\n■ {t['title']} — {n} chapitre(s) effacés, on refait")
            print(f"\n■ {t['title']}  ({t['seed_url']})")
            p, e = semer_arbre(conn, t, args.depth, args.cap, args.dry_run, args.verbose)
            print(f"    {p} chapitre(s) · {e} écarté(s)")
            total_p += p; total_e += e
        print(f"\n{total_p} chapitre(s) {'à poser' if args.dry_run else 'posés'} · {total_e} écarté(s)")

    if args.step == "sections":
        sql = ("SELECT c.* FROM chapter c JOIN theme t ON t.id = c.theme_id"
               " WHERE NOT EXISTS (SELECT 1 FROM exercise_prompt p WHERE p.chapter_id = c.id)")
        if args.theme:
            sql += " AND t.slug = ?"
        sql += " ORDER BY c.theme_id, c.depth, c.position"
        chapitres = list(conn.execute(sql, params if args.theme else ()))
        total_g = total_e = 0
        for c in chapitres:
            g, e = semer_sections(conn, c, args.dry_run)
            total_g += g; total_e += e
            print(f"  {c['title'][:44]:46} {g:>3} section(s) · {e:>3} écartée(s)")
        print(f"\n{len(chapitres)} chapitre(s) · {total_g} section(s) "
              f"{'à poser' if args.dry_run else 'posées'} · {total_e} écartée(s)")

    conn.close()


if __name__ == "__main__":
    main()
