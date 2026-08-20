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
#
# CE REFUS EST DOUBLÉ D'UNE CONSIGNE, et c'est ce qui le rend tenable.
# `sections.py` la pose juste sous l'article : elle énumère les douze
# champs balayés ici et annonce que l'exercice entier saute. Elle avait
# été retirée le 18/08/2026 puis remise le même jour, une fois mesuré
# ce que le refus coûte quand le modèle n'est pas prévenu.
#
# Si les lots rendent moins que leur `count`, c'est ici qu'il faut
# regarder d'abord : restreindre `META` aux seuls `prompt` et `body`
# pour les exercices écrits par `topup` — c'est là que le renvoi rend
# vraiment la question impossible ; ailleurs il est laid, pas bloquant.
META = re.compile(
    r"\b(?:dans ce cours|dans cette le[çc]on|d'apr[èe]s le (?:cours|texte|document)"
    r"|ce (?:cours|document|texte) (?:mentionne|indique|pr[ée]cise|aborde)"
    r"|selon le (?:cours|texte)|le cours (?:dit|parle|porte)"
    r"|in this (?:lesson|course|text)|according to the (?:text|lesson|document)"
    r"|this (?:document|lesson|text) (?:states|mentions|covers)"
    # Ajouté le 14/08/2026. La génération adossée à un article Wikipédia
    # a produit 255 exercices renvoyant à leur source — « The article
    # states that… » — que la règle ci-dessus laissait passer : elle
    # visait « according to the text », pas « the article ». Vérifié
    # sans aucun faux positif sur les 1 960 exercices déjà validés.
    r"|the article\b|the text (?:states|says|mentions|describes|explains|notes)"
    r"|in the (?:text|passage|article)\b"
    r"|according to (?:the|this) (?:article|passage|source)"
    r"|as (?:mentioned|stated|described|noted|explained) (?:in|above)"
    r"|the passage (?:states|says|mentions))\b",
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
             ("ok_line", "ko_line", "exp_title", "exp_text")]
    if any(META.search(t) for t in seen):
        reasons.append("renvoie au support : l'élève n'a pas le cours sous les yeux")

    # LA RÈGLE SUR LES FORMULATIONS INCERTAINES A ÉTÉ RETIRÉE. Elle
    # refusait « probablement », « sans doute », « most likely ». Écrite
    # pour un catalogue de grammaire — une règle d'accord ne se devine
    # pas, elle s'applique — elle n'a plus de sens sur de la culture
    # générale, où « most likely » apparaît légitimement dans une
    # question ouverte. Elle a écarté un exercice correct sur le disque
    # facial de la chouette effraie.

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

    # LES BORNES DE LONGUEUR ONT ÉTÉ RETIRÉES (migration 015). L'énoncé
    # était plafonné à 240 caractères et les options à 60, au nom d'« un
    # écran, pas de scroll ». Ces chiffres décrivaient une app de
    # grammaire dont les questions faisaient cinquante caractères ; le
    # catalogue d'informatique atteignait déjà 240, et le front avait dû
    # baisser sa police de 40 à 20 px pour les encaisser. La borne ne
    # protégeait donc plus rien qu'elle n'eût déjà cédé.
    #
    # Ce qui garde l'écran lisible n'est plus une limite de caractères
    # mais la mise en page : voir `PhaseBlocks.tsx`, qui replie et
    # redimensionne. Un énoncé trop long est désormais un défaut de
    # rédaction, pas une erreur que la machine sait trancher.

    # Pour une réponse courte, `options` liste les graphies acceptées :
    # une seule est un choix légitime, même s'il est risqué.
    if len(options) < 2 and kind != "short_answer":
        reasons.append("moins de deux options")

    # LA RÈGLE DE LONGUEUR RELATIVE A ÉTÉ RETIRÉE. Elle refusait toute
    # bonne réponse dépassant 2,2 fois la longueur moyenne des autres,
    # au motif qu'elle se devine sans rien savoir. Le motif est juste :
    # une bonne réponse détaillée face à trois distracteurs brefs se
    # repère au premier coup d'œil. Mais c'est un défaut de rédaction,
    # pas une erreur que la machine sait trancher — et sur un catalogue
    # de culture générale elle écartait des questions exactes dont la
    # réponse était simplement précise (« In the last segments of the
    # abdomen » contre « In the eyes »).
    #
    # Elle reste vraie comme conseil : écrire les quatre libellés de
    # longueur comparable. Elle n'est plus imposée.

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
  "autonome": true/false,{cle_langue}{cle_intuition}
  "coherent": true/false,
  "motif": "une phrase, vide si tout va bien"}}

  correcte  — la réponse annoncée est-elle juste {correcte_selon} ?
              Vérifie toi-même, ne fais pas confiance.
  unique    — est-elle la SEULE défendable ? Si une autre option se tient
              aussi, réponds false.
  niveau_ok — un élève de {level} peut-il comprendre l'énoncé et y répondre ?
  autonome  — la question se suffit-elle à elle-même, sans document externe ?{critere_langue}{critere_intuition}
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
  "autonome": true/false,{cle_langue}{cle_intuition}
  "coherent": true/false,
  "motif": "one sentence, empty if all is well"}}

  correcte  — is the marked answer right {correcte_selon}? Check for
              yourself, do not take it on trust.{critere_langue}{critere_intuition}
  coherent  — does the marked answer answer exactly what is asked, and does
              no wrong option's feedback describe correct behaviour?"""


