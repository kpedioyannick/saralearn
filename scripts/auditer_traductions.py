#!/usr/bin/env python3
"""Compare chaque carte française à son original anglais, et signale ce qui cloche.

C'EST UNE COMPARAISON, PAS UNE RELECTURE. Juger le français seul revient
à deviner ce qu'il devait dire ; avec l'anglais en regard, la faute saute
aux yeux — « The cut is in a very sensitive area » rendu par « La coupe
est dans une zone très sensible » ne se voit QUE si on a les deux.

Ce qu'on cherche est précis, et c'est la faiblesse connue du moteur :
`deep-translator` traduit CHAMP PAR CHAMP. Un libellé de quatre mots n'a
aucune phrase autour de lui, donc aucun contexte pour choisir entre deux
sens. D'où les trois familles de dégâts :

  · LE SENS — « a paper cut » devenu « on se fait couper du papier »,
    « the metre » devenu « le compteur » ;
  · L'ACCORD — « Elle ralentit / … / Il disparaît » ;
  · LA RÉPONSE ILLISIBLE — le cas grave : quand c'est la bonne option
    qui est cassée, la carte devient injouable.

Le juge ne réécrit rien. Il classe, il cite le champ fautif, et il se
tait sur ce qui va bien : une liste vide est le résultat normal.

    python3 scripts/auditer_traductions.py
    python3 scripts/auditer_traductions.py --limite 20
    python3 scripts/auditer_traductions.py --json rapport.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.db import connection, rows  # noqa: E402
from api.llm import ask  # noqa: E402

LANGUE = "fr"
# Quatre cartes par appel. Au-delà le juge survole ; en dessous on paie
# la consigne trop souvent.
LOT = 4

CONSIGNE = """You compare French translations against their English source.

REPORT ONLY WHAT A FRENCH READER WOULD STOP ON. Not what could be
phrased better — what is WRONG. The empty array is the expected answer,
and it is the answer for most cards.

This is the bar. Report faults of this size and no smaller:

  EN "When you get a paper cut..."  ->  FR "Quand on se fait couper du
  papier..."          the French says someone is cutting paper. REPORT.

  EN "The cut is in a very sensitive area"  ->  FR "La coupe est dans
  une zone tres sensible"     "la coupe" is a haircut. REPORT.

  EN "Sunlight is split into colors"  ->  FR "La lumiere du soleil est
  divisee en couleurs"        correct, merely plain. DO NOT REPORT.

YOU ARE NOT JUDGING WHETHER A STATEMENT IS TRUE. Three options out of
four are FALSE ON PURPOSE — they are the wrong answers. "Light travels
slower than sound" is a wrong answer, and "La lumiere voyage plus
lentement que le son" is its faithful translation. NOT A FAULT.

The only question you answer is: does the French say what the English
says? Never: is it correct physics?

NEVER report any of these:
  - a false statement faithfully translated — that is a wrong option;
  - a wording that could be more elegant;
  - "tu" against "vous" — the app mixes both on purpose;
  - a heavy but correct sentence;
  - a technical term kept in English;
  - anything you have to argue for.

Three kinds of fault, and nothing else:
  "sens"    the French says something different, or absurd
  "accord"  wrong gender or number, so the sentence does not hold
  "langue"  not French — a word-for-word rendering nobody would write

Set "reponse": true ONLY when the fault is on the option marked CORRECT
ANSWER: that card cannot be answered in French any more.

"raison" is at most EIGHT French words. Never deliberate, never write
"however", never change your mind mid-sentence. If you find yourself
weighing, the answer is: do not report it.

{cartes}

Answer with a JSON array, nothing else:
[{{"id": 123, "faute": "sens", "champ": "option 3", "reponse": true,
   "en": "the English text", "fr": "the French text",
   "raison": "huit mots maximum"}}]"""


def _carte(e, opts_en, opts_fr) -> str:
    lignes = [f"--- card {e['id']} ---", f"EN question: {e['prompt_en']}",
              f"FR question: {e['prompt_fr']}"]
    for i, (a, b) in enumerate(zip(opts_en, opts_fr), 1):
        marque = "  <-- CORRECT ANSWER" if i - 1 == e["correct_index"] else ""
        lignes.append(f"EN option {i}: {a.get('label','')}{marque}")
        lignes.append(f"FR option {i}: {b.get('label','')}")
    lignes.append(f"EN explanation: {e['exp_en']}")
    lignes.append(f"FR explanation: {e['exp_fr']}")
    return "\n".join(lignes)


def _tableau(brut: str) -> list[dict]:
    debut, fin = brut.find("["), brut.rfind("]")
    if debut < 0 or fin <= debut:
        return []
    try:
        data = json.loads(brut[debut : fin + 1])
    except Exception:  # noqa: BLE001 — un rendu illisible ne vaut pas un verdict
        return []
    return [x for x in data if isinstance(x, dict) and x.get("id")]


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    with connection() as conn:
        cartes = rows(
            conn,
            "SELECT e.id, e.prompt AS prompt_en, e.options AS opts_en,"
            "       e.correct_index, e.exp_text AS exp_en,"
            "       t.prompt AS prompt_fr, t.options AS opts_fr, t.exp_text AS exp_fr"
            "  FROM exercise e"
            "  JOIN exercise_translation t"
            "    ON t.exercise_id = e.id AND t.lang = ?"
            " WHERE e.state = 'validated'"
            " ORDER BY e.id",
            (LANGUE,),
        )
    if args.limite:
        cartes = cartes[: args.limite]
    print(f"{len(cartes)} cartes à comparer, par lots de {LOT}\n")

    fautes: list[dict] = []
    for depart in range(0, len(cartes), LOT):
        lot = cartes[depart : depart + LOT]
        blocs = []
        for e in lot:
            try:
                blocs.append(_carte(e, json.loads(e["opts_en"]), json.loads(e["opts_fr"])))
            except Exception:  # noqa: BLE001 — une carte illisible se saute
                continue
        if not blocs:
            continue
        try:
            brut = await ask(CONSIGNE.format(cartes="\n\n".join(blocs)))
        except Exception as exc:  # noqa: BLE001 — un juge muet ne bloque pas la ronde
            print(f"  lot {depart // LOT + 1} : sans verdict ({type(exc).__name__})")
            continue
        trouvees = _tableau(brut)
        fautes.extend(trouvees)
        print(f"  lot {depart // LOT + 1}/{(len(cartes) - 1) // LOT + 1} :"
              f" {len(trouvees)} faute(s)   [{depart + len(lot)}/{len(cartes)}]")

    graves = [f for f in fautes if f.get("reponse")]
    print(f"\n{len(fautes)} fautes sur {len(cartes)} cartes"
          f" — dont {len(graves)} sur la BONNE RÉPONSE\n")
    print("par famille :", dict(Counter(f.get("faute", "?") for f in fautes)))

    for titre, liste in (("CARTES INJOUABLES — la bonne réponse est cassée", graves),
                         ("AUTRES FAUTES", [f for f in fautes if not f.get("reponse")])):
        if not liste:
            continue
        print(f"\n=== {titre} ===")
        for f in sorted(liste, key=lambda x: x.get("id", 0)):
            print(f"  [{f.get('id')}] {f.get('faute','?')} · {f.get('champ','?')}"
                  f" — {f.get('raison','')}")
            print(f"        en : {str(f.get('en',''))[:96]}")
            print(f"        fr : {str(f.get('fr',''))[:96]}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(fautes, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"\nrapport écrit dans {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
