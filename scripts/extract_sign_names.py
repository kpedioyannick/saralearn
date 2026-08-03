#!/usr/bin/env python3
"""Tire le libellé d'un panneau de sa description Wikimedia.

Par règles, jamais par modèle de langue : ce libellé devient la BONNE
RÉPONSE d'un exercice. Une extraction ratée doit laisser le champ vide —
on préfère un panneau sans exercice à un exercice qui enseigne faux.

La description est de la prose :

    « Panneau A13a signalant la traversée d'enfants (France) - modèle… »
    « Panneau de limitation de vitesse à 50 km/h utilisé en France »

    →  Traversée d'enfants
    →  Limitation de vitesse à 50 km/h

    python3 scripts/extract_sign_names.py --dry-run
    python3 scripts/extract_sign_names.py
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "sara.db"
UA = "sara-exos/1.0 (https://learn.sara.education)"

# On coupe tout ce qui suit : c'est du contexte d'archive, pas du sens.
TAIL = re.compile(
    r"\s*(?:[-–—]\s*modèle.*|\(France\).*|utilisé en France.*|défini (?:dans|par).*"
    r"|en France\b.*|selon l'arrêté.*|\(depuis.*|\(avant.*)$",
    re.I,
)

PATTERNS = [
    # « Panneau A13a signalant la traversée d'enfants »
    re.compile(
        r"^panneau\s+(?:\w+\s+)?(?:signalant|indiquant|annonçant|marquant)\s+"
        r"(?:la\s|le\s|les\s|l'|un\s|une\s|des\s|du\s|de\s)?(?P<v>.+)$",
        re.I,
    ),
    # « Panneau de signalisation de virage à droite »
    re.compile(r"^panneau\s+de\s+signalisation\s+(?:de\s|d'|du\s)?(?P<v>.+)$", re.I),
    # « Panneau de limitation de vitesse à 50 km/h »
    re.compile(r"^panneau\s+(?:de\s|d'|du\s)(?P<v>.+)$", re.I),
    # « Panneau AB4 : stop » — deux-points explicites
    re.compile(r"^panneau\s+\S+\s*[:–—-]\s*(?P<v>.+)$", re.I),
]

# Si le résultat ressemble encore à ça, l'extraction a échoué.
REJECT = re.compile(
    r"^(?:signalisation|routier|routière|road sign|diagram|sign|france|"
    r"circulation|type\s|\W*$)",
    re.I,
)


def extract(desc: str) -> str | None:
    text = re.sub(r"\s+", " ", desc).strip()
    text = TAIL.sub("", text).strip(" .;,-–—")
    for pattern in PATTERNS:
        m = pattern.match(text)
        if not m:
            continue
        value = m.group("v").strip(" .;,-–—")
        value = TAIL.sub("", value).strip(" .;,-–—")
        if len(value) < 4 or len(value) > 90 or REJECT.match(value):
            continue
        # Une phrase entière n'est pas un libellé.
        if value.count(",") > 2 or len(value.split()) > 12:
            continue
        return value[0].upper() + value[1:]
    return None


def descriptions(codes: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for i in range(0, len(codes), 20):
        params = urllib.parse.urlencode({
            "action": "query",
            "titles": "|".join(f"File:France road sign {c}.svg" for c in codes[i:i + 20]),
            "prop": "imageinfo", "iiprop": "extmetadata", "format": "json",
        })
        req = urllib.request.Request(
            "https://commons.wikimedia.org/w/api.php?" + params, headers={"User-Agent": UA}
        )
        try:
            data = json.load(urllib.request.urlopen(req, timeout=40))
        except Exception:
            time.sleep(3)
            continue
        for page in data.get("query", {}).get("pages", {}).values():
            code = page["title"].replace("File:France road sign ", "").replace(".svg", "")
            meta = page.get("imageinfo", [{}])[0].get("extmetadata", {})
            desc = re.sub(r"<[^>]+>", "", meta.get("ImageDescription", {}).get("value", ""))
            if desc.strip():
                out[code] = desc.strip()
        time.sleep(1.5)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="montre sans écrire")
    args = ap.parse_args()

    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    codes = [r[0] for r in conn.execute(
        "SELECT code FROM sign WHERE country='FR' ORDER BY code")]

    descs = descriptions(codes)
    found, missed = {}, []
    for code in codes:
        name = extract(descs.get(code, ""))
        if name:
            found[code] = name
        else:
            missed.append(code)

    print(f"{len(found)} libellé(s) extrait(s) sur {len(codes)}")
    print(f"{len(missed)} sans libellé — ces panneaux ne porteront aucun exercice\n")
    for code, name in list(found.items())[:15]:
        print(f"  {code:7s} {name}")
    if missed:
        print(f"\n  écartés : {' '.join(missed[:20])}" + (" …" if len(missed) > 20 else ""))

    if args.dry_run:
        print("\n(essai à blanc — rien écrit)")
        return

    for code, name in found.items():
        conn.execute(
            "UPDATE sign SET name = ?, meaning = ?, image_alt = ?"
            " WHERE country='FR' AND code = ?",
            (name, name, f"Panneau {code} — {name}", code),
        )
    conn.commit()
    conn.close()
    print(f"\n{len(found)} panneau(x) nommé(s) en base")


if __name__ == "__main__":
    main()
