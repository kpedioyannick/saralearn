"""D'une section d'article, tirer la consigne qui écrira ses exercices.

C'est le prompt du catalogue Wikipédia, et il remplace celui de
`chapters.py`. Les deux ne visent pas la même chose : `chapters.py` a été
écrit pour un chapitre de programme scolaire, sans source — le modèle y
inventait d'abord ses propres consignes, puis rédigeait de mémoire. C'est
la faiblesse connue de l'ancien catalogue : 1 960 exercices écrits sans
qu'aucune source ait été ouverte, et une erreur factuelle trouvée par
hasard sur l'orvet.

Ici la source est là. Une ligne d'`exercise_prompt` porte une section
d'article et son texte ; la consigne se bâtit autour de ce texte, et le
modèle n'a plus à se souvenir de rien.

CE QU'ON DEMANDE, depuis le 19/08/2026 et sur décision du propriétaire :
L'INTUITION, jamais l'accumulation. La consigne du 18/08 réclamait « les
connaissances de base, les définitions à connaître » ; elle notait
elle-même le prix, et le prix a été payé. Relecture de douze exercices
tirés au sort sur les 179 :

  · « What causes atmospheric refraction? » → « Change in air density » :
    on connaît l'étiquette ou on ne la connaît pas ;
  · « What are radio waves? » → « Electromagnetic radiation » : deux mots
    qui se touchent dans n'importe quel texte ;
  · « What did Pierre Gassendi contribute? » : un nom à retenir ;
  · « What is the defining property of circularly polarized light? » :
    comprendre l'énoncé suppose déjà la réponse.

Et les trois qui tenaient — la route brûlante qui semble mouillée, le
Soleil aplati au couchant, la couleur des objets — partaient toutes
d'une chose DÉJÀ VUE.

D'où le test, écrit dans la consigne et repris par le juge : *quelqu'un
qui n'a jamais lu l'article peut-il y arriver EN RÉFLÉCHISSANT ?* Trois
formes autorisées — la scène, la prédiction, la cause — et les
définitions, les noms propres, les dates et les records interdits.

LE VRAI LEVIER EST AILLEURS QUE DANS L'ÉNONCÉ : dans les trois mauvaises
options. Tant qu'elles sont du vocabulaire sans rapport (« Gravity of
Earth / Magnetic fields / Wind speed »), on élimine au flair. Quand
chacune est une croyance que quelqu'un a vraiment — « la Terre est plus
proche du Soleil en juillet » —, se tromper montre à l'élève son propre
modèle, et le `feedback` dit où cette intuition lâche.

LE RENVOI AU SUPPORT EST INTERDIT JUSTE SOUS L'ARTICLE, et non plus
dans le bloc RULES. Le 18/08/2026 la consigne a été retirée deux fois
puis remise une troisième, sous une forme plus forte : elle est
maintenant collée au texte qui la provoque, elle ÉNUMÈRE les douze
champs concernés, et elle dit la sanction.

C'est cette sanction qui la rend nécessaire. `critic.META` cherche ces
tournures dans les douze champs — énoncé, les quatre libellés, les
quatre retours, `ok_line`, `ko_line`, `exp_title`, `exp_text` — et un
seul mot dans un seul d'entre eux fait sauter l'exercice ENTIER, en
silence, sans passer par `draft`. La génération adossée à Wikipédia
avait produit 255 exercices disant « The article states that… » avant
que ce garde-fou existe.

LE CONTRAT DE SORTIE EST ÉCRIT ICI, jamais confié au modèle. Il doit
correspondre au caractère près à ce que `llm.validate` accepte : quatre
options pour un QCM, libellés sous soixante caractères, `exp_text`
obligatoire, `correct_index` entre 0 et 3. Un modèle à qui on demande
d'inventer ce contrat le réinvente à chaque appel, et les exercices sont
écartés en silence à l'insertion.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# La moitié haute : le sujet, sa source, et ce qu'on veut en tirer.
# --------------------------------------------------------------------------

_SUJET = """You are writing multiple-choice questions for a general-knowledge \
app about the created world. The learner is a beginner and has no course in \
front of them — only your question.

