"""Le second appel du pipeline : d'un chapitre, tirer son prompt.

Le programme est validé. Pour chaque chapitre, le modèle choisit le type
de question qui lui convient, écrit les consignes pédagogiques, et donne
un exemple de ce qu'on obtiendra.

LE PROMPT EST COMPOSÉ, PAS RECOPIÉ. Le modèle n'écrit que la moitié
haute — ce que le chapitre demande d'apprendre, comment interroger
dessus. La moitié basse, le contrat de sortie, est écrite ici et ne lui
est jamais confiée : elle doit correspondre au caractère près à ce que
`llm.validate` accepte. Quatre options pour un QCM, `exp_text`
obligatoire, libellés sous soixante caractères — un modèle à qui on
demande d'inventer ce contrat le réinvente à chaque appel, et les
exercices sont écartés en silence à l'insertion.

C'est ce qui distingue ce prompt d'un gabarit de la table `prompt` : le
gabarit est un texte figé où l'on substitue le cours, celui-ci est écrit
pour un chapitre précis puis scellé dans un contrat commun.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .config import CHAPTER_TYPES
from .llm import GenerationError, extract_json_object

# Le modèle choisit parmi ces types, et pas les cinq du CHECK de
# `chapter`. `cloze` en est écarté : `llm.validate` ne conserve que le
# libellé de chaque option et laisse tomber `blank` et `correct`, si bien
# qu'un texte à trous produit par cette voie perd le lien entre ses
# candidats et ses trous. Les neuf en base viennent des scripts, qui
# passent par `api/critic.py`. À rouvrir quand `validate` saura les lire.
# Les types réellement proposés au modèle viennent de la configuration :
# le propriétaire les restreint sans toucher au code. On garde ici la
# liste des types que ce module SAIT décrire, pour refuser tout de suite
# un réglage qui demanderait l'impossible.
KNOWN_TYPES = ("qcm", "complete", "find_error", "short_answer")

TYPES = tuple(t for t in CHAPTER_TYPES if t in KNOWN_TYPES) or ("qcm",)

LIMITS = {"instructions": 4000, "example_prompt": 240, "example_exp": 600}


# --------------------------------------------------------------------------
# Le contrat de sortie — écrit ici, jamais demandé au modèle
# --------------------------------------------------------------------------

_COMMUN = """
Rends UNIQUEMENT un tableau JSON de {{count}} objets, sans texte autour.
Chaque objet :

  "prompt"     la question, {{max_prompt}} caractères au plus
  "options"    {{options}}
  "correct_index" l'indice de la bonne réponse dans "options", à partir de 0
  "ok_title"   deux ou trois mots de félicitation
  "ok_line"    une phrase qui confirme le raisonnement
  "ko_title"   deux ou trois mots, jamais culpabilisants
  "ko_line"    une phrase qui dit où l'erreur se glisse
  "exp_title"  le titre de l'explication
  "exp_text"   l'explication de la solution — obligatoire. Claire, nette,
               précise : juste ce qu'il faut pour comprendre pourquoi
               c'est la bonne réponse. Ni trop long, ni trop court.
               L'objectif est que l'élève APPRENNE quelque chose{{extra}}

