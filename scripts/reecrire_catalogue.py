#!/usr/bin/env python3
"""Réécrit le catalogue avec la consigne d'intuition du 19/08/2026.

Les 179 exercices en base ont été écrits avec la consigne précédente,
celle qui demandait « les définitions à connaître ». Ils se répondent en
appariant deux mots. La nouvelle consigne (`api/sections.py`) demande
l'inverse : une scène, une prédiction ou une cause, et trois mauvaises
options qui sont des croyances réelles.

CE SCRIPT NE SUPPRIME RIEN. L'ancien exercice passe en `state='draft'` :
il sort du flux, il reste en base, et les tentatives qui le désignent
gardent leur sens. Un `DELETE` casserait treize lignes d'`attempt` et
serait sans retour — ce dépôt a déjà perdu 886 exercices une fois.

L'ORDRE COMPTE, et il est le même pour chaque chapitre :

  1. on écrit le nouveau lot ;
  2. SI ET SEULEMENT SI il a produit quelque chose, on met l'ancien en
     réserve. Un chapitre dont la réécriture échoue garde ses exercices :
     mieux vaut l'ancienne forme qu'un chapitre vide ;
  3. on traduit le nouveau lot en français.

L'anglais reste la source, le français est traduit — comme partout
ailleurs. « Réécrire en anglais ET en français » veut dire : écrire
l'anglais, puis passer le traducteur.

Reprise : un chapitre déjà réécrit porte une ligne `exercise_prompt` de
modèle `reecriture` en `done`. Relancer le script reprend où il s'est
arrêté.

    python3 scripts/reecrire_catalogue.py --dry-run
    python3 scripts/reecrire_catalogue.py --chapter 5
    python3 scripts/reecrire_catalogue.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.critic import review  # noqa: E402
from api.db import connection, rows, scalar, transaction  # noqa: E402
from api.llm import ask, validate  # noqa: E402
from api.sections import article  # noqa: E402
from api.topup import LANG, LEVEL, MATIERE, TYPE, source_de  # noqa: E402
from api.traduction import LANGUES_CACHE, traduire_exercices  # noqa: E402

MODEL = "reecriture"
DEMANDE = 10


def a_reecrire(conn) -> list[dict]:
    """Les chapitres qui ont des exercices de l'ancienne forme.

    On saute ceux qui portent déjà une réécriture aboutie : le script se
    relance sans repayer ce qui est fait.
    """
    return rows(
        conn,
        "SELECT e.chapter_id AS id, ch.title, COUNT(*) AS n"
        "  FROM exercise e JOIN chapter ch ON ch.id = e.chapter_id"
        " WHERE e.state = 'validated'"
        "   AND NOT EXISTS (SELECT 1 FROM exercise_prompt p"
        "                    WHERE p.chapter_id = e.chapter_id"
        "                      AND p.model = ? AND p.status = 'done')"
        " GROUP BY e.chapter_id ORDER BY e.chapter_id",
        (MODEL,),
    )


async def reecrire(chapter_id: int, titre: str) -> tuple[int, int, int]:
    """Un chapitre. Rend (écrits, mis en réserve, traduits)."""
    with connection() as conn:
        src = source_de(conn, chapter_id)
        # Les identifiants de l'ANCIEN lot, relevés avant d'écrire : c'est
        # ce qu'on mettra en réserve, et seulement ça. Relever après
        # l'écriture emporterait le nouveau lot avec l'ancien.
        anciens = [
            r["id"]
            for r in rows(
                conn,
                "SELECT id FROM exercise WHERE chapter_id = ? AND state = 'validated'",
                (chapter_id,),
            )
        ]
    if src is None:
        print(f"    pas de source en base — chapitre laissé tel quel")
        return 0, 0, 0

    with connection() as conn:
        with transaction(conn):
            cur = conn.execute(
                "INSERT INTO exercise_prompt (chapter_id, position, title,"
                " model, requested_count, status)"
                " VALUES (?, (SELECT COALESCE(MAX(position), 0) + 1"
                "             FROM exercise_prompt WHERE chapter_id = ?),"
                " ?, ?, ?, 'running')",
                (chapter_id, chapter_id, f"Réécriture — {titre}", MODEL, DEMANDE),
            )
            run_id = cur.lastrowid

    # `deja` reste VIDE, et c'est voulu : la liste des énoncés déjà posés
    # sert à ne pas répéter une question. Ici on veut au contraire
    # reprendre les mêmes sujets sous une autre forme — les interdire
    # priverait le nouveau lot de ce que le chapitre a de plus important.
    try:
        raw = await ask(article(src["theme"], src["chapter"], src["source"], DEMANDE, []))
        items = validate(raw, TYPE, LANG)
    except Exception as exc:  # noqa: BLE001
        with connection() as conn:
            conn.execute(
                "UPDATE exercise_prompt SET status = 'failed', error = ?,"
                " finished_at = datetime('now') WHERE id = ?",
                (str(exc)[:1000], run_id),
            )
        print(f"    échec de génération : {exc}")
        return 0, 0, 0

    gardes = []
    for item in items:
        verdict = await review(item, LANG, level=LEVEL, kind=TYPE, matiere=MATIERE)
        if verdict.ok:
            gardes.append(item)

    if not gardes:
        # RIEN DE NEUF : on ne touche pas à l'ancien. Un chapitre vide
        # serait pire que le même chapitre en moins bonne forme.
        with connection() as conn:
            conn.execute(
                "UPDATE exercise_prompt SET status = 'failed',"
                " error = 'aucun exercice retenu', finished_at = datetime('now')"
                " WHERE id = ?",
                (run_id,),
            )
        print(f"    0 retenu sur {len(items)} — ancien lot conservé")
        return 0, 0, 0

    neufs: list[int] = []
    with connection() as conn:
        with transaction(conn):
            for item in gardes:
                cur = conn.execute(
                    "INSERT INTO exercise (chapter_id, exercise_prompt_id, type_question,"
                    " prompt, body, options, correct_index, ok_title, ok_line,"
                    " ko_title, ko_line, exp_title, exp_text, state)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'validated')",
                    (
                        chapter_id, run_id, TYPE,
                        item["prompt"], item["body"],
                        json.dumps(item["options"], ensure_ascii=False),
                        item["correct_index"],
                        item["ok_title"], item["ok_line"],
                        item["ko_title"], item["ko_line"],
                        item["exp_title"], item["exp_text"],
                    ),
                )
                neufs.append(cur.lastrowid)
            # L'ancien lot sort du flux MAINTENANT, et pas avant : le
            # chapitre n'a jamais été vide, pas même une seconde.
            if anciens:
                conn.executemany(
                    "UPDATE exercise SET state = 'draft' WHERE id = ?",
                    [(i,) for i in anciens],
                )
            conn.execute(
                "UPDATE exercise_prompt SET status = 'done', produced_count = ?,"
                " finished_at = datetime('now') WHERE id = ?",
                (len(gardes), run_id),
            )
            conn.execute(
                "UPDATE chapter SET exercise_count ="
                " (SELECT COUNT(*) FROM exercise WHERE chapter_id = ? AND state = 'validated')"
                " WHERE id = ?",
                (chapter_id, chapter_id),
            )

    traduits = 0
    for lang in LANGUES_CACHE:
        traduits += await traduire_exercices(neufs, lang)
    return len(neufs), len(anciens), traduits


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", type=int, help="un seul chapitre")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="reprendre un chapitre déjà réécrit — pour celui dont"
                         " l'audit a montré qu'il était mauvais")
    args = ap.parse_args()

    with connection() as conn:
        cibles = a_reecrire(conn)
        if args.force and args.chapter:
            # `a_reecrire` saute ce qui porte déjà une réécriture aboutie.
            # Ici on veut justement y revenir : l'audit
            # (`scripts/auditer_exercices.py`) a nommé des chapitres dont
            # la nouvelle version est fausse plus d'une fois sur deux.
            cibles = rows(
                conn,
                "SELECT e.chapter_id AS id, ch.title, COUNT(*) AS n"
                "  FROM exercise e JOIN chapter ch ON ch.id = e.chapter_id"
                " WHERE e.state = 'validated' AND e.chapter_id = ?"
                " GROUP BY e.chapter_id",
                (args.chapter,),
            )
    if args.chapter:
        cibles = [c for c in cibles if c["id"] == args.chapter]
    cibles = cibles[: args.limit]

    if not cibles:
        print("Rien à réécrire.")
        return 0

    total = sum(c["n"] for c in cibles)
    print(f"{len(cibles)} chapitres, {total} exercices de l'ancienne forme :")
    for c in cibles:
        print(f"  {c['id']:>5}  {c['title'][:45]:<45} {c['n']}")
    # Mesuré : 30 s d'écriture, une dizaine d'appels courts au juge, et
    # 9 s par exercice pour la traduction, celle-ci sérialisée par le
    # verrou de `traduction._GOOGLE`.
    print(f"\n≈ {len(cibles) * 50 // 60 + total * 9 // 60} min, "
          f"≈ ${len(cibles) * 0.008:.2f} d'appels au modèle.")
    print("L'ancien lot passe en 'draft' : rien n'est supprimé.")
    if args.dry_run:
        return 0

    t0 = time.time()
    ecrits = reserve = traduits = 0
    for i, c in enumerate(cibles, 1):
        print(f"\n[{i}/{len(cibles)}] {c['id']} {c['title']}")
        n, vieux, tr = await reecrire(c["id"], c["title"])
        ecrits += n
        reserve += vieux
        traduits += tr
        if n:
            print(f"    {n} écrits, {vieux} mis en réserve, {tr} traduits")

    print(f"\n{ecrits} exercices neufs, {reserve} mis en réserve, "
          f"{traduits} traduits, en {int(time.time() - t0) // 60} min.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