THEME:   {theme}
ARTICLE: {chapter}
SUBJECT: {section}

SOURCE — from Wikipedia. Write FROM it. Never copy a sentence of it:
\"\"\"
{content}
\"\"\"

THE LEARNER NEVER SEES THIS ARTICLE — only your question, alone on a
screen. So never point back to it: not "the article", not "according to
the text", not "in the passage", not "as mentioned above", not "the
text states". THIS HOLDS FOR EVERY FIELD YOU WRITE — the question, each
of the four labels, each of the four feedbacks, "ok_line", "ko_line",
"exp_title" and "exp_text". One such phrase anywhere, even in the
feedback of a wrong answer, and the WHOLE exercise is thrown away.

Pick the {count} things in this subject that a beginner would most gain
from UNDERSTANDING, and turn each into one question.

WHAT MAKES A GOOD QUESTION HERE

The goal is INTUITION, not recall. The learner should come out of a
question understanding how something works — not having memorised a
word.

One test, applied to every question you write:

    Could someone who has never read this article reach the answer BY
    THINKING?

If the only path is having memorised a term, a name or a number, the
question is worthless here. Drop it and write another.

WRITE ONLY THESE THREE SHAPES

  1. THE SCENE — start from something the learner has already seen with
     their own eyes, then ask what is going on.
       "On a hot road in summer, what looks like a puddle appears far
        ahead. What is really being seen?"
  2. THE PREDICTION — change one thing, ask what follows.
       "If Earth's axis stood straight up, what would happen to the
        seasons?"
  3. THE CAUSE — why does the familiar thing behave the way it does?
       "Why does a straw look broken where it enters the water?"

SOME SUBJECTS HAVE NO EVERYDAY SCENE. Do not invent a laboratory one.
"You have a coil of wire and a capacitor..." is not a scene the learner
has lived, it is a bench they have never stood at, and it reads harder
than the definition it replaced. When the subject is abstract, use the
CAUSE shape on the nearest thing the learner has actually met, and if
even that fails, ask plainly why the thing works the way it does.

NEVER WRITE THESE

  - "What is X?", "What are X?", "What does X mean?" — a definition is
    answered by pairing two words that sit next to each other in any
    text. It teaches nothing.
  - "Who discovered X?", "In what year...?", "Which X is the largest,
    fastest, first?" — names, dates and records are accumulation.
  - Any question whose own wording already carries the technical term
    that is the answer.

THE THREE WRONG OPTIONS ARE THE HEART OF THE EXERCISE

They are not filler, and they are not other vocabulary. Each wrong
option is A BELIEF SOMEONE ACTUALLY HOLDS — the answer that feels right
and is not. At least one must be the mistake most people make.

  weak   Change in air density / Gravity of Earth / Magnetic fields /
         Wind speed
         -> three unrelated words; the learner eliminates by feel and
            learns nothing.
  strong Earth is closer to the Sun in July / The two halves get the Sun
         at different angles / One half sits in the other's shadow / The
         Sun burns hotter in summer
         -> every one of them is believed by grown adults.

Being wrong must show the learner their own model. That is what the
"feedback" of each wrong option is for: say why that intuition gives
way.

THE FOUR OPTIONS MUST BE FOUR DIFFERENT BELIEFS, AND EXACTLY ONE OF
THEM MAY BE TRUE. This is where writing plausible options turns
dangerous: a wrong option must be a belief that is WRONG, never a second
correct explanation worded differently.

  broken  "Why do geese in a V stay behind and to the side of the bird
           in front?"
             > To catch a free upward push from the bird ahead
               To stay in the leader's slipstream and reduce drag
           Same mechanism said twice. The exercise has no answer, and
           the learner who reasoned well is marked wrong.

