"""Le premier appel du pipeline : d'un sujet, tirer une présentation.

L'utilisateur écrit « les fonctions PHP ». Le modèle en rend un titre,
une description, une catégorie, un programme de trois à cinq chapitres
et des mots-clés.

Deux partis pris qui traversent tout ce fichier :

  · LA CATÉGORIE EST RECONNUE AVANT D'ÊTRE CRÉÉE. Le modèle reçoit les
    catégories existantes et doit dire si l'une convient. Il ne crée que
    si vraiment rien ne va. Sans cette étape, « Programmation »,
    « Développement » et « Code » cohabiteraient au bout d'un mois sans
    que personne ne l'ait décidé — et une taxonomie qui se dédouble ne
    se recolle pas après coup.

  · ON EST TOLÉRANT SUR LA FORME, INTRANSIGEANT SUR LE FOND. Le modèle
    encadre sa réponse, ajoute un commentaire, met un accent dans une
    clé. On récupère. Mais un programme à un seul chapitre, un titre
    vide ou une catégorie inventée alors qu'une existante convenait,
    non : ça n'entre pas en base.

Le transport est dans `llm.ask`. Ici, le texte de la demande et la
lecture de la réponse — rien d'autre.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .llm import GenerationError, extract_json_object

# Bornes du programme. En dessous de trois chapitres ce n'est pas un
# programme, c'est un titre redit ; au-delà de cinq, l'utilisateur ne
# relit plus et valide en bloc — ce qui vide la validation de son sens.
MIN_CHAPTERS = 3
MAX_CHAPTERS = 5

# Reprises des contraintes SQL : les dépasser ferait sauter l'insertion.
LIMITS = {
    "title": 255,
    "description": 2000,
    "category_label": 120,
    "chapter_title": 255,
    "chapter_description": 2000,
    "tag": 60,
}

MAX_TAGS = 6


TEMPLATE = """Tu prépares une fiche d'apprentissage à partir d'un sujet donné.

SUJET : {{subject}}

CATÉGORIES EXISTANTES (choisis-en une si elle convient) :
{{categories}}

Rends UNIQUEMENT un objet JSON, sans texte autour, de cette forme :

{
  "title": "titre court et clair de la connaissance",
  "description": "deux ou trois phrases : ce qu'on apprend, et pour qui",
  "category_id": 11,
  "category_label": null,
  "tags": ["mot-clé", "mot-clé"],
  "chapters": [
    {"title": "titre du chapitre", "description": "ce qu'il couvre, en une phrase"}
  ]
}

RÈGLES :
- Écris en {{langue}}.
- "category_id" : l'identifiant d'une catégorie ci-dessus si l'une
  convient, même approximativement. Mets null SEULEMENT si aucune ne
  peut raisonnablement accueillir ce sujet.
- "category_label" : à remplir UNIQUEMENT si category_id est null.
  Donne alors un nom large et durable, qui pourra accueillir d'autres
  sujets voisins — « Programmation » plutôt que « Fonctions PHP ».
- "chapters" : entre {{min}} et {{max}} chapitres, dans l'ordre où on
  les apprend. Chacun doit pouvoir donner lieu à des exercices : un
  chapitre est une chose qu'on sait faire, pas une intention.
