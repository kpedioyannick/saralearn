#!/usr/bin/env python3
"""Sème les 36 thèmes et 196 chapitres des six catégories de la création.

Les catégories sont entrées par la migration 014. Ce script pose ce
qu'elles contiennent : un programme FIXE, relu et validé avant d'être
écrit ici. Il ne demande rien à un modèle — ni `outline.py`, ni
`chapters.py`, ni DeepSeek. Le programme est une donnée de ce fichier.

POURQUOI PAS `outline.py`. Le chemin normal fait inventer le programme
par le modèle à partir d'un sujet tapé. Sa consigne dit qu'« un chapitre
est une chose qu'on sait faire » — de la pédagogie par compétence,
écrite pour conjuguer un verbe. Appliquée à « Mammals », elle rend
« Identifier un mammifère » là où l'on veut « Records and extremes ».
Et rien n'y interdit les objets fabriqués : on lui parle d'étoiles, il
propose des télescopes. Le programme a donc été écrit à la main.

LA RÈGLE DU TRI, pour qui ajoutera des chapitres plus tard :

  · Seulement l'œuvre, jamais l'outil. Un chapitre ne porte que sur une
    chose créée et sur la manière dont elle fonctionne. Tout ce que
    l'homme fabrique, mesure ou nomme pour son usage en est écarté — ni
    ampoule, ni télescope, ni fuseau horaire, ni vaccin.
  · Le fonctionnement avant le record. « How a bird flies » plutôt que
    « quel oiseau vole le plus vite ». Les records restent, mais
    rassemblés dans leur propre chapitre, un par thème au plus : ils
    émerveillent une fois, ils n'apprennent rien deux fois.

REPRENABLE, comme `import_tech.py`. On relance autant de fois qu'on
veut : un thème dont le slug existe déjà n'est pas recréé, un chapitre
déjà posé à sa position n'est pas redoublé. Rien n'est jamais réécrit.

LES THÈMES NAISSENT `private` ET SANS COURS. `source_markdown` reste
vide : ces exercices ne seront pas tirés d'un cours, ils sont écrits
directement. La mise en ligne est un geste séparé — `--step publier` —
et elle refuse un thème sans exercice, comme `publier_tech.py`.

    python3 scripts/semer_creation.py --step status
    python3 scripts/semer_creation.py --step themes --dry-run
    python3 scripts/semer_creation.py --step all
    python3 scripts/semer_creation.py --step publier
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "sara.db"

LANG = "en"


# =====================================================================
# Le programme
#
# (slug, titre, description, [chapitres])
# =====================================================================

PROGRAMME: dict[str, list[tuple[str, str, str, list[str]]]] = {

    # ---------------------------------------------------------------
    "light-and-darkness": [
        ("light-and-its-colours", "Light and Its Colours",
         "What light is made of, how fast it travels, and why the sky and the"
         " sunset are not the same colour.",
         ["What light is",
          "The speed of light",
          "The colours hidden in white light",
          "The rainbow",
          "Why the sky is blue and the sunset red",
          "The light the eye cannot see"]),

        ("shadow-and-darkness", "Shadow and Darkness",
         "How shadows form, why day gives way to night, and whether true"
         " darkness exists at all.",
         ["How a shadow is formed",
          "Day and night",
          "How day length changes through the year",
          "Dusk and dawn",
          "Does complete darkness exist?"]),

        ("creatures-of-the-night", "Creatures of the Night",
         "The animals that live when the light goes, and the senses they use"
         " in place of sight.",
         ["Seeing in the dark",
          "Eyes that shine back",
          "Hearing and smelling instead of seeing",
          "How animals sleep",
          "Flowers that open at night"]),

        ("living-light", "Living Light",
         "Creatures that make their own light, from the firefly in a hedge to"
         " the lamps of the deep sea.",
         ["Bioluminescence",
          "Fireflies and glow-worms",
          "Lights of the deep sea",
          "Glowing fungi",
          "Glowing plankton"]),

        ("the-light-that-feeds", "The Light That Feeds",
         "How living things turn light into food, follow it, and measure the"
         " year by it.",
         ["Photosynthesis",
          "Plants that follow the sun",
          "Light and the seasons of living things",
          "Light and the human body",
          "Life without light"]),
    ],

    # ---------------------------------------------------------------
    "the-sky": [
        ("air-and-the-atmosphere", "Air and the Atmosphere",
         "What we breathe, how it is layered above us, and where the sky"
         " finally ends.",
         ["What air is made of",
          "The layers of the atmosphere",
          "Air pressure",
          "The ozone layer",
          "Air and life"]),

        ("clouds", "Clouds",
         "How a cloud is born, why it does not fall, and how to read the ones"
         " that warn of a storm.",
         ["How a cloud forms",
          "Why clouds stay up",
          "Telling the main cloud types apart",
          "Fog and dew",
          "Clouds that warn of a storm"]),

        ("water-falling-from-the-sky", "Water Falling from the Sky",
         "The journey water makes from sea to cloud to ground, and the many"
         " shapes it takes on the way down.",
         ["The water cycle",
          "Rain",
          "The snowflake",
          "Hail, frost and black ice",
          "Records of rain and snow"]),

        ("wind-and-storms", "Wind and Storms",
         "Why air moves, the great winds that circle the Earth, and the"
         " storms that carve the land.",
         ["Where wind comes from",
          "The great winds of the Earth",
          "Hurricanes, typhoons and cyclones",
          "The tornado",
          "Wind that shapes the land"]),

        ("fires-of-the-sky", "Fires of the Sky",
         "Lightning, auroras and shooting stars — the sky when it stops being"
         " quiet.",
         ["Lightning and thunder",
          "The polar auroras",
          "Mirages and halos",
          "Shooting stars",
          "The sky changing colour"]),
    ],

    # ---------------------------------------------------------------
    "earth-sea-and-vegetation": [
        ("the-earth-beneath-our-feet", "The Earth Beneath Our Feet",
         "What lies under the ground, why it shakes and opens, and what the"
         " rock remembers.",
         ["The layers of the Earth",
          "Continents that move",
          "Volcanoes",
          "Earthquakes",
          "Rocks and minerals",
          "Caves and their formations"]),

        ("mountains-deserts-and-ice", "Mountains, Deserts and Ice",
         "How the great landscapes are raised, worn down and frozen.",
         ["How mountains are born",
          "Records of altitude",
          "Hot deserts and cold deserts",
          "Glaciers and sea ice",
          "Soil and erosion",
          "Islands"]),

        ("fresh-water", "Fresh Water",
         "Springs, rivers, lakes and marshes — the small share of the world's"
         " water that living things can drink.",
         ["Springs and groundwater",
          "The great rivers",
          "Lakes and inland seas",
          "Waterfalls",
          "Marshes and mangroves"]),

        ("the-oceans", "The Oceans",
         "Why the sea is salt, what moves it, and what lives at depths no"
         " light reaches.",
         ["The oceans and their seas",
          "The salt of the sea",
          "The depths and the trenches",
          "Tides",
          "Ocean currents",
          "Coral reefs"]),

        ("trees-and-forests", "Trees and Forests",
         "How a tree feeds and grows, why leaves fall, and the records held by"
         " the largest living things.",
         ["How a tree grows",
          "Sap and roots",
          "Broadleaves and conifers",
          "Records of the plant world",
          "Seasons and falling leaves",
          "The tropical forest"]),

        ("flowers-fruit-and-seeds", "Flowers, Fruit and Seeds",
         "How plants make the next generation, and the ways they get their"
         " seeds carried far from home.",
         ["From flower to fruit",
          "Pollinators",
          "Seeds and their journeys",
          "How a seed germinates",
          "Plants that defend themselves",
          "Carnivorous plants"]),

        ("the-quiet-ones-of-the-soil", "The Quiet Ones of the Soil",
         "Mosses, ferns, fungi and algae — the living things that came before"
         " flowers and still cover the ground.",
         ["Mosses and lichens",
          "Ferns",
          "Fungi",
          "Life in the soil",
          "Algae"]),
    ],

    # ---------------------------------------------------------------
    "sun-moon-and-stars": [
        ("the-sun", "The Sun",
         "The star we live beside: its light, its heat, and the year it rules.",
         ["What the Sun is",
          "Its light and its heat",
          "The seasons",
          "Solar eclipses",
          "Sunspots and solar flares"]),

        ("the-moon", "The Moon",
         "Why it changes shape, why one side is never seen, and how it pulls"
         " the sea.",
         ["The phases of the Moon",
          "The far side",
          "The Moon and the tides",
          "Lunar eclipses",
          "The surface of the Moon"]),

        ("the-solar-system", "The Solar System",
         "The eight planets and everything smaller that travels with them.",
         ["The eight planets",
          "The rocky planets",
          "The gas giants",
          "The moons of the solar system",
          "Asteroids, comets and meteorites"]),

        ("the-stars", "The Stars",
         "What a star is made of, how it lives and dies, and how the sky was"
         " read before maps.",
         ["What a star is",
          "The life and death of a star",
          "Constellations",
          "The colours of stars",
          "The pole star and finding your way"]),

        ("the-universe", "The Universe",
         "Our galaxy and the ones beyond it, and why looking far away means"
         " looking into the past.",
         ["The Milky Way",
          "Galaxies",
          "The distances of the universe",
          "Light from the past",
          "What the night sky shows"]),
    ],

    # ---------------------------------------------------------------
    "animals": [
        ("mammals", "Mammals",
         "Warm blood, milk and fur — from the smallest shrew to the largest"
         " animal that has ever lived.",
         ["What makes a mammal",
          "The great predators",
          "Herbivores and their digestion",
          "Young and family life",
          "Marine mammals",
          "Records and extremes"]),

        ("birds", "Birds",
         "How a wing carries a body through air, and what feathers, beaks and"
         " songs are for.",
         ["How a bird flies",
          "Feathers and colours",
          "Beaks and food",
          "Nests and eggs",
          "Migration",
          "Songs and calls",
          "Birds that cannot fly"]),

        ("fish-and-sea-life", "Fish and Sea Life",
         "Breathing water, hunting in the dark, and the strange bodies that"
         " the sea allows.",
         ["How a fish breathes",
          "Sharks",
          "Life in the deep",
          "Molluscs and crustaceans",
          "Jellyfish and coral",
          "Records of the ocean"]),

        ("reptiles-and-amphibians", "Reptiles and Amphibians",
         "Cold-blooded lives: scales and shells on one side, skin and water on"
         " the other.",
         ["Cold blood",
          "Snakes and their venom",
          "Lizards and chameleons",
          "Turtles and tortoises",
          "Crocodiles and alligators",
          "Frogs and salamanders"]),

        ("insects-and-spiders", "Insects and Spiders",
         "Six legs and eight, the most numerous animals of all, and the"
         " architects among them.",
         ["The anatomy of an insect",
          "Bees and the hive",
          "Ants and termites",
          "Butterflies and metamorphosis",
          "Spiders and their webs",
          "Camouflage and mimicry"]),

        ("how-animals-live", "How Animals Live",
         "Moving, hunting, sleeping and living together — what animals do"
         " whatever their shape.",
         ["Moving: walking, swimming, crawling",
          "Hunting and defending",
          "Animal senses",
          "Sleep and hibernation",
          "Living in groups",
          "Records of speed and long life"]),

        ("animals-that-are-gone", "Animals That Are Gone",
         "The creatures we know only from the rock they left behind.",
         ["The dinosaurs",
          "Fossils and what they tell",
          "Giants of prehistory",
          "Mammoths and the ice age",
          "Species that have disappeared"]),
    ],

    # ---------------------------------------------------------------
    "the-human-being": [
        ("the-body", "The Body",
         "The frame that holds us up and the organs it protects.",
         ["The skeleton",
          "The muscles",
          "The heart and the blood",
          "The lungs and breathing",
          "Skin, hair and nails",
          "The organs and what they do"]),

        ("the-senses", "The Senses",
         "Five ways the world gets in — and the ones nobody counts.",
         ["Sight",
          "Hearing",
          "Smell",
          "Taste",
          "Touch",
          "Balance and the senses we forget"]),

        ("eating-drinking-and-digesting", "Eating, Drinking and Digesting",
         "What happens to food after the last bite, and why the body asks for"
         " more.",
         ["The journey of food",
          "Teeth",
          "What the body takes from food",
          "Water in the body",
          "Hunger and thirst"]),

        ("the-brain-and-sleep", "The Brain and Sleep",
         "The organ that runs everything, and the third of life it spends"
         " switched inward.",
         ["What the brain does",
          "Memory",
          "Sleep and dreams",
          "Emotions",
          "Learning and concentrating"]),

        ("growing-and-ageing", "Growing and Ageing",
         "One cell to a person, and the whole road afterwards.",
         ["From cell to baby",
          "Birth",
          "Childhood and growth",
          "Adolescence",
          "Growing old",
          "Heredity and genes"]),

        ("the-bodys-defences", "The Body's Defences",
         "The unseen crowd around us, and everything the body does to hold its"
         " ground.",
         ["Microbes around us",
          "How the body defends itself",
          "Fever and pain",
          "Wounds that heal",
          "The body that repairs itself"]),

        ("the-body-in-motion", "The Body in Motion",
         "Walking, gripping, speaking, breathing hard — the body at work.",
         ["Walking and running",
          "The hand and its precision",
          "Voice and speech",
          "Breath and effort",
          "What the body can endure"]),
    ],
}


# =====================================================================
# Outils
# =====================================================================

def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def categories(conn: sqlite3.Connection) -> dict[str, sqlite3.Row]:
    """Les six catégories de la 014, par slug.

    On échoue tout de suite si l'une manque : semer des thèmes sous une
    catégorie absente donnerait une violation de clé étrangère au
    milieu du lot, avec la moitié du travail déjà écrite.
    """
    found = {
        c["slug"]: c
        for c in conn.execute(
            "SELECT id, slug, label_en, color FROM category WHERE slug IN"
            " ('light-and-darkness','the-sky','earth-sea-and-vegetation',"
            "  'sun-moon-and-stars','animals','the-human-being')")
    }
    missing = set(PROGRAMME) - set(found)
    if missing:
        raise SystemExit(
            f"catégories absentes : {', '.join(sorted(missing))}\n"
            "joue d'abord db/migrations/014_categories_de_la_creation.sql")
    return found


# =====================================================================
# Étapes
# =====================================================================

def step_themes(conn: sqlite3.Connection, dry: bool) -> None:
    cats = categories(conn)
    made = skipped = 0

    for cat_slug, themes in PROGRAMME.items():
        cat = cats[cat_slug]
        print(f"\n{cat['label_en']}")
        for slug, title, description, _chapters in themes:
            if conn.execute("SELECT 1 FROM theme WHERE slug = ?", (slug,)).fetchone():
                print(f"  · {title[:44]:46s} déjà là")
                skipped += 1
                continue
            print(f"  + {title[:44]:46s} {'(à créer)' if dry else 'créé'}")
            made += 1
            if dry:
                continue
            conn.execute(
                # `owner_id` reste NULL : ces thèmes viennent d'un semis,
                # pas d'un auteur. C'est ce que fait déjà `import_tech`,
                # et c'est pourquoi personne ne peut en demander la
                # relecture depuis l'écran — la publication est un geste
                # d'administrateur (voir `--step publier`).
                #
                # `source_markdown` reste NULL : il n'y a pas de cours.
                # Les exercices sont écrits, pas tirés d'un texte.
                "INSERT INTO theme (category_id, owner_id, slug, title,"
                " description, color, source_markdown, visibility, lang)"
                " VALUES (?, NULL, ?, ?, ?, ?, NULL, 'private', ?)",
                (cat["id"], slug, title, description, cat["color"], LANG))
    if not dry:
        conn.commit()
    print(f"\n{made} thème(s) {'à créer' if dry else 'créé(s)'}, {skipped} déjà en place")


def step_chapters(conn: sqlite3.Connection, dry: bool) -> None:
    made = skipped = 0

    for cat_slug, themes in PROGRAMME.items():
        for slug, title, _description, chapters in themes:
            theme = conn.execute("SELECT id, title FROM theme WHERE slug = ?",
                                 (slug,)).fetchone()
            if theme is None:
                print(f"  ! {title[:44]:46s} thème absent — joue --step themes")
                continue
            for position, chapter in enumerate(chapters, start=1):
                exists = conn.execute(
                    "SELECT 1 FROM chapter WHERE theme_id = ? AND position = ?",
                    (theme["id"], position)).fetchone()
                if exists:
                    skipped += 1
                    continue
                made += 1
                if dry:
                    continue
                conn.execute(
                    # `generated_prompt` et `type_question` restent NULL :
                    # ils appartiennent au chemin `chapters.py`, qui fait
                    # écrire le prompt d'un chapitre par un modèle. Ici
                    # les exercices sont rédigés directement, chapitre par
                    # chapitre, et entrés par `import_exercises.py`.
                    "INSERT INTO chapter (theme_id, position, title, status, model)"
                    " VALUES (?, ?, ?, 'draft', ?)",
                    (theme["id"], position, chapter, "programme semé"))
    if not dry:
        conn.commit()
    print(f"{made} chapitre(s) {'à créer' if dry else 'créé(s)'}, {skipped} déjà en place")


def step_publier(conn: sqlite3.Connection, dry: bool) -> None:
    """Met en ligne les thèmes qui ont de quoi être lus.

    Même garde-fou que `publier_tech.py` : un thème sans exercice validé
    n'est pas publié. Mettre en ligne une page vide est pire que de ne
    rien mettre.
    """
    done = held = 0
    for cat_slug, themes in PROGRAMME.items():
        for slug, title, _d, _c in themes:
            theme = conn.execute(
                "SELECT id, visibility,"
                " (SELECT COUNT(*) FROM exercise WHERE theme_id = theme.id"
                "   AND state = 'validated') AS n"
                " FROM theme WHERE slug = ?", (slug,)).fetchone()
            if theme is None:
                continue
            if theme["n"] == 0:
                held += 1
                continue
            if theme["visibility"] == "public":
                continue
            done += 1
            print(f"  + {title[:44]:46s} {theme['n']:3d} exercice(s)")
            if dry:
                continue
            conn.execute(
                "UPDATE theme SET visibility = 'public',"
                " published_at = datetime('now'), updated_at = datetime('now')"
                " WHERE id = ?", (theme["id"],))
    if not dry:
        conn.commit()
    print(f"\n{done} thème(s) {'à publier' if dry else 'publié(s)'},"
          f" {held} retenu(s) faute d'exercice")


def step_status(conn: sqlite3.Connection) -> None:
    cats = categories(conn)
    t_total = c_total = e_total = 0
    print(f"{'thème':48s} {'chap':>5s} {'exos':>6s}  visibilité")
    for cat_slug, themes in PROGRAMME.items():
        print(f"\n— {cats[cat_slug]['label_en']}")
        for slug, title, _d, chapters in themes:
            theme = conn.execute("SELECT id, visibility FROM theme WHERE slug = ?",
                                 (slug,)).fetchone()
            if theme is None:
                print(f"  {title[:46]:48s} {'—':>5s} {'—':>6s}  absent")
                continue
            t_total += 1
            nc = conn.execute("SELECT COUNT(*) FROM chapter WHERE theme_id = ?",
                              (theme["id"],)).fetchone()[0]
            ne = conn.execute("SELECT COUNT(*) FROM exercise WHERE theme_id = ?"
                              " AND state = 'validated'", (theme["id"],)).fetchone()[0]
            c_total += nc
            e_total += ne
            flag = "" if nc == len(chapters) else f" (sur {len(chapters)})"
            print(f"  {title[:46]:48s} {nc:5d}{flag} {ne:6d}  {theme['visibility']}")
    print(f"\n{t_total} thème(s) · {c_total} chapitre(s) · {e_total} exercice(s) validé(s)")
    attendu = sum(len(c) for ts in PROGRAMME.values() for *_, c in ts)
    print(f"programme complet : {sum(len(ts) for ts in PROGRAMME.values())} thèmes,"
          f" {attendu} chapitres")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True,
                    choices=("status", "themes", "chapters", "publier", "all"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not DB.exists():
        raise SystemExit(f"base introuvable : {DB}")

    conn = connect()
    try:
        if args.step == "status":
            step_status(conn)
        elif args.step == "themes":
            step_themes(conn, args.dry_run)
        elif args.step == "chapters":
            step_chapters(conn, args.dry_run)
        elif args.step == "publier":
            step_publier(conn, args.dry_run)
        else:
            step_themes(conn, args.dry_run)
            step_chapters(conn, args.dry_run)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