Before you finish an exercise, read your three wrong options one by one
and check that each is actually false.

PLAIN WORDS ONLY

No technical term in the question or in the four labels, unless the
question itself makes its meaning plain. The technical name belongs in
"exp_text", where it names what the learner has just understood — the
reward for having reasoned, never the toll to get in.
"""

# --------------------------------------------------------------------------
# Les règles éditoriales, réduites le 18/08/2026 aux deux qui restent.
# Les trois supprimées — « seulement l'œuvre, jamais l'instrument », « le
# fonctionnement avant le record », « aucun renvoi au support » — sont
# retirées SUR DEMANDE DU PROPRIÉTAIRE. La première ne tenait pas : 19
# des 151 exercices la franchissaient, dont les 10 du chapitre 7, parce
# qu'un chapitre entier consacré à une théorie humaine ne peut pas être
# refusé par le prompt. Le tri appartient au choix des chapitres.
#
# ATTENTION : la troisième était doublée d'un refus dur dans
# `critic.py` (« according to the text »). Le refus, lui, est toujours
# là — voir la note au-dessus de `_REGLES` dans critic.py.
#
# Celle qui reste a été mesurée. Sur le thème 245, écrit avec la
# consigne « ne termine jamais sur un chiffre ou un superlatif », le
# défaut tombe à 7 % contre 15 % pour les thèmes écrits sans elle, et
# 30 % pour les plus anciens.
# --------------------------------------------------------------------------

_REGLES = """
RULES

- NEVER END "exp_text" ON A NUMBER OR A SUPERLATIVE. The last sentence
  closes the mechanism the question opened; a spectacular figure in final
  position crushes the answer that was actually asked for.
- Write in English.
"""

# --------------------------------------------------------------------------
# La moitié basse : le contrat de sortie. Aligné sur `llm.validate`.
# --------------------------------------------------------------------------

_CONTRAT = """
Return ONLY a JSON object of the form {{"exercises": [ ... ]}}, holding
{count} exercises, with no text around it. Each exercise:

  "type_question"  always "qcm"
  "prompt"         the question, 200 characters at most, ending with "?".
                   A scene is worth the room it takes; past 240 the
                   question is cut off mid-sentence and lost
  "body"           always null
  "options"        exactly 4 objects, only one of them true:
                     "label"    the choice — A SHORT CLAIM IN EVERYDAY
                                WORDS, what someone might believe, not a
                                bare technical term. 60 CHARACTERS AT
                                MOST, and that limit is hard: a longer
                                label is dropped, and the exercise with
                                it. Count as you write, and say it
                                tersely rather than fully: "Earth is
                                closer to the Sun in July" (34), never
                                "Because the Earth happens to be closer
                                to the Sun during July" (61, lost)
                     "feedback" why THIS choice is wrong — one sentence.
                                On the right answer, why it is right
  "correct_index"  the index of the right answer in "options", 0 to 3
  "image_query"    two to four ordinary words to type into a PHOTO
                   library, to find a photograph that SETS THE SCENE the
                   question puts the learner in front of. Name the place,
                   the object or the animal that would be in the frame:
                   "hot empty road", "glass of water straw", "geese
                   flying formation".
                   NEVER name the phenomenon, the mechanism or the
                   answer — not "mirage", not "refraction", not "light
                   bending". The photo sets the scene, it never shows
                   why. A query holding a word from your explanation is
                   dropped, and the exercise stays without a photo.
                   Use "" when nothing in the question could be
                   photographed — a sound, an idea, a number.
  "ok_title"       PICK ONE OF THESE FIVE, copied exactly, nothing else:
                     "Exactly."  "That's it."  "Well seen."
                     "Correct."  "Well reasoned."
  "ok_line"        one sentence confirming the reasoning
  "ko_title"       PICK ONE OF THESE FIVE, copied exactly, nothing else.
                   Choose the one that fits the mistake:
                     "Not quite."  "Almost."  "Think again."
                     "The common trap."  "Not this time."
                   Use "The common trap." when the learner picked the
                   belief most people hold — the one you wrote as the
                   widespread mistake. Never let a title give the answer
                   away: it reacts to the attempt, the explanation comes
                   after
  "ko_line"        one sentence saying where the mistake creeps in
  "exp_title"      the title of the explanation
  "exp_text"       the explanation — required. It closes the mechanism
                   the question opened, starting from the scene the
                   learner was shown. This is where the technical name
                   finally appears, to name what has just been
                   understood. Clear, sharp, precise. Neither too long
                   nor too short

