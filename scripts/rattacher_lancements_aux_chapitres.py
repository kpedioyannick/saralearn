#!/usr/bin/env python3
"""Remplit `exercise_prompt.chapter_id`, laissé nul sur les 202 lancements.

Les exercices ont été écrits hors base, dans `db/creation/*.json`, puis
importés par `import_exercises.py` — qui n'écrivait pas le chapitre. Le
lien chapitre → lancement existe donc dans le schéma sans avoir jamais
été renseigné : impossible de répondre en SQL à « combien d'exercices
pour ce chapitre ? ».

L'information est récupérable, par trois chemins de fiabilité décroissante.

1. PAR LE CONTENU (196 lancements sur 202). Les énoncés d'un lancement
   sont cherchés à l'identique dans les fichiers. Un fichier qui les
   contient tous est le fichier d'origine ; son nom donne le rang, et
   (thème, rang) donne le chapitre. Aucune approximation.

2. PAR LE RANG SEUL (1 lancement). Le 512 ne porte qu'un exercice — la
   question corrigée après un rejet des règles. Deux fichiers le
   contiennent, `living-light-02` et `living-light-02b`, mais tous deux
   portent le rang 02 : l'ambiguïté ne change pas le chapitre.

3. PAR RESSEMBLANCE (5 lancements). Les cinq lots du thème 229 passés en
   `state='rejected'` — les doublons connus. Leur texte n'est dans aucun
   fichier : les fichiers gardent la version corrigée, la base garde
   l'écartée. On les rattache au lancement validé dont ils sont le plus
   proche. Mesure : 47 à 58 % de ressemblance, contre 37 à 42 % pour des
   lots sans rapport du même thème — le signal est réel, mais c'est le
   seul endroit où ce script infère au lieu de constater.

    python3 scripts/rattacher_lancements_aux_chapitres.py --dry-run
    python3 scripts/rattacher_lancements_aux_chapitres.py
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "sara.db"
CREATION = ROOT / "db" / "creation"

# `verification.json` vit dans le même dossier sans être un lot : il
# porte des verdicts de relecture, pas des exercices.
def lots_de_contenu() -> list[dict]:
    out = []
    for p in sorted(CREATION.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if not (isinstance(d, list) and d and "theme_id" in d[0]):
            continue
        # `02b` existe : un fichier de correction rattaché au même rang
        # que son fichier d'origine. On ne retient que les deux chiffres.
        m = re.match(r"(.+?)-(\d{2})\w?-(.+)\.json$", p.name)
        if not m:
            continue
        for lot in d:
            out.append({
                "nom": p.name,
                "rang": int(m.group(2)),
                "theme_id": lot["theme_id"],
                "enonces": {i["prompt"].strip() for i in lot["items"]},
            })
    return out


def ressemblance(a: list[str], b: list[str]) -> float:
    """Moyenne, pour chaque énoncé de `a`, de son meilleur appariement dans `b`."""
    return sum(max(difflib.SequenceMatcher(None, x, y).ratio() for y in b)
               for x in a) / len(a)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(DB, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    chapitres = {(r["theme_id"], r["position"]): r["id"]
                 for r in conn.execute("SELECT id, theme_id, position FROM chapter")}
    fichiers = lots_de_contenu()

    runs = []
    for r in conn.execute("SELECT id, theme_id FROM exercise_prompt ORDER BY id"):
        ex = [x[0].strip() for x in conn.execute(
            "SELECT prompt FROM exercise WHERE exercise_prompt_id = ?", (r["id"],))]
        runs.append({"id": r["id"], "theme_id": r["theme_id"], "enonces": ex})

    plan: dict[int, tuple[int, str]] = {}
    restants = []
    for run in runs:
        vus = set(run["enonces"])
        cands = [f for f in fichiers
                 if f["theme_id"] == run["theme_id"] and vus and vus <= f["enonces"]]
        rangs = {f["rang"] for f in cands}
        if len(rangs) == 1:
            ch = chapitres.get((run["theme_id"], rangs.pop()))
            if ch:
                plan[run["id"]] = (ch, "contenu" if len(cands) == 1 else "rang")
                continue
        restants.append(run)

    # Les orphelins se rattachent au lancement déjà placé qui leur
    # ressemble le plus, dans le même thème. Deux lots ne peuvent pas
    # partager un chapitre par ce chemin : on retire au fur et à mesure.
    for run in restants:
        voisins = [(o, [x for x in o["enonces"]]) for o in runs
                   if o["id"] in plan and o["theme_id"] == run["theme_id"] and o["enonces"]]
        if not run["enonces"] or not voisins:
            print(f"  lancement {run['id']} : IMPOSSIBLE à rattacher")
            continue
        best, score = max(((o, ressemblance(run["enonces"], e)) for o, e in voisins),
                          key=lambda t: t[1])
        plan[run["id"]] = (plan[best["id"]][0], f"ressemblance {score:.0%} au lancement {best['id']}")

    par_moyen: dict[str, int] = {}
    for _, (_, moyen) in plan.items():
        cle = moyen.split()[0]
        par_moyen[cle] = par_moyen.get(cle, 0) + 1
    print("Rattachements trouvés :", len(plan), "sur", len(runs))
    for k, v in sorted(par_moyen.items()):
        print(f"   {v:4} par {k}")

    print("\nLes rattachements inférés :")
    for rid, (ch, moyen) in sorted(plan.items()):
        if moyen.startswith("ressemblance"):
            print(f"   lancement {rid} → chapitre {ch}   ({moyen})")

    # Un chapitre appartient-il bien au thème de son lancement ?
    faux = [rid for rid, (ch, _) in plan.items()
            if conn.execute("SELECT theme_id FROM chapter WHERE id = ?", (ch,)).fetchone()[0]
            != next(r["theme_id"] for r in runs if r["id"] == rid)]
    print(f"\nContrôle thème du chapitre = thème du lancement : "
          f"{'ÉCHEC sur ' + str(faux) if faux else 'ok sur les ' + str(len(plan))}")
    if faux:
        raise SystemExit(1)

    if args.dry_run:
        print("\n--dry-run : rien n'a été écrit.")
        return

    sauvegarde = DB.with_suffix(DB.suffix + ".avant-rattachement")
    shutil.copy2(DB, sauvegarde)
    print(f"\nsauvegarde : {sauvegarde.name}")

    with conn:
        for rid, (ch, _) in plan.items():
            conn.execute("UPDATE exercise_prompt SET chapter_id = ? WHERE id = ?", (ch, rid))

    reste = conn.execute("SELECT COUNT(*) FROM exercise_prompt WHERE chapter_id IS NULL").fetchone()[0]
    print(f"{len(plan)} lancement(s) rattachés · {reste} encore sans chapitre")
    conn.close()


if __name__ == "__main__":
    main()