Aucun libellé d'option ne dépasse 60 caractères. Deux options ne peuvent
pas être identiques. Pas de commentaire, pas de bloc de code.
"""

_OPTIONS = {
    "qcm": "exactement 4 propositions, une seule vraie",
    "complete": "exactement 4 formes possibles pour le trou, une seule correcte",
    "find_error": "exactement 4 fragments du texte, celui qui est fautif et trois corrects",
    "short_answer": (
        "les graphies acceptées de la réponse, de 2 à 4 — l'élève écrit sa "
        "réponse, on la compare à cette liste après avoir retiré casse, "
        "accents et ponctuation. Liste les variantes plausibles (avec et "
        "sans article, singulier et pluriel si les deux se disent)"
    ),
}

_EXTRA = {
    "find_error": '\n  "body"       le texte où se cache l\'erreur — obligatoire pour ce type',
    "complete": (
        '\n  "body"       la phrase avec le trou, marqué par …'
        "\n\nLE TROU EST LE SEUL CARACTÈRE … (U+2026), employé une fois et une "
        'seule dans "body". Jamais « ___ », jamais trois points « ... », '
        "jamais un « …… » doublé. Ceux-là sont écartés d'office, et un "
        'exercice « complete » dont le "body" ne porte aucun trou l\'est '
        "aussi — il n'y a alors rien à compléter, et l'élève voit une phrase "
        "sans blanc."
    ),
    "short_answer": (
        "\n\nPour ce type, \"correct_index\" vaut 0 : il désigne la graphie "
        "canonique, celle qu'on affichera en correction."
    ),
}


# --------------------------------------------------------------------------
# Le même contrat, en anglais
#
# Il ne s'agit pas d'une commodité. Le prompt final est fait de deux
# moitiés : les consignes, écrites par le modèle dans la langue du
# chapitre, et ce contrat. Laisser le contrat en français sous des
# consignes anglaises, c'est donner au modèle deux langues et lui
# laisser trancher — et il tranche pour celle des instructions de
# format, qui sont les plus impératives. Une connaissance anglaise
# produisait des exercices français : questions, félicitations,
# explications, tout.
#
# Les contraintes sont les mêmes AU CARACTÈRE PRÈS que la version
# française, parce que c'est le même `llm.validate` qui les fait
# respecter : quatre options, `exp_text` obligatoire, libellés sous
# soixante caractères.
# --------------------------------------------------------------------------

_COMMUN_EN = """
Return ONLY a JSON array of {{count}} objects, with no text around it.
Each object:

  "prompt"     the question, {{max_prompt}} characters at most
  "options"    {{options}}
  "correct_index" the index of the right answer in "options", starting at 0
  "ok_title"   two or three words of praise
  "ok_line"    one sentence confirming the reasoning
  "ko_title"   two or three words, never shaming
  "ko_line"    one sentence saying where the mistake creeps in
  "exp_title"  the title of the explanation
  "exp_text"   the explanation of the solution — required. Clear, sharp,
               precise: just what it takes to understand why this is the
               right answer. Neither too long nor too short. The goal is
               that the reader LEARNS something{{extra}}

Option labels are SHORT FRAGMENTS, never sentences: a command, a flag, a
term, a value, a line of output. If an option needs a full sentence to
make sense, the context belongs in "prompt" and not in the choices — ask
"which command does X?" rather than "when would you use X?". No label may
exceed 60 characters; a longer one is dropped and the exercise with it.

When the answer is CODE and the full statement would not fit — an SQL
clause, a long command — put the fixed part in "body" and let the options
carry only the part that changes. Offer "ON DELETE CASCADE" against
"ON DELETE SET NULL", not two whole FOREIGN KEY lines that differ by
three words. Sixty characters is about two lines on the answer button;
past that the exercise never reaches a learner.

Two options cannot be identical. No commentary, no code fence.
"""

_OPTIONS_EN = {
    "qcm": "exactly 4 choices, only one of them true",
    "complete": "exactly 4 possible forms for the blank, only one correct",
    "find_error": (
        "exactly 4 fragments of the text, the faulty one and three correct ones"
    ),
    "short_answer": (
        "the accepted spellings of the answer, 2 to 4 — the learner types "
        "their answer and it is compared against this list once case, "
        "accents and punctuation have been stripped. List the plausible "
        "variants (with and without an article, singular and plural when "
        "both are said)"
    ),
}

_EXTRA_EN = {
    "find_error": '\n  "body"       the text hiding the error — required for this type',
    "complete": (
        '\n  "body"       the sentence with the blank, marked by …'
        "\n\nTHE BLANK IS THE SINGLE CHARACTER … (U+2026), used exactly once "
        'inside "body". Never "___", never three dots "...", never a doubled '
        '"……". Those are rejected on sight, and so is a complete exercise '
        'whose "body" carries no blank at all — there is then nothing to '
        "complete, and the learner sees a question with no gap in it."
    ),
    "short_answer": (
        '\n\nFor this type, "correct_index" is 0: it points to the canonical '
        "spelling, the one shown in the correction."
    ),
}

_CONTRACTS = {
    "fr": (_COMMUN, _OPTIONS, _EXTRA),
    "en": (_COMMUN_EN, _OPTIONS_EN, _EXTRA_EN),
}


def contract(type_question: str, count: int = 10, lang: str = "fr") -> str:
    """La moitié basse du prompt, identique pour tous les chapitres d'un type."""
    commun, options, extra = _CONTRACTS.get(lang, _CONTRACTS["fr"])
    out = commun
    for key, value in {
        "count": count,
        "max_prompt": 240,
        "options": options.get(type_question, options["qcm"]),
        "extra": extra.get(type_question, ""),
    }.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out.strip()