Two options cannot have the same label. No commentary, no code fence.

THE TWO TITLES ARE A CLOSED LIST, and inventing one is a mistake even
when it is clever. They are furniture, not content: the thinking belongs
in "ok_line", "ko_line" and "exp_text". Left free, they produced seventy
different forms over one hundred and seventy-three cards — "Bouncer!",
"Space kitchen", "Goldilocks planet" — and titles that shame, which the
rules have never allowed. They are also one or two words long, which is
exactly what a translator cannot handle: "Right!" came out as the French
word for the direction, on thirty-seven cards.
"""


_SUJET_ARTICLE = """You are writing multiple-choice questions for a general-knowledge \
app about the created world. The learner is a beginner and has no course in \
front of them — only your question.

THEME:   {theme}
ARTICLE: {chapter}

SOURCE — the whole article, from Wikipedia. Write FROM it. Never copy a
sentence of it:
\"\"\"
{content}
\"\"\"

THE LEARNER NEVER SEES THIS ARTICLE — only your question, alone on a
screen. So never point back to it: not "the article", not "according to
the text", not "in the passage", not "as mentioned above", not "the
text states". THIS HOLDS FOR EVERY FIELD YOU WRITE — the question, each
of the four labels, each of the four feedbacks, "ok_line", "ko_line",
"exp_title" and "exp_text". One such phrase anywhere, even in the
feedback of a wrong answer, and the WHOLE exercise is thrown away.

Pick the {count} things in this article that a beginner would most gain
from UNDERSTANDING, and turn each into one question. Never ask the same
question twice, in any wording, and never let two questions contradict
each other.

WHAT MAKES A GOOD QUESTION HERE

The goal is INTUITION, not recall. The learner should come out of a
question understanding how something works — not having memorised a
word.

One test, applied to every question you write:

    Could someone who has never read this article reach the answer BY
    THINKING?

If the only path is having memorised a term, a name or a number, the
question is worthless here. Drop it and write another.

WRITE ONLY THESE THREE SHAPES

  1. THE SCENE — start from something the learner has already seen with
     their own eyes, then ask what is going on.
       "On a hot road in summer, what looks like a puddle appears far
        ahead. What is really being seen?"
  2. THE PREDICTION — change one thing, ask what follows.
       "If Earth's axis stood straight up, what would happen to the
        seasons?"
  3. THE CAUSE — why does the familiar thing behave the way it does?
       "Why does a straw look broken where it enters the water?"

SOME SUBJECTS HAVE NO EVERYDAY SCENE. Do not invent a laboratory one.
"You have a coil of wire and a capacitor..." is not a scene the learner
has lived, it is a bench they have never stood at, and it reads harder
than the definition it replaced. When the subject is abstract, use the
CAUSE shape on the nearest thing the learner has actually met, and if
even that fails, ask plainly why the thing works the way it does.

NEVER WRITE THESE

  - "What is X?", "What are X?", "What does X mean?" — a definition is
    answered by pairing two words that sit next to each other in any
    text. It teaches nothing.
  - "Who discovered X?", "In what year...?", "Which X is the largest,
    fastest, first?" — names, dates and records are accumulation.
  - Any question whose own wording already carries the technical term
    that is the answer.

THE THREE WRONG OPTIONS ARE THE HEART OF THE EXERCISE