- "tags" : au plus {{max_tags}}, en minuscules.
- Pas de commentaire, pas de bloc de code, rien après l'objet JSON.
"""

LANGUES = {"fr": "français", "en": "anglais"}


def build_prompt(subject: str, categories: list[dict], lang: str = "fr") -> str:
    """Le texte exact envoyé au modèle.

    Les catégories sont listées avec leur identifiant : c'est ce qui
    permet au modèle d'en désigner une plutôt que d'en réécrire le nom,
    et donc d'éviter qu'« Orthographe » revienne sous une graphie
    voisine à chaque appel.
    """
    listing = (
        "\n".join(f"  {c['id']} — {c['label']}" for c in categories)
        or "  (aucune pour l'instant)"
    )
    out = TEMPLATE
    for key, value in {
        "subject": subject,
        "categories": listing,
        "langue": LANGUES.get(lang, "français"),
        "min": MIN_CHAPTERS,
        "max": MAX_CHAPTERS,
        "max_tags": MAX_TAGS,
    }.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out


def _clean(value: Any, field: str) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if not text:
        return None
    limit = LIMITS.get(field)
    if limit and len(text) > limit:
        cut = text[:limit]
        pivot = cut.rfind(". ")
        text = (cut[: pivot + 1] if pivot > limit * 0.6 else cut).strip()
    return text or None


def fold(text: str) -> str:
    """Minuscules, sans accent, sans ponctuation — pour comparer des noms."""
    stripped = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in stripped if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", stripped.casefold()).strip()


def match_existing(label: str, categories: list[dict]) -> int | None:
    """Une catégorie existante porte-t-elle déjà ce nom ?

    Dernier filet quand le modèle a renvoyé `category_label` alors qu'une
    catégorie convenait. Il arrive qu'il propose « Grammaire » sans voir
    celle qui existe déjà — et une catégorie créée en double ne se
    fusionne pas sans toucher aux thèmes qui y pendent.
    """
    target = fold(label)
    if not target:
        return None
    for c in categories:
        for name in (c.get("label"), c.get("label_en"), c.get("slug")):
            if name and fold(str(name)) == target:
                return int(c["id"])
    return None


def parse(raw: str, categories: list[dict]) -> dict:
    """Lit la réponse du modèle et rend une proposition sûre à écrire.

    Lève `GenerationError` sur tout ce qui ne peut pas devenir une
    connaissance : c'est le seul endroit où ce jugement est porté, et il
    vaut mieux un échec net qu'un thème vide en base.
    """
    data = extract_json_object(raw)

    title = _clean(data.get("title"), "title")
    if not title:
        raise GenerationError("Le modèle n'a pas donné de titre.")

    chapters: list[dict] = []
    seen: set[str] = set()
    for item in data.get("chapters") or []:
        if not isinstance(item, dict):
            continue
        ch_title = _clean(item.get("title"), "chapter_title")
        if not ch_title:
            continue
        # Deux chapitres au même nom, c'est un programme qui tourne en
        # rond — et deux lignes en conflit sur UNIQUE (theme_id, position)
        # n'auraient de toute façon aucun sens à relire.
        key = fold(ch_title)
        if key in seen:
            continue
        seen.add(key)
        chapters.append(
            {
                "title": ch_title,
                "description": _clean(item.get("description"), "chapter_description"),
            }
        )
        if len(chapters) == MAX_CHAPTERS:
            break

    if len(chapters) < MIN_CHAPTERS:
        raise GenerationError(
            f"Programme trop court : {len(chapters)} chapitre(s) exploitable(s), "
            f"il en faut au moins {MIN_CHAPTERS}."
        )

    # La catégorie : on retient l'identifiant s'il désigne une catégorie
    # réellement servie. Un identifiant inventé vaut absence de réponse.
    known = {int(c["id"]) for c in categories}
    raw_id = data.get("category_id")
    category_id = int(raw_id) if isinstance(raw_id, int) and raw_id in known else None

    category_label = None
    if category_id is None:
        category_label = _clean(data.get("category_label"), "category_label")
        if category_label:
            # Le modèle a proposé un nom : si une catégorie le porte déjà,
            # on la reprend plutôt que d'en créer une jumelle.
            hit = match_existing(category_label, categories)
            if hit is not None:
                category_id, category_label = hit, None

    tags: list[str] = []
    for tag in data.get("tags") or []:
        cleaned = _clean(tag, "tag")
        if cleaned and fold(cleaned) not in {fold(t) for t in tags}:
            tags.append(cleaned.casefold())
        if len(tags) == MAX_TAGS:
            break

    return {
        "title": title,
        "description": _clean(data.get("description"), "description"),
        "category_id": category_id,
        "category_label": category_label,
        "tags": tags,
        "chapters": chapters,
    }
