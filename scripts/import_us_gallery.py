#!/usr/bin/env python3
"""Construit le catalogue américain depuis la galerie Wikimedia.

Pourquoi pas la FHWA : sa page « Standard Highway Signs » ne publie que
les panneaux NOUVEAUX ET RÉVISÉS d'une édition — un supplément, pas un
catalogue. On y trouve « Express Restriction Ends » mais pas STOP.
Sa brochure illustrée, elle, est un scan sans couche texte.

La galerie Commons, elle, associe explicitement un fichier et sa
légende :

    File:MUTCD R1-1.svg|Stop
    File:MUTCD R1-2.svg|Yield (Give Way)

Le code vient du NOM DU FICHIER, le nom vient de la légende, et l'image
téléchargée est ce même fichier. Les trois sont donc liés par
construction — il n'y a pas d'étape où l'on apparie à la main.

Source communautaire : tout entre en 'community', jamais en 'verified'.

    python3 scripts/import_us_gallery.py --dry-run
    python3 scripts/import_us_gallery.py
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
MEDIA = ROOT / "media" / "signs" / "us"
API = "https://commons.wikimedia.org/w/api.php"
UA = "sara-exos/1.0 (https://learn.sara.education)"
GALLERY = "Road signs of the United States"

# R1-1, W11-2, R3-5aP, R1-5L… La lettre finale distingue les variantes
# (L/R pour gauche/droite, P pour plaque).
CODE = re.compile(r"^[A-Z]{1,2}\d{1,2}-\d{1,3}[a-zA-Z]{0,3}$")


def get(url: str, tries: int = 4) -> bytes:
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("inatteignable")


def clean_caption(text: str) -> str:
    text = re.sub(r"\{\{[^}]*\}\}|\[\[[^\]|]*\|?|\]\]|'''|''|<[^>]+>", " ", text)
    text = re.sub(r"\((?:19|20)\d{2}[–-].*?\)", " ", text)  # « (2003–2023) »
    text = re.sub(r"\s+", " ", text).strip(" .;,–—-")
    return text


def gallery_pairs() -> dict[str, str]:
    params = urllib.parse.urlencode({
        "action": "parse", "page": GALLERY, "prop": "wikitext",
        "format": "json", "formatversion": "2",
    })
    wikitext = json.loads(get(f"{API}?{params}"))["parse"]["wikitext"]

    out: dict[str, str] = {}
    for line in wikitext.splitlines():
        m = re.match(r"^\s*(?:File:)?(MUTCD[ _][^|\n]+?\.svg)\s*\|\s*(.+)$", line, re.I)
        if not m:
            continue
        filename = m.group(1).replace("_", " ")
        code = re.sub(r"^MUTCD\s+|\.svg$", "", filename, flags=re.I).strip()
        # Les variantes datées portent l'année dans le NOM de fichier :
        # on garde le fichier tel quel mais on écarte ces obsolètes,
        # sinon deux entrées se disputent le même code.
        if "(" in code or not CODE.match(code):
            continue
        name = clean_caption(m.group(2))
        # Une légende d'un seul mot très court n'est pas une signification.
        if not name or len(name) < 3 or len(name) > 90:
            continue
        out.setdefault(code, (name[0].upper() + name[1:], filename))
    return out


def image_urls(filenames: list[str]) -> dict[str, tuple[str, str, str]]:
    """URL, licence et auteur, par nom de fichier."""
    found: dict[str, tuple[str, str, str]] = {}
    for i in range(0, len(filenames), 20):
        params = urllib.parse.urlencode({
            "action": "query",
            "titles": "|".join("File:" + f for f in filenames[i:i + 20]),
            "prop": "imageinfo", "iiprop": "url|extmetadata", "format": "json",
        })
        try:
            data = json.loads(get(f"{API}?{params}"))
        except Exception:
            continue
        for page in data.get("query", {}).get("pages", {}).values():
            if "missing" in page:
                continue
            info = page["imageinfo"][0]
            meta = info.get("extmetadata", {})
            author = re.sub(
                r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")
            ).strip()
            found[page["title"][5:]] = (
                info["url"],
                meta.get("LicenseShortName", {}).get("value", "inconnue"),
                author or "Wikimedia Commons",
            )
        time.sleep(1.5)
    return found


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    pairs = gallery_pairs()
    if args.limit:
        pairs = dict(list(pairs.items())[: args.limit])
    print(f"{len(pairs)} panneau(x) dans la galerie\n")
    for code, (name, _) in list(pairs.items())[:12]:
        print(f"  {code:9s} {name}")

    if args.dry_run:
        print("\n(essai à blanc — rien écrit)")
        return

    MEDIA.mkdir(parents=True, exist_ok=True)
    urls = image_urls([f for _, f in pairs.values()])

    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")

    kept, refused = 0, []
    for code, (name, filename) in pairs.items():
        entry = urls.get(filename)
        if not entry:
            refused.append(f"{code}: image introuvable")
            continue
        url, license_, author = entry
        try:
            svg = get(url)
        except Exception as exc:
            refused.append(f"{code}: téléchargement impossible ({exc})")
            continue

        (MEDIA / f"{code}.svg").write_bytes(svg)
        conn.execute(
            "INSERT INTO sign (country, code, family, name, meaning, image_path,"
            " image_alt, source_url, license, attribution, review_state)"
            " VALUES ('US',?,?,?,?,?,?,?,?,?,'community')"
            " ON CONFLICT (country, code) DO UPDATE SET"
            "   name=excluded.name, meaning=excluded.meaning,"
            "   image_path=excluded.image_path, image_alt=excluded.image_alt,"
            "   source_url=excluded.source_url, license=excluded.license,"
            "   attribution=excluded.attribution, review_state='community'",
            (code, code[0], name, name, f"/media/signs/us/{code}.svg",
             f"Sign {code} — {name}",
             f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(filename)}",
             license_, author),
        )
        conn.commit()
        kept += 1

    print(f"\n{kept} panneau(x) enregistré(s)")
    if refused:
        print(f"{len(refused)} écarté(s) :")
        for r in refused[:10]:
            print("  ·", r)
    conn.close()


if __name__ == "__main__":
    main()
