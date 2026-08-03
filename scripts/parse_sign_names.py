#!/usr/bin/env python3
"""Lit un tableau « code + signification » disposé en colonnes.

Le document présente les panneaux en grille : une ligne de codes, puis
la signification de chacun empilée dessous. `pdftotext -layout` ne suffit
pas — il coupe les mots au milieu quand deux colonnes se chevauchent à
l'impression. On travaille donc sur les COORDONNÉES réelles des mots
(`pdftotext -bbox-layout`), ce qui rend le découpage exact.

Les significations sont la formulation réglementaire de l'IISR : du
texte officiel, pas la prose d'un éditeur.

    pdftotext -bbox-layout panneaux.pdf panneaux.xml
    python3 scripts/parse_sign_names.py panneaux.xml --dry-run
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "sara.db"
NS = {"x": "http://www.w3.org/1999/xhtml"}

CODE = re.compile(r"^(?:A|AB|B|C|CE|D|E|EB|M|SR)\d{1,3}[a-z]?\d?$")

# En-têtes et pieds de page du document, à ne jamais prendre pour du sens.
NOISE = re.compile(
    r"^(?:liste|complète|des|signaux|routiers|page|www\.|http|\d+)$", re.I
)

# Tolérance horizontale : un mot appartient à la colonne dont l'ancre est
# la plus proche à gauche. 40 points couvre l'indentation sans mordre sur
# la colonne suivante, qui est à ~175 points.
BAND = 40.0


def words_of(page: ET.Element) -> list[tuple[float, float, str]]:
    out = []
    for w in page.findall(".//x:word", NS):
        text = (w.text or "").strip()
        if text:
            out.append((float(w.get("xMin")), float(w.get("yMin")), text))
    return out


def parse(path: Path) -> dict[str, str]:
    root = ET.parse(path).getroot()
    found: dict[str, list[str]] = {}

    for page in root.findall(".//x:page", NS):
        words = words_of(page)
        if not words:
            continue

        # Les codes donnent à la fois les colonnes (x) et les lignes (y).
        codes = [(x, y, t) for x, y, t in words if CODE.match(t)]
        if not codes:
            continue

        rows: dict[float, list[tuple[float, str]]] = {}
        for x, y, t in codes:
            key = min((k for k in rows if abs(k - y) <= 6), default=y)
            rows.setdefault(key, []).append((x, t))
        row_ys = sorted(rows)

        for i, y0 in enumerate(row_ys):
            y_end = row_ys[i + 1] if i + 1 < len(row_ys) else float("inf")
            anchors = sorted(rows[y0])

            for j, (x0, code) in enumerate(anchors):
                x_end = anchors[j + 1][0] if j + 1 < len(anchors) else float("inf")
                cell = [
                    # (ligne, position dans la ligne, mot) — l'ordre de
                    # lecture est vertical PUIS horizontal. Trier sur le
                    # seul y remettrait les mots par ordre alphabétique.
                    (round(y / 6), x, t)
                    for x, y, t in words
                    # Sous le code, au-dessus de la ligne suivante, et dans
                    # la bande horizontale de CETTE colonne.
                    if y0 + 4 < y < y_end
                    # Borne droite quasi collée à la colonne suivante :
                    # la retirer de BAND laissait tomber les mots qui
                    # débordent en fin de ligne — d'où « les enfant »
                    # au lieu de « les enfants ».
                    and x0 - BAND <= x < x_end - 5
                    and not CODE.match(t)
                    and not NOISE.match(t)
                ]
                if not cell:
                    continue
                text = " ".join(t for _, _, t in sorted(cell))
                text = re.sub(r"\s+", " ", text).strip(" .;,")
                # Le premier arrivé gagne : le document répète certains
                # panneaux (variantes de taille) avec le même sens.
                if code not in found and 8 <= len(text) <= 240:
                    found[code] = text

    return found


def shorten(meaning: str) -> str:
    """Un libellé de réponse tient en 60 caractères ; la phrase complète non."""
    text = re.sub(
        r"^(?:Indique|Signale|Annonce|Marque|Prescrit|Notifie)\s+"
        r"(?:que\s|qu'|de\s|la\s|le\s|les\s|l'|un\s|une\s|des\s|du\s|d'|aux\s|au\s)*",
        "",
        meaning.strip(),
        flags=re.I,
    )
    text = re.split(r"[.;]", text)[0].strip()
    # La couche texte du PDF perd parfois le « s » final : le document
    # écrit littéralement « les enfant ». On ne rétablit l'accord que
    # derrière un déterminant pluriel — là où il ne peut pas y avoir de
    # doute — et jamais ailleurs.
    text = re.sub(r"\b(les|des|aux)\s+([a-zéèêàôûîç]+[^sxz\W])\b",
                  lambda m: f"{m.group(1)} {m.group(2)}s", text)
    if len(text) > 58:
        cut = text[:58]
        pivot = cut.rfind(" ")
        text = cut[:pivot] if pivot > 30 else cut
    return (text[0].upper() + text[1:]) if text else ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="XML issu de pdftotext -bbox-layout")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    parsed = parse(Path(args.source))

    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    have = [r[0] for r in conn.execute(
        "SELECT code FROM sign WHERE country='FR' ORDER BY code")]

    matched = {c: parsed[c] for c in have if c in parsed and shorten(parsed[c])}
    missing = [c for c in have if c not in matched]

    print(f"{len(parsed)} code(s) lus dans le document")
    print(f"{len(matched)} panneaux nommables sur {len(have)} en base")
    print(f"{len(missing)} resteront sans exercice\n")
    for code, meaning in list(matched.items())[:16]:
        print(f"  {code:7s} {shorten(meaning)}")
    if missing:
        print(f"\n  sans : {' '.join(missing[:22])}" + (" …" if len(missing) > 22 else ""))

    if args.dry_run:
        print("\n(essai à blanc — rien écrit)")
        return

    for code, meaning in matched.items():
        label = shorten(meaning)
        conn.execute(
            "UPDATE sign SET name = ?, meaning = ?, image_alt = ?"
            " WHERE country='FR' AND code = ?",
            (label, meaning, f"Panneau {code} — {label}", code),
        )
    conn.commit()
    conn.close()
    print(f"\n{len(matched)} panneau(x) nommé(s)")


if __name__ == "__main__":
    main()
