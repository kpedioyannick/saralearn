#!/usr/bin/env python3
"""Les titres français des chapitres, pris aux liens de langue de Wikipédia.

Pourquoi pas un traducteur : les 2 187 chapitres SONT des articles de
Wikipédia, et Wikipédia sait déjà comment chacun s'appelle en français.
« 22° halo » se dit « Halo à 22 degrés » — un traducteur automatique
rendrait « 22° halo » ou « halo de 22° », et « Sun dog » donnerait « chien
du soleil » là où l'article s'appelle « Parhélie ». Le lien de langue est
exact par construction : c'est un humain qui l'a posé, sur l'article
lui-même.

C'est aussi gratuit et sans clé. Cinquante identifiants de page par
requête, une pause entre deux, et on n'écrit que ce qui existe : un
article sans version française ne reçoit pas de ligne et reste affiché en
anglais. **Mieux vaut un titre anglais juste qu'un titre français
inventé.**

    python3 scripts/traduire_titres.py            # tout ce qui manque
    python3 scripts/traduire_titres.py --lang es  # une autre langue
    python3 scripts/traduire_titres.py --dry-run  # sans rien écrire

Relançable sans risque : il ne demande que les chapitres qui n'ont pas
encore leur ligne dans la langue voulue.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "sara.db"

API = "https://en.wikipedia.org/w/api.php"
# La courtoisie d'usage sur l'API de Wikimédia : se nommer, pour qu'on
# sache qui appelle et qu'on puisse être joint plutôt que bloqué.
UA = "SaraLearn/1.0 (https://learn.sara.education)"

# Cinquante, c'est le plafond de l'API pour un client anonyme.
PAR_REQUETE = 50


def a_traduire(conn: sqlite3.Connection, lang: str) -> list[tuple[int, int, str]]:
    """(chapter_id, pageid, titre anglais) pour ce qui n'a pas sa ligne."""
    return [
        (r["id"], r["pageid"], r["title"])
        for r in conn.execute(
            "SELECT ch.id, ch.title, json_extract(ch.meta, '$.pageid') AS pageid"
            "  FROM chapter ch"
            " WHERE json_extract(ch.meta, '$.pageid') IS NOT NULL"
            "   AND NOT EXISTS (SELECT 1 FROM chapter_translation t"
            "                    WHERE t.chapter_id = ch.id AND t.lang = ?)"
            " ORDER BY ch.id",
            (lang,),
        )
    ]


def langlinks(client: httpx.Client, pageids: list[int], lang: str) -> dict[int, str]:
    """Le titre de l'article dans la langue demandée, par identifiant."""
    r = client.get(
        API,
        params={
            "action": "query",
            "prop": "langlinks",
            "lllang": lang,
            "lllimit": "500",
            "pageids": "|".join(str(p) for p in pageids),
            "format": "json",
            "formatversion": "2",
        },
        timeout=30,
    )
    r.raise_for_status()
    out: dict[int, str] = {}
    for page in r.json().get("query", {}).get("pages", []):
        liens = page.get("langlinks") or []
        if liens and liens[0].get("title"):
            out[page["pageid"]] = liens[0]["title"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="fr")
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pause", type=float, default=0.3, help="secondes entre deux requêtes")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    restant = a_traduire(conn, args.lang)
    if not restant:
        print("rien à faire : tous les chapitres ont leur titre.")
        return
    print(f"{len(restant)} chapitres sans titre en « {args.lang} »")

    # Un pageid porte PLUSIEURS chapitres : le même article peut être
    # rangé sous deux jours de la création — « Human eye » est à la fois
    # de la Lumière et de l'Être humain. Une correspondance simple
    # pageid → chapitre en perdait un sur cinq, silencieusement : le
    # dernier écrasait les autres et eux restaient en anglais.
    par_pageid: dict[int, list[tuple[int, str]]] = {}
    for cid, pageid, titre in restant:
        par_pageid.setdefault(pageid, []).append((cid, titre))

    trouves: list[tuple] = []
    with httpx.Client(headers={"User-Agent": UA}) as client:
        pageids = list(par_pageid)
        for i in range(0, len(pageids), PAR_REQUETE):
            lot = pageids[i : i + PAR_REQUETE]
            try:
                rendus = langlinks(client, lot, args.lang)
            except Exception as exc:  # noqa: BLE001 — un lot raté n'arrête pas le reste
                print(f"  lot {i // PAR_REQUETE + 1} : échec ({exc})", file=sys.stderr)
                continue
            for pageid, titre in rendus.items():
                for cid, _ in par_pageid[pageid]:
                    trouves.append((cid, args.lang, titre))
            print(
                f"  {i + len(lot):>5}/{len(pageids)} · {len(trouves)} titres trouvés",
                end="\r",
                flush=True,
            )
            time.sleep(args.pause)

    print()
    manquants = len(restant) - len(trouves)
    print(
        f"{len(trouves)} chapitres traduits ({len(pageids)} articles demandés) ·"
        f" {manquants} sans article dans cette langue"
    )
    for cid, _, titre in trouves[:5]:
        anglais = next(t for c, _, t in restant if c == cid)
        print(f"    {anglais}  →  {titre}")

    if args.dry_run:
        print("--dry-run : rien n'a été écrit.")
        return

    with conn:
        conn.executemany(
            "INSERT OR IGNORE INTO chapter_translation (chapter_id, lang, title, source)"
            " VALUES (?, ?, ?, 'wikipedia-langlinks')",
            trouves,
        )
    total = conn.execute(
        "SELECT COUNT(*) FROM chapter_translation WHERE lang = ?", (args.lang,)
    ).fetchone()[0]
    print(f"écrit. {total} chapitres ont désormais leur titre en « {args.lang} ».")


if __name__ == "__main__":
    main()
