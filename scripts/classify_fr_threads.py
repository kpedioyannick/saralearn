#!/usr/bin/env python3
"""Trie les notions de français : étude de la langue, ou pas.

Les espaces de la base source mélangent deux choses très différentes :

  · l'ÉTUDE DE LA LANGUE — grammaire, conjugaison, orthographe. Une
    notion, une règle, une réponse vérifiable. C'est ce qu'on garde.

  · la LECTURE et l'ÉCRITURE — « Identifier le narrateur », « Rédiger
    un petit récit », « Les figures de style ». Ce sont des compétences
    qui s'évaluent sur une production, pas des questions à quatre
    options. Un QCM les trahirait.

Le tri se fait par mots-clés sur le titre du fil, et l'exclusion prime :
dans le doute, on écarte. Mieux vaut perdre une notion que produire un
exercice qui ne veut rien dire.

    python3 scripts/classify_fr_threads.py            # montre le tri
    python3 scripts/classify_fr_threads.py --json     # sortie exploitable
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import unicodedata
from pathlib import Path

SOURCE = Path("/var/www/saralearn-anythingllm/server/storage/anythingllm.db")
# CM2 seul : reprendre les trois niveaux produisait le même titre
# plusieurs fois (« Le complément du nom » en CM1, CM2 et 6e), ce qui
# aurait servi trois exercices sur la même notion.
WORKSPACES = ("CM2 — Français",)
LEVEL = {"CM2 — Français": "CM2"}


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[’']", "'", text)


# Écarté d'emblée : lecture, littérature, expression écrite, oral.
# Ces compétences s'évaluent sur une production, pas sur un choix.
EXCLUDE = [
    r"\bcomprendre\b", r"\bidentifier le\b", r"\bidentifier les elements\b",
    r"\bnarrateur\b", r"\bpersonnage\b", r"\bauteur\b", r"\brecit\b",
    r"\bpoeme\b", r"\bpoesie\b", r"\bdialogue\b", r"\bportrait\b",
    r"\bredig", r"\becrire\b", r"\bresume", r"\bdecrire\b", r"\bsommaire\b",
    r"\blitterair", r"\bgenres?\b", r"\bregistres\b", r"\bfigures de style\b",
    r"\badaptations\b", r"\banalyse de l'image\b", r"\boeuvres\b",
    r"\bdocuments?\b", r"\btypes? de textes?\b", r"\bmemorisation\b",
    r"\breperer\b", r"\btrouver les points\b", r"\bimaginer\b",
    r"\bconnecteurs\b", r"\baventure\b", r"\bmonstres\b", r"\bmasquer\b",
    r"\benchanter\b", r"\brecreer\b", r"\bmots et merveilles\b",
    r"\bidees essentielles\b", r"\bordre des actions\b", r"\blettre ou un email\b",
    # La dictée est un format d'évaluation, pas une notion : ses
    # objectifs ne donneraient que des questions creuses.
    r"\bdictee\b",
]

# Conjugaison — un temps, un mode, une terminaison.
CONJUGAISON = [
    r"\bconjug", r"\bpresent\b", r"\bimparfait\b", r"\bfutur\b",
    r"\bpasse compose\b", r"\bpasse simple\b", r"\bpasse simple\b",
    r"\bplus-que-parfait\b", r"\bconditionnel\b", r"\bimperatif\b",
    r"\bmodes verbaux\b", r"\btemps composes\b", r"\bterminaisons des verbes\b",
    r"\btrois groupes de verbes\b", r"\bradical et terminaisons\b",
    r"\bvaleur des temps\b", r"\bpasse\b.*\bverbes\b",
]

# Orthographe — accord, homophone, graphie, son, ponctuation.
ORTHOGRAPHE = [
    r"\baccord", r"\bhomophone", r"\bhomonymes grammaticaux\b",
    r"\bpluriel\b", r"\bparticipe passe\b", r"\b-e ou -er\b", r"\be ou er\b",
    r"\bconsonnes? doubles?\b", r"\bdoubles consonnes\b",
    r"\blettres finales muettes\b", r"\bnoms terminés\b", r"\bnoms termines\b",
    r"\bmots commencant\b", r"\bmots en -eau\b", r"\bmots finissant\b",
    r"\ble son\b", r"\bponctuation\b", r"\bdictee\b",
    r"\bmots qui se ressemblent\b",
    r"\baccord du participe passe\b",
]

# Grammaire — nature, fonction, structure de la phrase.
GRAMMAIRE = [
    r"\badjectif\b", r"\battribut du sujet\b", r"\bepithete\b",
    r"\bfonction grammaticale\b", r"\bcomplement", r"\bgroupe nominal\b",
    r"\bgroupe sujet\b", r"\ble nom\b", r"\ble sujet\b", r"\ble verbe\b",
    r"\badverbes?\b", r"\bconjonctions\b", r"\bdeterminants\b",
    r"\bmots invariables\b", r"\bnatures et les fonctions\b",
    r"\bphrases?\b", r"\bpronoms?\b", r"\bprepositions\b",
    r"\bcod\b", r"\bcoi\b",
]

# Vocabulaire : présent dans la source, mais hors des trois
# sous-catégories demandées. On le signale plutôt que de le noyer.
VOCABULAIRE = [
    r"\bsynonymes?\b", r"\bantonymes?\b", r"\bhomonymes\b", r"\bpolysemie\b",
    r"\bchamp lexical\b", r"\bfamilles de mots\b", r"\bprefixes\b",
    r"\bsuffixes\b", r"\betymologie\b", r"\borigines latines\b",
    r"\bdictionnaire\b", r"\bsens d'un mot\b", r"\bformation.*mots\b",
]


def any_match(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def classify(title: str) -> str:
    t = fold(title)
    # L'exclusion prime : « Comprendre le sens d'un mot » contient
    # « mot » mais reste de la lecture.
    if any_match(EXCLUDE, t):
        return "écarté"
    if any_match(CONJUGAISON, t):
        return "Conjugaison"
    if any_match(ORTHOGRAPHE, t):
        return "Orthographe"
    if any_match(VOCABULAIRE, t):
        return "Vocabulaire"
    if any_match(GRAMMAIRE, t):
        return "Grammaire"
    return "écarté"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(f"file:{SOURCE}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT w.name AS espace, t.id AS thread_id, t.name AS titre,"
        "       COUNT(o.id) AS objectifs"
        " FROM workspace_threads t"
        " JOIN workspaces w ON w.id = t.workspace_id"
        " LEFT JOIN thread_objectives o ON o.threadId = t.id"
        f" WHERE w.name IN ({','.join('?' * len(WORKSPACES))})"
        " GROUP BY t.id HAVING objectifs > 0 ORDER BY t.name",
        WORKSPACES,
    ).fetchall()
    conn.close()

    # Un même titre revient parfois deux fois dans le même espace, avec
    # des nombres d'objectifs différents. On garde la version la plus
    # fournie : c'est celle qui a été travaillée.
    best: dict[str, sqlite3.Row] = {}
    for r in rows:
        key = fold(r["titre"])
        if key not in best or r["objectifs"] > best[key]["objectifs"]:
            best[key] = r
    rows = sorted(best.values(), key=lambda r: r["titre"])

    buckets: dict[str, list[dict]] = {}
    for r in rows:
        entry = {
            "thread_id": r["thread_id"],
            "titre": r["titre"],
            "niveau": LEVEL[r["espace"]],
            "objectifs": r["objectifs"],
        }
        buckets.setdefault(classify(r["titre"]), []).append(entry)

    if args.json:
        print(json.dumps(buckets, ensure_ascii=False, indent=1))
        return

    for name in ("Grammaire", "Conjugaison", "Orthographe", "Vocabulaire", "écarté"):
        items = buckets.get(name, [])
        total = sum(i["objectifs"] for i in items)
        print(f"\n=== {name} — {len(items)} notions, {total} objectifs ===")
        for i in sorted(items, key=lambda x: x["titre"])[:40]:
            print(f"  [{i['niveau']:3s}] {i['titre'][:66]}  ({i['objectifs']})")
        if len(items) > 40:
            print(f"  … et {len(items) - 40} autres")


if __name__ == "__main__":
    main()
