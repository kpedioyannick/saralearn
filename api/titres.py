"""Les titres des deux écrans de réponse — un jeu fermé, pas de la prose.

`ok_title` et `ko_title` sont l'en-tête de l'écran qui suit la réponse :
deux ou trois mots, au-dessus de la ligne qui explique. C'est du mobilier,
pas du contenu — la pensée est dans `ok_line`, `ko_line` et `exp_text`.

Laissés libres, ils ont donné **soixante-dix formes pour cent
soixante-treize cartes**, dont « Bouncer! », « Space kitchen »,
« Goldilocks planet » et « Stuck on polarization » en titre de RÉUSSITE.
Et des titres qui rabaissent — « Wrong », « Nope », « Misstep » — alors
que la consigne l'interdit depuis toujours.

MAIS LE VRAI DÉGÂT ÉTAIT DANS LA TRADUCTION, et il était invisible côté
anglais. Ces champs font UN OU DEUX MOTS : le traducteur les prend seuls,
sans phrase autour, et n'a rien pour choisir le bon sens.

    Right!    ->  « Droite ! »   (la direction — sur 37 cartes)
    Close     ->  « Fermer »     (le verbe)
    Careful   ->  « Prudent »
    Try again ->  « Essayer à nouveau »

« Droite ! » s'affichait sur une carte réussie sur cinq, et
`lib/spoken.ts` le LISAIT À VOIX HAUTE. C'est le cas d'école où une table
bat un traducteur : le jeu est fini, connu, et il tient en dix lignes.

D'où ce fichier. Le modèle CHOISIT dans la liste au lieu de rédiger — voir
le contrat de sortie dans `sections.py` — et `traduction.py` lit la table
au lieu d'appeler Google. Ce qui n'y figure pas repart chez le traducteur :
la table n'est pas un mur, c'est un raccourci sûr.

La voix est celle du front (`src/data/content.ts`) : sobre, un point, pas
de point d'exclamation.
"""

from __future__ import annotations

import re

# Ce que le modèle a le droit d'écrire, et la seule chose que la table
# ait à traduire. Cinq de chaque : assez pour que le titre colle à la
# situation — « C'est l'inverse. » quand l'élève a pris le contraire —
# et assez peu pour que la voix de l'app reste la même d'une carte à
# l'autre.
OK = (
    "Exactly.",
    "That's it.",
    "Well seen.",
    "Correct.",
    "Well reasoned.",
)

KO = (
    "Not quite.",
    "Almost.",
    # Celui-ci porte quelque chose que les quatre autres n'ont pas : il
    # dit à l'élève que sa réponse est l'erreur que TOUT LE MONDE fait.
    # C'est le pendant exact de la consigne d'écriture, qui demande que
    # chaque mauvaise option soit une croyance réelle — se tromper doit
    # montrer son propre modèle, et savoir qu'on partage l'erreur vaut
    # mieux que se croire seul à côté de la plaque.
    #
    # Il remplace « The other way round. », retiré : sur quatre options,
    # « c'est l'inverse » désignait presque la bonne case avant même
    # l'explication, sans même en désigner une seule. Et c'était le seul
    # des cinq à AFFIRMER quelque chose sur le contenu au lieu de réagir
    # à la tentative — mal choisi, il contredisait l'explication juste
    # en dessous.
    "The common trap.",
    "Think again.",
    "Not this time.",
)

# La table, sur une clé sans casse ni ponctuation : « Exactly! »,
# « exactly » et « Exactly. » sont le même titre.
#
# LES CLÉS SE LISENT APRÈS `cle()`, apostrophe comprise : celle-ci
# devient une ESPACE, donc « That's it. » a pour clé « that s it » et non
# « thats it ». Écrite collée, l'entrée ne se trouvait jamais et vingt
# cartes gardaient leur titre français d'origine — « Mirage maîtrisé ! »,
# « Étaler! ».
FR = {
    "exactly": "Exact.",
    "that s it": "C'est ça.",
    "well seen": "Bien vu.",
    "correct": "Juste.",
    "well reasoned": "Bien raisonné.",
    "not quite": "Pas tout à fait.",
    "almost": "Presque.",
    # Sans adresse directe, comme les quatre autres : l'app hésite
    # entre le tutoiement et le vouvoiement (46 « vous » contre 27 « tu »
    # dans `i18n.ts`), et ce n'est pas un titre de deux mots qui doit
    # trancher.
    "the common trap": "Le piège classique.",
    "think again": "À reconsidérer.",
    "not this time": "Pas cette fois.",
}


def cle(titre: str) -> str:
    """La forme comparable d'un titre : sans casse, sans ponctuation."""
    return re.sub(r"[^a-z0-9 ]+", " ", (titre or "").lower()).strip()


def traduire(titre: str, lang: str) -> str | None:
    """Le titre dans la langue voulue, ou None s'il n'est pas au catalogue."""
    if lang != "fr":
        return None
    return FR.get(cle(titre))


# Ce qui rattache une ANCIENNE forme à la liste. Le premier motif qui
# accroche gagne, donc l'ordre compte : « not exactly » doit tomber sur
# « Not quite. » et non sur « Exactly. », d'où la négation en tête.
_VERS_KO = (
    (r"\b(?:common|usual|classic|trap|everyone|most people)\b", "The common trap."),
    (r"\b(?:close|almost|nearly|not so far)\b", "Almost."),
    (r"\b(?:think|remember|consider|careful|watch)\b", "Think again."),
    (r"\bnot (?:quite|exactly|so|that|it|right)\b", "Not quite."),
    # Les rabaissants tombent ici, et c'est le point : « Wrong », « Nope »
    # et « Misstep » n'ont jamais eu leur place sur cet écran.
    (r"\b(?:wrong|no|nope|oops|misstep|incorrect|false)\b", "Not quite."),
    (r"\b(?:yet|again|retry|try)\b", "Not this time."),
)

_VERS_OK = (
    (r"\b(?:exactly|precisely|exact)\b", "Exactly."),
    (r"\b(?:that s it|thats it|got it|nailed|you see it|that s right)\b", "That's it."),
    (r"\b(?:reason|thinking|thought|insight|smart|clever|sharp)\b", "Well reasoned."),
    (r"\b(?:right|correct|true|yes|spot on)\b", "Correct."),
    (r"\b(?:good|great|nice|well|perfect|brilliant|excellent|beautiful|super)\b",
     "Well seen."),
)


def canoniser(titre: str, ok: bool, graine: int = 0) -> str:
    """Rattache un titre libre à la liste fermée.

    Sert au rattrapage de ce qui a été écrit avant la liste. Ce qui
    n'accroche aucun motif — « Bouncer! », « Space kitchen » — se
    répartit sur la liste par le NUMÉRO DE LA CARTE : ces titres-là ne
    veulent rien dire de particulier, et il vaut mieux les voir varier
    que les voir tous devenir « Exact. ».
    """
    # Ce qui est déjà dans la liste y reste, sans passer par les motifs.
    # C'est ce qui rend la fonction IDEMPOTENTE, et il le faut : le
    # script de rattrapage peut être relancé, et « Not this time. »
    # n'accroche aucun de ses propres motifs — il partait alors sur le
    # tirage par numéro de carte, et le titre changeait à chaque passage.
    table = OK if ok else KO
    if titre in table:
        return titre

    k = cle(titre)
    for motif, canon in (_VERS_OK if ok else _VERS_KO):
        if re.search(motif, k):
            return canon
    return table[graine % len(table)]
