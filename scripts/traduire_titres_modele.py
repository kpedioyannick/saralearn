#!/usr/bin/env python3
"""Les titres français que Wikipédia ne peut pas donner, écrits par le modèle.

`traduire_titres.py` prend les titres aux LIENS DE LANGUE : exact par
construction, gratuit, et c'est lui qui doit passer en premier. Il a rendu
1 669 titres sur 2 187, puis il s'est arrêté net — les 518 qui restent sont
des articles anglais SANS version française. Le lien n'existe pas ; il n'y
a rien à aller chercher. Relancer ce script mille fois ne changera rien.

Reste deux façons de finir, et une seule tient :

  · le traducteur mot à mot (`deep-translator`), gratuit, qui traduit
    chaque chaîne ISOLÉMENT. C'est lui qui rend « Sun dog » par « chien du
    soleil » là où l'article s'appelle « Parhélie », et qui a donné
    « l'ascenseur » pour *lift* dans un exercice servi. Sur un titre de
    trois mots, il n'a ni contexte ni filet ;

  · le modèle du projet, à qui on DONNE le contexte : le jour de la
    création dont le chapitre relève, et le chapitre parent. « Sea worm »
    sous « Les Animaux marins / Ver marin » ne peut plus devenir autre
    chose qu'un ver. C'est cette différence-là qu'on paye.

Vingt-cinq titres par appel, avec leur voisinage. Le rendu est vérifié
avant écriture — voir `verifier` — et ce qui ne passe pas reste en
anglais : mieux vaut un titre anglais juste qu'un titre français inventé.

    python3 scripts/traduire_titres_modele.py --dry-run   # sans écrire
    python3 scripts/traduire_titres_modele.py --limite 50 # un essai court
    python3 scripts/traduire_titres_modele.py             # les 518

Relançable sans risque : il ne demande que ce qui n'a pas encore sa ligne,
et `source = 'modele'` garde la trace de qui a écrit quoi — on doit
pouvoir repasser sur ce qu'une machine a produit sans toucher au reste.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.llm import ask, extract_json_object  # noqa: E402

DB = ROOT / "data" / "sara.db"

# Vingt-cinq : assez pour que le modèle voie une famille de titres d'un
# coup — les huit vers marins ensemble, et il ne peut plus les rendre par
# le même mot — mais assez court pour que la réponse ne soit pas coupée.
PAR_APPEL = 25

CONSIGNE = """Tu traduis en français des titres d'articles de Wikipédia.

Ces articles n'ont PAS de version française : c'est à toi de proposer le
titre qu'ils porteraient. Écris comme Wikipédia titre ses articles — un
groupe nominal, sans article défini en tête, sans point final, majuscule
au premier mot seulement (sauf noms propres).

Trois règles qui comptent :

1. NE TRADUIS PAS ce qui ne se traduit pas : noms propres, taxons latins
   (Chondrichthyes, Osteichthyes), termes que les francophones gardent en
   anglais dans leur domaine. Rends alors le titre anglais inchangé.
2. Le CONTEXTE t'est donné — le thème et l'article parent. Sers-t'en :
   « Sea worm » sous « Les Animaux marins » est un ver, pas autre chose.
3. Deux titres différents doivent rester DIFFÉRENTS en français. Si deux
   entrées du lot se rendraient par le même mot, distingue-les.

Rends UNIQUEMENT un objet JSON, sans texte autour :
{"titres": {"<id>": "<titre français>", ...}}

Un id par entrée demandée, tous présents.

