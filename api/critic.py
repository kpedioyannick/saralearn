"""Contrôle un exercice avant qu'il n'entre en base.

Deux étages, du moins cher au plus cher, et le premier suffit souvent :

  1. DES RÈGLES. Certaines fautes se voient sans réfléchir : une question
     qui parle du support (« dans ce cours »), deux options identiques,
     une bonne réponse hors bornes, un énoncé trop long pour l'écran.
     Gratuit, certain, immédiat.

  2. UN JUGE. Un second appel au modèle, à qui l'on demande de REFUSER
     par défaut. Il ne relit pas son propre travail — on lui donne
     l'exercice seul, sans le cours ni la réponse attendue, et on lui
     demande si un élève du niveau visé peut y répondre sans ambiguïté.

Le juge n'est pas là pour améliorer, il est là pour écarter. Un exercice
douteux ne doit pas être réécrit, il doit disparaître : le modèle en
produira dix autres pour le prix d'une correction.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field

from .llm import ask

# Renvois au support. L'élève ne voit que la question : elle doit tenir
# debout seule. Ces tournures rendent l'exercice littéralement
# impossible pour qui n'a pas le document sous les yeux.
META = re.compile(
    r"\b(?:dans ce cours|dans cette le[çc]on|d'apr[èe]s le (?:cours|texte|document)"
    r"|ce (?:cours|document|texte) (?:mentionne|indique|pr[ée]cise|aborde)"
    r"|selon le (?:cours|texte)|le cours (?:dit|parle|porte)"
    r"|in this (?:lesson|course|text)|according to the (?:text|lesson|document)"
    r"|this (?:document|lesson|text) (?:states|mentions|covers))\b",
    re.I,
)


# L'incertitude n'a pas sa place : « la règle est probablement la même »
# enseigne à deviner d'après la mise en page d'un document.
HEDGE = re.compile(r"\b(?:probablement|sans doute|il semble que|peut-[êe]tre que"
                   r"|probably|most likely|it seems that)\b", re.I)


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


@dataclass
class Verdict:
    ok: bool
    reasons: list[str] = field(default_factory=list)


# Formules qui déclarent un fragment irréprochable. Sur l'option
# désignée comme fautive, elles trahissent un exercice sans faute.
INNOCENT = re.compile(r"(?:est|sont) (?:correcte?s?|juste|bien [ée]crite?s?)"
                      r"|bien [ée]crit|rien (?:n'est|à corriger)"
                      r"|is correct|correctly (?:written|spelled)", re.I)

# Un trou se marque par « … » et rien d'autre. « ___ », « ... » ou un
# double « …… » sont des trous mal formés : à l'écran ils se voient.
BAD_BLANK = re.compile(r"_{2,}|\.{3,}|…{2,}")


def check_rules(item: dict, level: str | None = None,
                kind: str | None = None) -> Verdict:
    """Ce qui se décide sans modèle. Refuse plutôt que de corriger."""
    reasons: list[str] = []
    prompt = (item.get("prompt") or "").strip()
    body = (item.get("body") or "").strip()
    options = item.get("options") or []
    correct = item.get("correct_index")

    # L'élève lit TOUT : la question, les options, les retours, l'explication.
    # Un renvoi au support n'importe où le laisse devant un texte absent.
    seen = [prompt, body]
    seen += [str(o.get(k, "")) for o in options for k in ("label", "feedback")]
    seen += [str(item.get(k) or "") for k in
             ("ok_line", "ko_line", "exp_title", "exp_text", "exp_tip")]
    if any(META.search(t) for t in seen):
        reasons.append("renvoie au support : l'élève n'a pas le cours sous les yeux")

    # « Probablement » dans un retour : une règle de français ne se devine pas.
    if any(HEDGE.search(t) for t in seen):
        reasons.append("formulation incertaine : une règle ne se devine pas")

    if not isinstance(correct, int) or not 0 <= correct < len(options):
        reasons.append("bonne réponse hors bornes")

    labels = [str(o.get("label", "")).strip() for o in options]
    if any(not l for l in labels):
        reasons.append("option vide")
    # Comparaison SANS `fold` : celui-ci retire les accents, or « ou » et
    # « où », « la » et « là » sont des réponses différentes — c'est même
    # tout l'objet des exercices d'homophones. On ignore seulement la
    # casse et les espaces.
    if len({" ".join(l.split()).casefold() for l in labels}) != len(labels):
        reasons.append("deux options identiques : la bonne réponse est indécidable")

    # « Un écran, pas de scroll » : ces bornes viennent du cahier des
    # charges, pas d'un goût personnel.
    if len(prompt) > 240:
        reasons.append("énoncé trop long pour l'écran")
    if any(len(l) > 60 for l in labels):
        reasons.append("option trop longue pour le bouton")
    # Pour une réponse courte, `options` liste les graphies acceptées :
    # une seule est un choix légitime, même s'il est risqué.
    if len(options) < 2 and kind != "short_answer":
        reasons.append("moins de deux options")

    # Une option nettement plus longue que les autres trahit la bonne
    # réponse : l'élève la repère sans rien savoir. Sans objet pour les
    # deux types où l'on ne choisit pas parmi des propositions : la
    # réponse courte n'en affiche aucune, et le texte à trous mélange
    # les candidats de plusieurs trous dans la même liste.
    if (kind not in ("short_answer", "cloze")
            and len(labels) >= 3 and correct is not None
            and 0 <= correct < len(labels)):
        others = [len(l) for i, l in enumerate(labels) if i != correct]
        if others and len(labels[correct]) > 2.2 * (sum(others) / len(others)):
            reasons.append("la bonne réponse est bien plus longue : elle se devine")

    # Le matériau doit être SOUS LES YEUX de l'élève. « Complète la phrase
    # avec la forme correcte du verbe être » sans phrase n'est pas un
    # exercice : l'explication citait un exemple que personne ne voit.
    enonce = f"{prompt} {body}"
    if BAD_BLANK.search(enonce):
        reasons.append("trou mal formé : le blanc se marque par « … »")
    if kind == "complete" and "…" not in enonce:
        reasons.append("rien à compléter : l'énoncé ne contient aucun trou")
    if kind == "qcm":
        if "…" in enonce:
            reasons.append("un QCM pose une question, il ne se complète pas")
        elif not prompt.rstrip().endswith(("?", "?")):
            reasons.append("l'énoncé d'un QCM est une question")
    # ── Réponse courte ───────────────────────────────────────────────
    # L'élève écrit ; il n'a aucune liste sous les yeux. Les options ne
    # sont donc pas des choix mais les GRAPHIES ACCEPTÉES, et c'est là
    # que se joue la justesse : trop peu, on refuse une réponse correcte.
    if kind == "short_answer":
        if "…" in enonce:
            reasons.append("une réponse courte se rédige, elle ne se complète pas")
        if not prompt.rstrip().endswith(("?", ":", "?")):
            reasons.append("l'énoncé d'une réponse courte est une question")
        canon = labels[correct] if 0 <= (correct or -1) < len(labels) else ""
        if len(canon.split()) > 4:
            reasons.append("réponse attendue trop longue pour une saisie")
        # Une seule graphie acceptée refusera « l'aorte » quand on
        # attendait « aorte ». On exige la variante avec article dès que
        # la réponse commence par une consonne ou une voyelle — donc
        # toujours : c'est le cas le plus fréquent des copies d'élèves.
        if len(labels) < 2:
            reasons.append("une seule graphie acceptée : un élève écrira"
                           " l'article ou le pronom, et sera refusé à tort")

    # ── Texte à trous ────────────────────────────────────────────────
    if kind == "cloze":
        holes = body.count("…")
        if holes < 2:
            reasons.append("un texte à trous en compte au moins deux")
        blanks: dict[int, list[dict]] = {}
        for o in options:
            blanks.setdefault(o.get("blank"), []).append(o)
        if set(blanks) != set(range(holes)):
            reasons.append("les candidats ne correspondent pas aux trous du texte")
        else:
            for i, group in sorted(blanks.items()):
                good = [o for o in group if o.get("correct")]
                if len(good) != 1:
                    reasons.append(f"trou {i + 1} : il faut exactement une bonne réponse")
                elif len(group) < 3:
                    reasons.append(f"trou {i + 1} : moins de trois candidats")
        # Le piège que la règle du designer nomme : une banque commune
        # laisse éliminer par recoupement au lieu de savoir.
        shared = [l for l in {fold(o["label"]) for o in options}
                  if sum(1 for o in options if fold(o["label"]) == l) > 1]
        if shared:
            reasons.append("un même candidat sert à plusieurs trous :"
                           " l'élève élimine au lieu de savoir")

    if kind == "find_error":
        if not body.strip():
            reasons.append("aucune phrase à corriger")
        # Un « trouve l'erreur » dont la bonne réponse est justifiée par
        # « cette forme est correcte » n'a pas d'erreur du tout : l'élève
        # est noté juste pour avoir désigné au hasard. Le retour de la
        # bonne option se contredit, et ça se voit sans rien comprendre
        # au français.
        elif 0 <= (correct or -1) < len(options):
            fb = str(options[correct].get("feedback", ""))
            if fb and INNOCENT.search(fb):
                reasons.append("la bonne réponse est présentée comme correcte :"
                               " il n'y a pas d'erreur à trouver")

    if not (item.get("exp_text") or "").strip():
        reasons.append("explication absente")

    return Verdict(ok=not reasons, reasons=reasons)


JUDGE_FR = """Tu relis un exercice destiné à un élève de {level}. Tu ne l'as pas
écrit et tu n'as pas le cours : tu vois exactement ce que verra l'élève.