# --------------------------------------------------------------------------
# La demande faite au modèle
# --------------------------------------------------------------------------

TEMPLATE = """Tu prépares la fabrication d'exercices pour un chapitre.

CONNAISSANCE : {{theme}}
CHAPITRE {{position}} : {{chapter}}
CE QU'IL COUVRE : {{description}}

Rends UNIQUEMENT un objet JSON, sans texte autour :

{
  "type_question": "qcm",
  "instructions": "les consignes de rédaction pour ce chapitre",
  "example": {
    "prompt": "une question d'exemple",
    "options": ["…", "…", "…", "…"],
    "correct_index": 0,
    "exp_text": "l'explication de cet exemple"
  }
}

RÈGLES :
- Écris en {{langue}}.
{{typeguide}}
- "instructions" : ce que le rédacteur doit couvrir et éviter pour CE
  chapitre — les notions à balayer, les pièges classiques des élèves, le
  niveau SCOLAIRE visé, ce qui ne doit pas être demandé parce que c'est
  le sujet d'un autre chapitre. N'y mets AUCUNE consigne de format JSON,
  et AUCUN niveau cognitif : ne dis pas si les questions doivent faire
  se rappeler, comprendre, appliquer ou analyser. Ces deux consignes
  sont ajoutées ensuite, et une phrase comme « teste la reconnaissance »
  contredirait celle qui, au lancement suivant, demandera d'appliquer.
  Écris-les à la deuxième personne, comme des instructions à quelqu'un.
- "example" : un exercice réel, pas un gabarit — l'utilisateur le lira
  pour décider s'il lance la fabrication.{{examplenote}}
{{mixrule}}- Pas de commentaire, pas de bloc de code, rien après l'objet JSON.
"""

# --------------------------------------------------------------------------
# Le bloc de consignes sur le type, construit d'après les types autorisés.
#
# Il ne suffit pas de restreindre `TYPES` : le gabarit disait aussi
# « prends short_answer dès qu'un chapitre demande de produire » et
# « un bon programme mélange les types ». Laissées en place avec un seul
# type permis, ces deux phrases demandent au modèle l'inverse de ce qu'on
# autorise — il rendrait un type refusé par `parse`, et le chapitre
# tomberait en erreur.
# --------------------------------------------------------------------------

_TYPE_DESC = {
    "qcm": "qcm           une notion se reconnaît parmi quatre propositions",
    "complete": "complete      une forme précise remplit un trou dans une phrase",
    "find_error": "find_error    un texte contient une faute à désigner",
    "short_answer": "short_answer  l'élève ÉCRIT la réponse, qui tient en un mot",
}

_PRODUIRE = """
  La question à te poser : le chapitre demande-t-il de RECONNAÎTRE ou de
  PRODUIRE ? Reconnaître « allées » parmi quatre formes n'est pas savoir
  l'écrire. Dès qu'un chapitre demande de produire une forme — un verbe
  conjugué, une graphie, un mot-clé, un résultat — prends short_answer,
  c'est le seul type qui l'éprouve vraiment.

  Sa limite, en revanche, est stricte : la réponse est comparée à une
  liste de graphies acceptées, après normalisation de la casse, des
  accents et de la ponctuation. Il ne peut donc PAS servir à faire
  écrire une phrase, une explication ou du code — il n'existe pas de
  liste finie de bonnes réponses, et tout serait compté faux. Si la
  réponse attendue ne tient pas en un mot ou deux, prends un autre type."""


