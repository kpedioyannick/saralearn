"""Schémas d'échange.

Les limites reprennent celles de la base : elles viennent du cahier des
charges (« un écran, pas de scroll »), pas d'un caprice de validation.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

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
TypeBloom = Literal["remember", "understand", "apply", "analyze"]
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

class SubCategoryOut(BaseModel):
    id: int
    slug: str
    label: str
    color: str | None = None


class CategoryOut(BaseModel):
    id: int
    slug: str
    label: str
    color: str
    sub_categories: list[SubCategoryOut] = []


class ThemeOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None = None
    color: str | None = None
    category_id: int
    category_label: str | None = None
    sub_category_id: int | None = None
    sub_category_label: str | None = None
    visibility: Visibility
    lang: Lang = "fr"
    exercise_count: int
    subscriber_count: int
    tags: list[str] = []
    is_owner: bool = False
    subscribed: bool = False


class ThemeIn(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    category_id: int
    lang: Lang = "fr"
    sub_category_id: int | None = None
    description: str | None = Field(default=None, max_length=2000)
    color: str | None = Field(default=None, max_length=7)
    source_markdown: str | None = Field(default=None, max_length=200_000)
    tags: list[str] = Field(default_factory=list, max_length=20)


class ThemePatch(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    category_id: int | None = None
    sub_category_id: int | None = None
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


class ExerciseOut(BaseModel):
    id: int
    theme_id: int
    theme: str
    color: str
    type_question: TypeQuestion
    type_bloom: TypeBloom
    prompt: str
    body: str | None = None
    # Illustration liée par clé étrangère au panneau, jamais recopiée :
    # c'est ce qui garantit qu'elle correspond bien à la question.
    image: str | None = None
    image_alt: str | None = None
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
    exp_tip: str | None = None
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


class SettingsIn(BaseModel):
    muted: bool | None = None
    dark: bool | None = None
    lang: Lang | None = None
    theme_ids: list[int] | None = None


# --------------------------------------------------------------------------
# Génération
# --------------------------------------------------------------------------

class GenerateIn(BaseModel):
    types: list[TypeQuestion] = Field(min_length=1)
    blooms: list[TypeBloom] = Field(default=["remember", "understand"], min_length=1)
    count: int = Field(default=20, ge=1, le=40)


class GenerationRunOut(BaseModel):
    id: int
    type_question: TypeQuestion
    type_bloom: TypeBloom
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
    exp_tip: str | None = Field(default=None, max_length=240)


TokenOut.model_rebuild()