Ton rôle est de REFUSER. Dans le doute, refuse. Un exercice écarté ne
coûte rien ; un exercice faux enseigne une erreur.

EXERCICE
{question}
{corps}
Options (avec le retour prévu pour chacune) :
{options}
Réponse annoncée comme correcte : {reponse}
Explication montrée après coup : {explication}

Réponds UNIQUEMENT par un objet JSON, sans texte autour :
{{"correcte": true/false,
  "unique": true/false,
  "niveau_ok": true/false,
  "autonome": true/false,
  "porte_sur_la_langue": true/false,
  "coherent": true/false,
  "motif": "une phrase, vide si tout va bien"}}

  correcte  — la réponse annoncée est-elle juste selon les règles du français ?
              Vérifie toi-même, ne fais pas confiance.
  unique    — est-elle la SEULE défendable ? Si une autre option se tient
              aussi, réponds false.
  niveau_ok — un élève de {level} peut-il comprendre l'énoncé et y répondre ?
  autonome  — la question se suffit-elle à elle-même, sans document externe ?
  porte_sur_la_langue
            — répondre exige-t-il d'appliquer une règle de français à une
              phrase ou à un mot présents dans l'énoncé ? Si la question
              porte sur ce qu'une leçon contient, sur son plan ou sur son
              champ d'application, réponds false.
  coherent  — la bonne réponse répond-elle exactement à ce qui est demandé ?
              Si la question demande une erreur, la bonne réponse doit être
              une erreur. Si le retour d'une option fausse décrit une
              conduite correcte, réponds false."""

JUDGE_EN = """You are reviewing an exercise meant for a {level} learner. You did not
write it and you do not have the lesson: you see exactly what the learner sees.