# Les deux formulations du critère `correcte`, et le critère de langue
# lui-même, dépendent de ce qu'on enseigne. Voir `judge`.
_SELON = {
    ("langue", "fr"): "selon les règles du français",
    ("langue", "en"): "according to the rules of English",
    ("connaissance", "fr"): "selon le sujet traité",
    ("connaissance", "en"): "for the subject being taught",
}
_CRITERE_LANGUE = {
    "fr": """
  porte_sur_la_langue
            — répondre exige-t-il d'appliquer une règle de français à une
              phrase ou à un mot présents dans l'énoncé ? Si la question
              porte sur ce qu'une leçon contient, sur son plan ou sur son
              champ d'application, réponds false.""",
    "en": """
  porte_sur_la_langue — does answering require applying a rule of English to
              a sentence or word present in the question? If it asks what a
              lesson contains or covers, answer false.""",
}


# LE CRITÈRE D'INTUITION, posé le 19/08/2026 et réservé à la
# « connaissance ». Il double la consigne de `sections.py` : celle-ci
# demande des questions auxquelles on peut RÉFLÉCHIR, celui-ci écarte
# celles auxquelles on ne peut que se souvenir.
#
# Il est écrit étroit, exprès. Le juge de ce fichier refuse par défaut,
# et un critère large fait tomber des lots entiers — c'est déjà arrivé
# avec `porte_sur_la_langue`, qui écartait 100 % d'un catalogue
# technique pour une raison sans rapport avec sa qualité. Celui-ci ne
# refuse QUE le cas franc : aucun chemin de raisonnement, seulement un
# mot à avoir retenu.
_CRITERE_INTUITION = {
    "fr": """
  intuitif  — quelqu'un qui n'a jamais lu de cours sur le sujet pourrait-il
              atteindre la réponse EN RÉFLÉCHISSANT, à partir de ce qu'il a
              déjà observé du monde ? Réponds false si le seul chemin est
              d'avoir retenu un terme, un nom propre, une date ou un record —
              une définition, un « qui a découvert », un « lequel est le
              plus grand ». Un raisonnement même court suffit à répondre
              true : dans le doute, réponds true.""",
    "en": """
  intuitif  — could someone who has never read a lesson on this subject
              reach the answer BY THINKING, from what they have already
              observed of the world? Answer false only if the sole path is
              having memorised a term, a proper name, a date or a record —
              a definition, a "who discovered", a "which is the largest".
              Any reasoning path, however short, means true: when in doubt,
              answer true.""",
}


async def judge(item: dict, lang: str = "fr", level: str = "CM2",
                matiere: str = "langue") -> Verdict:
    """Second avis d'un modèle qui n'a ni le cours ni le contexte.

    `matiere` dit ce qu'on enseigne, et commande deux critères :

      « langue »        le défaut — grammaire, conjugaison, orthographe.
                        Rien ne change pour eux.
      « connaissance »  tout le reste : Git, SQL, l'agile, le code de la
                        route. Le critère `porte_sur_la_langue` DISPARAÎT,
                        du prompt comme du dépouillement.

    Sans cette distinction, le juge refusait la totalité d'un catalogue
    technique : « répondre exige-t-il d'appliquer une règle de français ? »
    ne peut valoir que non sur une question Git, et le refus tombait pour
    une raison sans rapport avec la qualité de l'exercice. Mesuré sur
    huit exercices tirés des douze sujets techniques : 0 accepté.
    """
    options = item.get("options") or []
    correct = item.get("correct_index", 0)
    template = JUDGE_FR if lang == "fr" else JUDGE_EN
    sur_la_langue = matiere == "langue"
    prompt = template.format(
        level=level,
        correcte_selon=_SELON[(matiere if matiere in ("langue", "connaissance")
                               else "langue", "fr" if lang == "fr" else "en")],
        cle_langue='\n  "porte_sur_la_langue": true/false,' if sur_la_langue else "",
        critere_langue=_CRITERE_LANGUE["fr" if lang == "fr" else "en"]
        if sur_la_langue else "",
        cle_intuition='\n  "intuitif": true/false,' if not sur_la_langue else "",
        critere_intuition=_CRITERE_INTUITION["fr" if lang == "fr" else "en"]
        if not sur_la_langue else "",
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
    criteres = [
        ("correcte", "réponse jugée fausse"),
        ("unique", "plusieurs options défendables"),
        ("niveau_ok", "hors de portée du niveau"),
        ("autonome", "dépend d'un document absent"),
        ("coherent", "la réponse ne répond pas à la question posée"),
    ]
    # Le critère n'est réclamé que s'il a été posé : sinon un juge qui ne
    # le renvoie pas — parce qu'on ne le lui a pas demandé — ferait
    # échouer tout le lot sur une clé absente.
    if sur_la_langue:
        criteres.insert(4, ("porte_sur_la_langue", "interroge le cours, pas la langue"))
    else:
        criteres.insert(4, ("intuitif", "se répond de mémoire, pas en réfléchissant"))
    for key, label in criteres:
        if data.get(key) is not True:
            reasons.append(f"{label}{' — ' + motif if motif else ''}")
            motif = ""  # le motif n'est utile qu'une fois
    return Verdict(ok=not reasons, reasons=reasons)


async def review(item: dict, lang: str = "fr", level: str = "CM2",
                 with_judge: bool = True, kind: str | None = None,
                 matiere: str = "langue") -> Verdict:
    rules = check_rules(item, level, kind)
    if not rules.ok:
        return rules              # inutile de payer un juge pour ça
    if not with_judge:
        return rules
    return await judge(item, lang, level, matiere)