def type_guide(types: tuple[str, ...] = TYPES) -> str:
    """Les consignes de choix du type, réduites à ce qui est permis."""
    lines = "\n".join("    " + _TYPE_DESC[t] for t in types if t in _TYPE_DESC)
    if len(types) == 1:
        only = types[0]
        return (
            f'- "type_question" : toujours "{only}", sans exception. C\'est le\n'
            f"  seul type accepté pour ce programme.\n{lines}"
        )
    guide = (
        '- "type_question" : un seul parmi ' + ", ".join(types) + ". Choisis celui\n"
        "  qui éprouve vraiment ce chapitre.\n" + lines
    )
    if "short_answer" in types:
        guide += "\n" + _PRODUIRE
    return guide


def example_note(types: tuple[str, ...] = TYPES) -> str:
    """La note sur `options` ne vaut que si short_answer est permis.

    Elle explique que pour ce type, `options` porte les graphies
    acceptées et non des choix. Laissée en place sans le type, elle
    décrit un cas qui ne peut pas se produire — du bruit dans un prompt
    déjà long.
    """
    if "short_answer" not in types:
        return ""
    return (
        ' Pour short_answer, "options"\n'
        "  ne contient pas des choix mais les GRAPHIES ACCEPTÉES de la réponse,\n"
        '  deux à quatre : par exemple ["chantait", "il chantait"] pour une forme\n'
        '  conjuguée. "correct_index" vaut alors 0.'
    )


def mix_rule(types: tuple[str, ...] = TYPES) -> str:
    """La règle de mélange n'a de sens qu'à partir de deux types."""
    if len(types) < 2:
        return ""
    return (
        "- Un bon programme mélange les types : un chapitre qui fait produire,\n"
        "  un qui fait reconnaître, un qui fait corriger. Cinq chapitres du\n"
        "  même type interrogent cinq fois le même geste.\n"
    )


LANGUES = {"fr": "français", "en": "anglais"}


def build_prompt(
    theme_title: str,
    chapter_title: str,
    chapter_description: str | None,
    position: int,
    lang: str = "fr",
) -> str:
    out = TEMPLATE
    for key, value in {
        "theme": theme_title,
        "chapter": chapter_title,
        "description": chapter_description or "(non précisé)",
        "position": position,
        "typeguide": type_guide(),
        "mixrule": mix_rule(),
        "examplenote": example_note(),
        "langue": LANGUES.get(lang, "français"),
        "types": ", ".join(TYPES),
    }.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out


# --------------------------------------------------------------------------
# Lecture de la réponse
# --------------------------------------------------------------------------