Your job is to REJECT. When in doubt, reject. A discarded exercise costs
nothing; a wrong one teaches a mistake.

EXERCISE
{question}
{corps}
Options (with the feedback planned for each):
{options}
Answer marked correct: {reponse}
Explanation shown afterwards: {explication}

Reply with a JSON object ONLY, no surrounding text:
{{"correcte": true/false,
  "unique": true/false,
  "niveau_ok": true/false,
  "autonome": true/false,
  "porte_sur_la_langue": true/false,
  "coherent": true/false,
  "motif": "one sentence, empty if all is well"}}

  porte_sur_la_langue — does answering require applying a rule of English to
              a sentence or word present in the question? If it asks what a
              lesson contains or covers, answer false.
  coherent  — does the marked answer answer exactly what is asked, and does
              no wrong option's feedback describe correct behaviour?"""


async def judge(item: dict, lang: str = "fr", level: str = "CM2") -> Verdict:
    """Second avis d'un modèle qui n'a ni le cours ni le contexte."""
    options = item.get("options") or []
    correct = item.get("correct_index", 0)
    template = JUDGE_FR if lang == "fr" else JUDGE_EN
    prompt = template.format(
        level=level,
        question=item.get("prompt", ""),
        corps=(item.get("body") or ""),
        options="\n".join(
            f"- {o.get('label','')}"
            + (f"   [retour : {o['feedback']}]" if o.get("feedback") else "")
            for o in options),
        explication=item.get("exp_text", ""),
        reponse=options[correct].get("label", "") if 0 <= correct < len(options) else "?",
    )

    try:
        raw = await ask(prompt)
    except Exception as exc:  # noqa: BLE001
        # Le juge injoignable ne doit pas laisser passer : on refuse.
        return Verdict(False, [f"juge indisponible ({exc})"])

    # Le juge commente parfois avant ou après son objet. raw_decode lit le
    # premier objet complet et ignore le reste : sans ça on refusait des
    # exercices valables pour un défaut de forme du juge, pas du contenu.
    data = None
    for start in (m.start() for m in re.finditer(r"\{", raw)):
        try:
            data, _ = json.JSONDecoder().raw_decode(raw[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "correcte" in data:
            break
        data = None
    if data is None:
        return Verdict(False, ["réponse du juge illisible"])

    reasons = []
    motif = (data.get("motif") or "").strip()
    for key, label in (
        ("correcte", "réponse jugée fausse"),
        ("unique", "plusieurs options défendables"),
        ("niveau_ok", "hors de portée du niveau"),
        ("autonome", "dépend d'un document absent"),
        ("porte_sur_la_langue", "interroge le cours, pas la langue"),
        ("coherent", "la réponse ne répond pas à la question posée"),
    ):
        if data.get(key) is not True:
            reasons.append(f"{label}{' — ' + motif if motif else ''}")
            motif = ""  # le motif n'est utile qu'une fois
    return Verdict(ok=not reasons, reasons=reasons)


async def review(item: dict, lang: str = "fr", level: str = "CM2",
                 with_judge: bool = True, kind: str | None = None) -> Verdict:
    rules = check_rules(item, level, kind)
    if not rules.ok:
        return rules              # inutile de payer un juge pour ça
    if not with_judge:
        return rules
    return await judge(item, lang, level)
