#!/usr/bin/env python3
"""Remplit le catalogue de panneaux depuis les sources officielles.

Deux sources, deux niveaux de confiance — et le script ne prétend jamais
à plus de confiance qu'il n'en a :

  US  · deux sources combinées, chacune pour ce qu'elle fait le mieux :
        — le NOM officiel vient de la FHWA (archive SHS), qui fait
          autorité, et dont le nom de fichier porte le code : auto-vérifiant ;
        — l'IMAGE vient de Wikimedia, « MUTCD <code>.svg », domaine public.

        Les PDF de la FHWA ne sont PAS des illustrations : ce sont des
        plans de fabrication, cotés en rouge et barrés d'un filigrane
        « WORKING DRAWING ». Corrects, vérifiables, et inutilisables
        devant un apprenant. L'erreur est instructive : le contrôle
        d'auto-vérification confirmait QUEL panneau c'était, jamais que
        le fichier était montrable.

  FR  · Wikimedia Commons, convention exacte « France road sign <code>.svg ».
        Correspondance EXACTE uniquement, jamais de recherche floue : une
        recherche sur « A9 » remonte un panneau algérien et un écusson
        d'autoroute. Source communautaire, donc importé en 'imported' —
        un humain doit confirmer avant qu'un exercice s'y adosse.

    python3 scripts/import_signs.py --country US --limit 10
    python3 scripts/import_signs.py --country FR --codes A1a,A2b
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "sara.db"
# HORS de dist/ : `vite build` vide ce dossier à chaque construction.
# Les médias sont de la donnée, pas un artefact de build.
MEDIA = ROOT / "media" / "signs"

UA = "sara-exos/1.0 (https://learn.sara.education)"
FHWA_ZIP = "https://mutcd.fhwa.dot.gov/shsm_interim/zip_files/{}"
FHWA_INDEX = "https://mutcd.fhwa.dot.gov/shsm_interim/"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def get(url: str, tries: int = 4) -> bytes:
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("inatteignable")


# --------------------------------------------------------------------------
# USA
# --------------------------------------------------------------------------

def us_zip_name(code: str) -> str | None:
    """R1-9 → r01_09.zip · W4-4aP → w04_04ap.zip"""
    m = re.match(r"^([A-Z]+)(\d+)-(\d+)([a-zA-Z]*)$", code)
    if not m:
        return None
    fam, major, minor, suffix = m.groups()
    return f"{fam.lower()}{int(major):02d}_{int(minor):02d}{suffix.lower()}.zip"


def us_code_from_filename(name: str) -> str | None:
    """« R01-09 STATE LAW YIELD… » → R1-9"""
    m = re.match(r"^([A-Z]+)(\d+)-(\d+)([a-zA-Z]*)\s", name)
    if not m:
        return None
    fam, major, minor, suffix = m.groups()
    return f"{fam}{int(major)}-{int(minor)}{suffix}"


def us_index() -> list[str]:
    """Les codes réellement publiés, lus sur la page FHWA."""
    html = get(FHWA_INDEX).decode("utf-8", "replace")
    files = set(re.findall(r'zip_files/([a-z]\d+_\d+[a-z]*\.zip)', html))
    codes = []
    for f in sorted(files):
        m = re.match(r"^([a-z]+)(\d+)_(\d+)([a-z]*)\.zip$", f)
        if m:
            fam, major, minor, suffix = m.groups()
            # Le « P » final désigne une plaque et s'écrit en majuscule ;
            # les lettres de variante qui le précèdent restent minuscules.
            # D'où « d09_11bp » → « D9-11bP ». Sans cette nuance, le
            # contrôle d'auto-vérification rejette des panneaux valides.
            if suffix.endswith("p"):
                suffix = suffix[:-1] + "P"
            codes.append(f"{fam.upper()}{int(major)}-{int(minor)}{suffix}")
    return codes


def import_us(conn: sqlite3.Connection, codes: list[str]) -> tuple[int, list[str]]:
    out = MEDIA / "us"
    out.mkdir(parents=True, exist_ok=True)
    kept, refused = 0, []

    for code in codes:
        zname = us_zip_name(code)
        if not zname:
            refused.append(f"{code}: code non reconnu")
            continue
        try:
            blob = get(FHWA_ZIP.format(zname))
        except Exception as exc:
            refused.append(f"{code}: téléchargement impossible ({exc})")
            continue

        try:
            zf = zipfile.ZipFile(io.BytesIO(blob))
        except zipfile.BadZipFile:
            refused.append(f"{code}: archive illisible")
            continue

        pdfs = [n for n in zf.namelist() if n.lower().endswith(".pdf")]
        if not pdfs:
            refused.append(f"{code}: aucun PDF dans l'archive")
            continue
        inner = pdfs[0]

        # Le contrôle qui fait tout tenir : le code inscrit dans le nom du
        # fichier livré doit être celui qu'on a demandé. S'il diverge, on
        # n'enregistre rien — plutôt aucun panneau qu'un mauvais.
        found = us_code_from_filename(Path(inner).name)
        if found != code:
            # La FHWA nomme parfois l'archive sans le suffixe directionnel
            # qu'elle met dans le fichier : r03_20.zip contient « R3-20L »
            # (variante gauche). Ce n'est pas un décalage, c'est une
            # précision — on l'accepte, mais on enregistre sous le code
            # que le FICHIER déclare, jamais sous celui qu'on espérait.
            if found and found.rstrip("LR") == code.rstrip("LR"):
                code = found
            else:
                refused.append(f"{code}: l'archive contient {found!r} — écarté")
                continue

        # « R01-09 STATE LAW YIELD TO PEDESTRIANS 24X30 » → « State Law Yield
        # To Pedestrians ». Les dimensions en fin de nom sont une donnée de
        # fabrication, pas la signification du panneau.
        name = re.sub(r"^[A-Z]+\d+-\d+[a-zA-Z]*\s+", "", Path(inner).stem)
        name = re.sub(r"\s+\d+\s*[xX]\s*\d+\s*$", "", name).strip()
        rel = f"/media/signs/us/{code}.pdf"
        (out / f"{code}.pdf").write_bytes(zf.read(inner))

        conn.execute(
            "INSERT INTO sign (country, code, family, name, meaning, image_path,"
            " image_alt, source_url, license, attribution, review_state)"
            " VALUES ('US',?,?,?,?,?,?,?,'Domaine public (MUTCD)','FHWA','verified')"
            " ON CONFLICT (country, code) DO UPDATE SET"
            " name=excluded.name, image_path=excluded.image_path,"
            " review_state=excluded.review_state",
            (code, code[0], name.title(), name.title(), rel,
             f"Panneau {code} — {name.title()}", FHWA_ZIP.format(zname)),
        )
        conn.commit()
        kept += 1
    return kept, refused


# --------------------------------------------------------------------------
# France
# --------------------------------------------------------------------------

COMMONS_NAME = {
    "FR": "File:France road sign {}.svg",
    "US": "File:MUTCD {}.svg",
}


def import_commons(conn: sqlite3.Connection, country: str,
                   codes: list[str]) -> tuple[int, list[str]]:
    """Récupère les pictogrammes propres depuis Wikimedia.

    Correspondance EXACTE du nom, jamais de recherche approchante : sur
    « A9 », une recherche remonte un panneau algérien et un écusson
    d'autoroute. Source communautaire, donc 'imported' — un humain
    valide avant qu'un exercice s'y adosse.
    """
    pattern = COMMONS_NAME[country]
    out = MEDIA / country.lower()
    out.mkdir(parents=True, exist_ok=True)
    kept, refused = 0, []

    for batch in (codes[i:i + 10] for i in range(0, len(codes), 10)):
        titles = "|".join(pattern.format(c) for c in batch)
        query = urllib.parse.urlencode({
            "action": "query", "titles": titles, "prop": "imageinfo",
            "iiprop": "url|extmetadata", "format": "json",
        })
        data = json.loads(get(f"{COMMONS_API}?{query}"))

        prefix, suffix = pattern.split("{}")
        for page in data.get("query", {}).get("pages", {}).values():
            code = page["title"][len(prefix):].removesuffix(suffix)
            if "missing" in page:
                # Ni invention, ni repli sur une recherche approchante :
                # on note le trou et on passe.
                refused.append(f"{code}: absent de Commons sous ce nom exact")
                continue

            info = page["imageinfo"][0]
            meta = info.get("extmetadata", {})
            license_ = meta.get("LicenseShortName", {}).get("value", "inconnue")
            author = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()

            try:
                svg = get(info["url"])
            except Exception as exc:
                refused.append(f"{code}: téléchargement impossible ({exc})")
                continue

            rel = f"/media/signs/{country.lower()}/{code}.svg"
            (out / f"{code}.svg").write_bytes(svg)

            # Si le panneau existe déjà (nom officiel importé de la FHWA),
            # on ne remplace QUE l'image et sa provenance — le libellé
            # faisant autorité ne vient pas de Wikimedia. Et on repasse en
            # 'imported' : une image communautaire n'est pas auto-vérifiée.
            conn.execute(
                "INSERT INTO sign (country, code, family, name, meaning, image_path,"
                " image_alt, source_url, license, attribution, review_state)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,'imported')"
                " ON CONFLICT (country, code) DO UPDATE SET"
                " image_path=excluded.image_path, license=excluded.license,"
                " attribution=excluded.attribution, source_url=excluded.source_url,"
                " review_state='imported'",
                (country, code, code[0], f"Panneau {code}", "", rel,
                 f"Panneau {code}", info.get("descriptionurl", ""),
                 license_, author or "Wikimedia Commons"),
            )
            kept += 1
        conn.commit()   # par lot : un blocage ne perd que le lot en cours
        time.sleep(2)   # on reste poli avec l'API
    return kept, refused


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", choices=["FR", "US"], required=True)
    ap.add_argument("--codes", help="liste séparée par des virgules")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--source", choices=["commons", "fhwa"], default="commons",
                    help="fhwa = noms officiels US (plans cotés, pas des illustrations)")
    args = ap.parse_args()

    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("PRAGMA foreign_keys = ON")
    # L'API et l'autre import écrivent dans la même base. Sans ce délai,
    # SQLite abandonne immédiatement sur « database is locked ».
    conn.execute("PRAGMA busy_timeout = 60000")

    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    elif args.country == "US":
        codes = us_index()
    else:
        codes = [r[0] for r in conn.execute(
            "SELECT code FROM sign WHERE country = 'FR' ORDER BY code")]
        if not codes:
            raise SystemExit("--codes est requis pour la France")

    if args.limit:
        codes = codes[: args.limit]

    if args.source == "fhwa":
        kept, refused = import_us(conn, codes)
    else:
        kept, refused = import_commons(conn, args.country, codes)

    print(f"{kept} panneau(x) enregistré(s) sur {len(codes)} demandé(s)")
    if refused:
        print(f"{len(refused)} écarté(s) — rien n'est enregistré à moitié :")
        for r in refused:
            print("  ·", r)
    conn.close()


if __name__ == "__main__":
    main()