Les titres à traduire :
{{ENTREES}}
"""


def restants(conn: sqlite3.Connection, lang: str, limite: int | None) -> list[dict]:
    sql = (
        "SELECT ch.id, ch.title, th.title AS theme,"
        "       COALESCE(pt.title, p.title) AS parent"
        "  FROM chapter ch"
        "  JOIN theme th ON th.id = ch.theme_id"
        "  LEFT JOIN chapter p ON p.id = ch.parent_id"
        "  LEFT JOIN chapter_translation pt"
        "         ON pt.chapter_id = p.id AND pt.lang = ?"
        " WHERE ch.status != 'rejected' AND ch.visibility = 'public'"
        "   AND NOT EXISTS (SELECT 1 FROM chapter_translation t"
        "                    WHERE t.chapter_id = ch.id AND t.lang = ?)"
        # Par thème puis par parent : un lot voit ainsi des titres
        # voisins, ce qui est exactement ce qui permet de les distinguer.
        " ORDER BY ch.theme_id, ch.parent_id, ch.title"
    )
    params: list = [lang, lang]
    if limite:
        sql += " LIMIT ?"
        params.append(limite)
    return [dict(r) for r in conn.execute(sql, params)]


def verifier(entree: dict, rendu: str, deja: set[str]) -> str | None:
    """Ce qui rend un titre inservable. Le motif, ou None.

    Le refus est la valeur par défaut : ce qui ne passe pas reste en
    anglais, et l'anglais est lisible. Un titre français faux, lui, ne se
    voit pas — c'est le pire des deux.
    """
    titre = (rendu or "").strip()
    if not titre:
        return "vide"
    if len(titre) > 200:
        return "trop long"
    if titre.endswith("."):
        return "finit par un point"
    # Une phrase, une explication, une paraphrase : le modèle a répondu à
    # côté. Un titre d'article ne dépasse pas trois fois son original.
    if len(titre) > max(60, 3 * len(entree["title"])):
        return "trois fois plus long que l'original"
    if titre.casefold() in deja:
        return "déjà pris par un autre chapitre du lot"
    return None


async def un_lot(lot: list[dict]) -> dict[int, str]:
    entrees = "\n".join(
        f'- id {e["id"]} · thème « {e["theme"]} »'
        + (f' · article parent « {e["parent"]} »' if e["parent"] else "")
        + f' · titre anglais : "{e["title"]}"'
        for e in lot
    )
    brut = await ask(CONSIGNE.replace("{{ENTREES}}", entrees))
    objet = extract_json_object(brut)
    titres = objet.get("titres") or objet
    out: dict[int, str] = {}
    for cle, valeur in titres.items():
        try:
            out[int(str(cle).strip())] = str(valeur)
        except (TypeError, ValueError):
            continue
    return out


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="fr")
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--limite", type=int, default=0, help="ne traiter que N chapitres")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    lot_total = restants(conn, args.lang, args.limite or None)
    if not lot_total:
        print("rien à faire : tous les chapitres ont leur titre.")
        return
    print(f"{len(lot_total)} chapitres sans titre en « {args.lang} »")

    # Ce qui est déjà pris, pour ne pas fabriquer deux fois le même titre
    # dans une même catégorie — le piège « Crépuscule » de la migration
    # 026, qui aurait donné deux lignes identiques dans un rayon de six.
    #
    # LES CHAPITRES DU LOT EN SONT EXCLUS, et ça a coûté 22 refus au
    # premier passage. Sans l'exclusion, le titre anglais d'un chapitre à
    # traduire compte comme « déjà pris » — par lui-même. Or la consigne
    # demande justement de RENDRE LE TITRE INCHANGÉ pour ce qui ne se
    # traduit pas : « Jeewanu », « Rhizobia », « WISE J0336−0143 ». Le
    # modèle obéissait, et la vérification refusait sa bonne réponse.
    a_faire = {e["id"] for e in lot_total}
    pris: dict[int, set[str]] = {}
    for r in conn.execute(
        "SELECT ch.id, ch.theme_id, COALESCE(ct.title, ch.title) AS t FROM chapter ch"
        "  LEFT JOIN chapter_translation ct"
        "         ON ct.chapter_id = ch.id AND ct.lang = ?"
        " WHERE ch.status != 'rejected' AND ch.visibility = 'public'",
        (args.lang,),
    ):
        if r["id"] in a_faire:
            continue
        pris.setdefault(r["theme_id"], set()).add(r["t"].casefold())

    par_theme = {e["id"]: e for e in lot_total}
    theme_de = dict(
        conn.execute(
            "SELECT id, theme_id FROM chapter WHERE id IN ("
            + ",".join("?" * len(par_theme))
            + ")",
            list(par_theme),
        )
    )

    ecrits: list[tuple] = []
    refuses: list[tuple[str, str]] = []
    for i in range(0, len(lot_total), PAR_APPEL):
        lot = lot_total[i : i + PAR_APPEL]
        try:
            rendus = await un_lot(lot)
        except Exception as exc:  # noqa: BLE001 — un lot raté n'arrête pas le reste
            print(f"\n  lot {i // PAR_APPEL + 1} : échec ({exc})", file=sys.stderr)
            continue
        for e in lot:
            rendu = rendus.get(e["id"])
            if rendu is None:
                refuses.append((e["title"], "absent de la réponse"))
                continue
            tid = theme_de.get(e["id"], 0)
            motif = verifier(e, rendu, pris.setdefault(tid, set()))
            if motif:
                refuses.append((e["title"], motif))
                continue
            titre = rendu.strip()
            pris[tid].add(titre.casefold())
            ecrits.append((e["id"], args.lang, titre, "modele"))
        print(
            f"  {min(i + PAR_APPEL, len(lot_total)):>5}/{len(lot_total)}"
            f" · {len(ecrits)} retenus · {len(refuses)} refusés",
            end="\r",
            flush=True,
        )

    print()
    for cid, _, titre, _ in ecrits[:8]:
        print(f"    {par_theme[cid]['title']}  →  {titre}")
    if refuses:
        print(f"  {len(refuses)} refusés, laissés en anglais :")
        for anglais, motif in refuses[:8]:
            print(f"    {anglais} — {motif}")

    if args.dry_run:
        print(f"--dry-run : {len(ecrits)} titres prêts, rien n'a été écrit.")
        return

    with conn:
        conn.executemany(
            "INSERT OR IGNORE INTO chapter_translation"
            " (chapter_id, lang, title, source) VALUES (?, ?, ?, ?)",
            ecrits,
        )
    total = conn.execute(
        "SELECT COUNT(*) FROM chapter_translation WHERE lang = ?", (args.lang,)
    ).fetchone()[0]
    print(f"écrit. {total} chapitres ont désormais leur titre en « {args.lang} ».")


if __name__ == "__main__":
    asyncio.run(main())