def _clean(value: Any, field: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    limit = LIMITS.get(field)
    return text[:limit] if limit else text


def _example(data: Any) -> dict | None:
    """L'exemple est montré, pas inséré — on le nettoie sans le refuser.

    Un exemple bancal ne doit pas faire échouer le chapitre : le prompt,
    lui, est utilisable. L'utilisateur verra simplement le chapitre sans
    aperçu.
    """
    if not isinstance(data, dict):
        return None
    prompt = _clean(data.get("prompt"), "example_prompt")
    if not prompt:
        return None

    options: list[str] = []
    for opt in data.get("options") or []:
        label = (opt.get("label") if isinstance(opt, dict) else opt) or ""
        label = str(label).strip()
        if label and label not in options:
            options.append(label)

    correct = data.get("correct_index")
    if not isinstance(correct, int) or not 0 <= correct < max(1, len(options)):
        correct = 0

    return {
        "prompt": prompt,
        "options": options,
        "correct_index": correct,
        "exp_text": _clean(data.get("exp_text"), "example_exp"),
    }


def parse(raw: str) -> dict:
    """Rend le type, les consignes et l'exemple. Lève si le prompt est inutilisable."""
    data = extract_json_object(raw)

    type_question = str(data.get("type_question") or "").strip().lower()
    if type_question not in TYPES:
        raise GenerationError(
            f"Type de question inattendu : {type_question!r}. "
            f"Attendu l'un de {', '.join(TYPES)}."
        )

    instructions = _clean(data.get("instructions"), "instructions")
    # Sous deux cents caractères, ce ne sont pas des consignes mais un
    # titre redit : le rédacteur n'aurait rien de plus que le nom du
    # chapitre, et produirait les mêmes questions pour tous.
    if not instructions or len(instructions) < 200:
        raise GenerationError(
            "Consignes trop maigres pour écrire des exercices distincts."
        )

    example = _example(data.get("example"))

    # Un exemple de short_answer sans graphies acceptées, ou dont la
    # réponse fait une phrase, montre que le modèle a mal saisi le type.
    # On écarte l'APERÇU, pas le chapitre : le prompt composé explique le
    # contrat au rédacteur, et c'est lui qui écrira les exercices. Faire
    # échouer le chapitre ici coûtait un appel entier et de bonnes
    # consignes pour une vignette ratée — huit chapitres sur dix perdus
    # au premier essai.
    if type_question == "short_answer" and example:
        labels = example["options"]
        if len(labels) < 2 or any(len(label) > 60 for label in labels):
            example = None

    return {
        "type_question": type_question,
        "instructions": instructions,
        "example": example,
    }


def compose(
    instructions: str, type_question: str, count: int = 10, lang: str = "fr"
) -> str:
    """Le texte final, celui qui sera envoyé pour écrire les exercices.

    SANS NIVEAU DE BLOOM, et c'est délibéré. Ce texte est composé une
    fois, relu, parfois corrigé, puis servi à tous les lancements du
    chapitre. Y figer un niveau le rendrait bon pour un lot et faux pour
    les trois autres.
    """
    return f"{instructions.strip()}\n\n{contract(type_question, count, lang)}\n"


# Les deux ouvertures de contrat, où `recount` réécrit le nombre. Les
# reconnaître dans les deux langues évite d'avoir à deviner dans laquelle
# le prompt a été composé — un prompt relu et corrigé à la main ne dit
# pas la sienne.
_COUNT_RE = re.compile(
    r"^(Rends UNIQUEMENT un tableau JSON de|Return ONLY a JSON array of)(\s+)\d+",
    re.M,
)


def with_note(prompt: str, note: str | None) -> str:
    """Glisse une consigne supplémentaire juste avant le contrat.

    Charnière du contrat, et pour la même raison : le contrat
    reste en dernier, parce qu'un modèle suit d'autant mieux une règle de
    format qu'elle est la dernière lue.

    Sert à corriger le tir sur un chapitre DÉJÀ COMPOSÉ, sans recomposer
    son prompt — ce qui effacerait les corrections faites à la main et
    ferait repayer un appel pour rendre autre chose. Le cas qui l'a
    motivée : deux chapitres SQL dont chaque option est une clause
    entière, donc au-dessus des soixante caractères que le bouton
    accepte, et qui revenaient vides à chaque tentative.
    """
    if not note or not note.strip():
        return prompt
    note = note.strip()
    found = _COUNT_RE.search(prompt)
    if found is None:
        return f"{prompt.rstrip()}\n\n{note}\n"
    head, tail = prompt[: found.start()].rstrip(), prompt[found.start() :]
    return f"{head}\n\n{note}\n\n{tail}"


def recount(prompt: str, count: int) -> str:
    """Réécrit le nombre d'exercices demandé dans un prompt déjà composé.

    Le volume se choisit à l'écran, après que le prompt a été écrit et
    parfois corrigé à la main. Réécrire seulement ce nombre évite de
    recomposer le prompt, ce qui effacerait les corrections de l'auteur.
    """
    return _COUNT_RE.sub(
        lambda m: f"{m.group(1)}{m.group(2)}{count}", prompt, count=1
    )