They are not filler, and they are not other vocabulary. Each wrong
option is A BELIEF SOMEONE ACTUALLY HOLDS — the answer that feels right
and is not. At least one must be the mistake most people make.

  weak   Change in air density / Gravity of Earth / Magnetic fields /
         Wind speed
         -> three unrelated words; the learner eliminates by feel and
            learns nothing.
  strong Earth is closer to the Sun in July / The two halves get the Sun
         at different angles / One half sits in the other's shadow / The
         Sun burns hotter in summer
         -> every one of them is believed by grown adults.

Being wrong must show the learner their own model. That is what the
"feedback" of each wrong option is for: say why that intuition gives
way.

THE FOUR OPTIONS MUST BE FOUR DIFFERENT BELIEFS, AND EXACTLY ONE OF
THEM MAY BE TRUE. This is where writing plausible options turns
dangerous: a wrong option must be a belief that is WRONG, never a second
correct explanation worded differently.

  broken  "Why do geese in a V stay behind and to the side of the bird
           in front?"
             > To catch a free upward push from the bird ahead
               To stay in the leader's slipstream and reduce drag
           Same mechanism said twice. The exercise has no answer, and
           the learner who reasoned well is marked wrong.

Before you finish an exercise, read your three wrong options one by one
and check that each is actually false.

PLAIN WORDS ONLY

No technical term in the question or in the four labels, unless the
question itself makes its meaning plain. The technical name belongs in
"exp_text", where it names what the learner has just understood — the
reward for having reasoned, never the toll to get in.
"""

# Ce que les questions déjà en ligne ont demandé. Sans ça, une recharge
# repose la même question reformulée : c'est le défaut qui avait fait
# ajouter la comparaison des énoncés dans `topup.py`, et le dire au
# modèle coûte moins cher que de jeter ce qu'il rend.
_DEJA = """
ALREADY ASKED — do not ask any of these again, in any wording:
{liste}
"""


def article(
    theme: str,
    chapter: str,
    contenu: str,
    count: int = 10,
    deja: list[str] | None = None,
) -> str:
    """La consigne pour un ARTICLE ENTIER, et non pour une seule section.

    Mesuré sur « Bird flight », mêmes règles et même contrat de sortie,
    seule la source changeant :

        une consigne par section  →  4 questions faibles sur 11
        l'article entier          →  1 sur 11

    La cause est mécanique. Par section, le nombre de questions est imposé
    par la LONGUEUR du texte — la section « Wings » fait 1 670 caractères,
    donc cinq questions. Mais elle n'a pas cinq mécanismes à enseigner :
    le modèle remplit avec le nom des trois os de l'aile et les griffes du
    poussin de hoatzin. Sur l'article entier, personne n'impose de quota
    paragraphe par paragraphe, et le modèle choisit.

    Et c'est neuf fois moins d'appels : un par chapitre au lieu d'un par
    section.
    """
    haut = _SUJET_ARTICLE.format(
        theme=theme,
        chapter=chapter,
        content=(contenu or "").strip(),
        count=count,
    )
    vu = ""
    if deja:
        vu = _DEJA.format(liste="\n".join(f"  · {q}" for q in deja[:60]))
    return f"{haut}{vu}{_REGLES}{_CONTRAT.format(count=count)}".strip()


def consigne(
    theme: str,
    chapter: str,
    section: str,
    content: str,
    count: int = 10,
) -> str:
    """La consigne complète pour une section, prête à partir au modèle.

    C'est elle qu'on écrit dans `exercise_prompt.rendered_prompt`, et
    c'est par elle qu'on remonte d'un exercice douteux au texte exact
    qui l'a commandé.
    """
    haut = _SUJET.format(
        theme=theme,
        chapter=chapter,
        section=section,
        content=(content or "").strip(),
        count=count,
    )
    return f"{haut}{_REGLES}{_CONTRAT.format(count=count)}".strip()
