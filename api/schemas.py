"""Schémas d'échange.

Les limites reprennent celles de la base : elles viennent du cahier des
charges (« un écran, pas de scroll »), pas d'un caprice de validation.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

# `EmailStr` exigerait le paquet email-validator, absent de la machine et
# qu'on ne veut pas installer pour ça. Cette contrainte suffit : la
# validation sérieuse d'un email, c'est l'envoi d'un message, pas une regex.
EmailStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=5,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$",
    ),
]

# Doit rester aligné sur le CHECK de `exercise.type_question`
# (db/schema.sql et db/migrations/007) : un type accepté en base mais
# absent d'ici fait tomber le feed entier en 500, pas seulement
# l'exercice fautif.
TypeQuestion = Literal[
    "qcm", "true_false", "complete", "find_error", "reorder",
    "short_answer", "cloze",
]
Visibility = Literal["private", "pending", "public"]
Lang = Literal["fr", "en"]
ExerciseState = Literal["draft", "validated", "rejected"]


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------

class AnonymousIn(BaseModel):
    device_id: str = Field(min_length=8, max_length=64)
    lang: Lang = "fr"


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)
    # La langue n'est pas un simple libellé : elle décide du catalogue
    # servi (voir theme.lang). On la demande à l'inscription plutôt que
    # de la laisser à la valeur héritée de la session anonyme.
    lang: Lang = "fr"


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    token: str
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    lang: Lang = "fr"
    display_name: str | None = None
    email: str | None = None
    is_anonymous: bool
    is_admin: bool
    muted: bool
    dark: bool | None = None


# --------------------------------------------------------------------------
# Taxonomie
# --------------------------------------------------------------------------

class CategoryOut(BaseModel):
    id: int
    slug: str
    label: str
    color: str


class ThemeOut(BaseModel):
    id: int
    slug: str
    # Le code de partage : six caractères qui ouvrent le quiz même privé.
    # Servi à tout le monde et pas seulement à l'auteur — c'est justement
    # ce qu'on recopie pour le donner à quelqu'un.
    code: str | None = None
    title: str
    description: str | None = None
    color: str | None = None
    category_id: int
    category_label: str | None = None
    visibility: Visibility
    lang: Lang = "fr"
    exercise_count: int
    subscriber_count: int
    # Deux chiffres d'auteur : le nombre de consignes de génération
    # retenues, et le nombre de personnes ayant répondu au moins une fois.
    # Ils valent 0 pour qui n'a rien créé, et ne coûtent rien à lire.
    prompt_count: int = 0
    learner_count: int = 0
    # Le nombre d'articles qui descendent directement de celui-ci — le
    # poids du chapitre dans l'arbre, et l'ordre d'affichage du catalogue.
    child_count: int = 0
    # L'étage dans l'arbre : 0 pour l'article racine du thème, 1 pour ses
    # piliers. Servi parce que le front trie lui-même, et qu'il doit
    # trier COMME l'API — la racine en tête. Sans ce champ il ne pouvait
    # que deviner, et deux ordres pour une même liste font que l'écran ne
    # montre pas ce que l'API a rangé.
    depth: int = 0
    # Le chapitre dont celui-ci descend, `null` à la racine du thème.
    # Servi parce que suivre un chapitre suit sa branche entière : sans
    # le lien, le front ne saurait pas quelles autres lignes de la liste
    # viennent de changer d'état.
    parent_id: int | None = None
    tags: list[str] = []
    is_owner: bool = False
    subscribed: bool = False


class ThemeIn(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    category_id: int
    lang: Lang = "fr"
    description: str | None = Field(default=None, max_length=2000)
    color: str | None = Field(default=None, max_length=7)
    source_markdown: str | None = Field(default=None, max_length=200_000)
    tags: list[str] = Field(default_factory=list, max_length=20)


class ThemePatch(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=2000)
    color: str | None = Field(default=None, max_length=7)
    source_markdown: str | None = Field(default=None, max_length=200_000)
    tags: list[str] | None = Field(default=None, max_length=20)


class PublishIn(BaseModel):
    public: bool = False


# --------------------------------------------------------------------------
# Exercices
# --------------------------------------------------------------------------

class OptionOut(BaseModel):
    label: str
    feedback: str | None = None
    # Les deux champs suivants ne servent qu'au type `cloze` : un texte à
    # trous porte tous ses candidats dans la même liste, et chacun dit à
    # quel trou il appartient et s'il est le bon. `correct_index` ne peut
    # pas l'exprimer — il n'y a pas une bonne réponse mais une par trou.
    blank: int | None = None
    correct: bool | None = None


class StepOut(BaseModel):
    """Une étape de l'explication, avec son image.

    Le RANG n'est pas envoyé : la liste est déjà dans l'ordre, et un
    numéro que le client n'affiche pas est un numéro qui finit par
    diverger de la position. C'est ce qui arrivait quand le front
    redécoupait `exp_text` lui-même.

    `image` est nulle quand l'étape énonce une relation ou une négation
    — rien à photographier — ou quand aucune banque n'a rendu de photo.
    Le client garde alors celle de l'étape précédente : une image qui
    persiste vaut mieux qu'un trou, et bien mieux qu'une image fausse.
    """

    text: str
    image: str | None = None
    image_alt: str | None = None
    image_credit: str | None = None
    image_credit_url: str | None = None
    image_source: str | None = None


class ExerciseOut(BaseModel):
    id: int
    theme_id: int
    theme: str
    color: str
    type_question: TypeQuestion
    prompt: str
    body: str | None = None
    # Illustration liée par clé étrangère au panneau, jamais recopiée :
    # c'est ce qui garantit qu'elle correspond bien à la question.
    image: str | None = None
    image_alt: str | None = None
    # Le crédit du photographe, le lien vers son profil, et LE NOM DE LA
    # BANQUE. Ils ne sont pas décoratifs : les conditions d'API des trois
    # fournisseurs les imposent dès qu'une de leurs photos est affichée.
    # La source ne se devine pas depuis l'URL — celle de Pixabay est
    # rapatriée chez nous, donc indiscernable d'un fichier local. Voir
    # `api/photos.py`.
    image_credit: str | None = None
    image_credit_url: str | None = None
    image_source: str | None = None
    options: list[OptionOut]
    # Envoyé au client pour un retour instantané et hors ligne. Compromis
    # assumé : lisible dans le DevTools, sans enjeu sur une app
    # d'apprentissage sans note ni classement par exercice.
    correct_index: int
    ok_title: str | None = None
    ok_line: str | None = None
    ko_title: str | None = None
    ko_line: str | None = None
    exp_title: str | None = None
    exp_text: str
    # L'explication découpée, une étape par image. `exp_text` reste : la
    # voix le lit d'un trait quand le client ne sait pas enchaîner, et
    # un client déployé qui ignore `steps` continue de fonctionner.
    steps: list[StepOut] = []
    up_count: int = 0
    down_count: int = 0
    # +1, -1, ou None si l'utilisateur n'a pas voté.
    my_vote: int | None = None
    comment_count: int = 0
    state: ExerciseState = "validated"


class AttemptIn(BaseModel):
    exercise_id: int
    # None = passé au swipe sans répondre.
    chosen_index: int | None = Field(default=None, ge=0, le=3)
    answer_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class AttemptOut(BaseModel):
    is_correct: bool | None
    win: int
    fail: int
    streak: int


class VoteIn(BaseModel):
    # 0 retire le vote — se dédire doit être aussi simple que voter.
    value: Literal[-1, 0, 1]


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class CommentOut(BaseModel):
    id: int
    body: str
    author: str
    created_at: str


# --------------------------------------------------------------------------
# Progression, classement, réglages
# --------------------------------------------------------------------------

class ProgressOut(BaseModel):
    theme_id: int
    name: str
    passed: int
    total: int
    pct: int


class RankRowOut(BaseModel):
    rank: int
    user_id: int
    name: str
    points: int
    passed: int
    is_me: bool = False


class SettingsOut(BaseModel):
    muted: bool
    dark: bool | None = None
    lang: Lang = "fr"
    theme_ids: list[int]
    display_name: str | None = None


# Les libellés que l'app écrit elle-même à la place d'un nom. Les laisser
# prendre ferait passer quelqu'un pour la ligne « c'est vous » du
# classement, ou pour un commentaire sans auteur.
RESERVED_NAMES = frozenset({"toi", "you", "anonyme", "anonymous", "saralearn"})


class SettingsIn(BaseModel):
    muted: bool | None = None
    dark: bool | None = None
    lang: Lang | None = None
    theme_ids: list[int] | None = None
    # Le pseudo. Comme les autres champs de ce corps, `None` veut dire
    # « ne touche pas » — il n'y a donc aucun moyen de l'effacer, et
    # c'est voulu : un nom vide au classement ne veut rien dire.
    #
    # Il n'est PAS unique. L'unicité sur une étiquette que rien ne
    # protège crée une course au nom et laisse croire à une identité
    # qu'elle ne garantit pas : ce qui authentifie, c'est le jeton, pas
    # le pseudo.
    display_name: str | None = Field(default=None, max_length=24)

    @field_validator("display_name")
    @classmethod
    def _clean_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = " ".join(value.split())
        if len(name) < 2:
            raise ValueError("Un pseudo fait au moins deux caractères.")
        if name.casefold() in RESERVED_NAMES:
            raise ValueError("Ce pseudo est un mot réservé de l'app.")
        return name


# --------------------------------------------------------------------------
# Génération
# --------------------------------------------------------------------------

class GenerateIn(BaseModel):
    types: list[TypeQuestion] = Field(min_length=1)
    count: int = Field(default=20, ge=1, le=40)


class GenerationRunOut(BaseModel):
    id: int
    type_question: TypeQuestion
    status: Literal["pending", "running", "done", "failed"]
    requested_count: int
    produced_count: int
    error: str | None = None


class GenerationStatusOut(BaseModel):
    theme_id: int
    running: bool
    requested: int
    produced: int
    validated: int
    runs: list[GenerationRunOut]


class ExercisePatch(BaseModel):
    state: ExerciseState | None = None
    prompt: str | None = Field(default=None, max_length=240)
    exp_text: str | None = Field(default=None, max_length=600)


# --------------------------------------------------------------------------
# Connaissance — le sujet écrit par l'utilisateur, et le programme qu'on
# en tire. Voir api/outline.py pour la demande faite au modèle.
# --------------------------------------------------------------------------

class OutlineIn(BaseModel):
    # Un sujet, pas un cours : « les fonctions PHP ». La borne haute est
    # là pour écarter un copier-coller de document — le dépôt de
    # documents viendra, il ne passera pas par ce champ.
    subject: str = Field(min_length=3, max_length=200)
    lang: Lang | None = None


# Restreint aux cinq types qui existent réellement en base. `prompt` en
# autorise sept, mais `true_false` et `reorder` n'ont jamais rien produit
# et le front ne les a jamais dessinés : voir le CHECK de `chapter`.
ChapterType = Literal["qcm", "complete", "find_error", "short_answer", "cloze"]


class ChapterOut(BaseModel):
    id: int
    position: int
    title: str
    description: str | None = None
    # Le prompt écrit pour ce chapitre. Il n'était pas renvoyé : l'écran
    # de création n'en a pas besoin, il montre l'exemple produit. La
    # fiche d'auteur, elle, liste les prompts eux-mêmes.
    generated_prompt: str | None = None
    # Les trois champs suivants n'arrivent qu'au second appel, une fois
    # le programme validé : ils restent nuls entre-temps.
    type_question: ChapterType | None = None
    example: dict | None = None
    status: Literal["draft", "validated", "rejected"] = "draft"
    error: str | None = None


class ChapterPatch(BaseModel):
    # Le prompt est modifiable : c'est un texte, l'auteur doit pouvoir le
    # corriger sans relancer le modèle. `example` ne l'est pas — il
    # illustre ce que le prompt produit, le retoucher à la main
    # mentirait sur ce qu'on obtiendra.
    status: Literal["draft", "validated", "rejected"] | None = None
    title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    type_question: ChapterType | None = None
    generated_prompt: str | None = Field(default=None, max_length=20_000)


class GenerateFromChaptersIn(BaseModel):
    # Réparti sur les chapitres retenus. La borne haute est celle de
    # `GenerateIn` : au-delà, l'auteur ne relit plus et valide en bloc.
    count: int = Field(default=20, ge=1, le=40)


class KnowledgeOut(BaseModel):
    theme_id: int
    title: str
    description: str | None = None
    category_id: int
    category_label: str
    # Vrai quand le modèle a créé la catégorie : elle n'entre au
    # catalogue qu'une fois retenue, sans quoi chaque essai abandonné en
    # laisserait une derrière lui.
    category_is_new: bool = False
    tags: list[str] = []
    chapters: list[ChapterOut] = []


TokenOut.model_rebuild()
