"""Configuration du service. Tout est surchargeable par variable d'environnement."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env_file() -> None:
    """Charge `.env` pour les scripts lancés à la main.

    systemd le fait déjà pour le service (`EnvironmentFile=`), mais
    `scripts/import_exercises.py` se lance depuis un shell : sans ceci,
    la clé posée dans `.env` n'existerait que pour l'API, et la
    génération retomberait silencieusement sur le proxy local. On ne
    remplace jamais une variable déjà définie — l'environnement réel
    l'emporte sur le fichier.
    """
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        if name and name not in os.environ:
            os.environ[name] = value.strip().strip("\"'")


_load_env_file()

DB_PATH = Path(os.environ.get("SARA_DB", ROOT / "data" / "sara.db"))

# Le secret sert à signer les jetons. On le persiste dans un fichier hors
# du dépôt : régénérer le secret déconnecterait tout le monde.
_SECRET_FILE = ROOT / "data" / ".secret"


def _load_secret() -> bytes:
    env = os.environ.get("SARA_SECRET")
    if env:
        return env.encode()
    if _SECRET_FILE.exists():
        return _SECRET_FILE.read_bytes()
    secret = secrets.token_bytes(32)
    _SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SECRET_FILE.write_bytes(secret)
    _SECRET_FILE.chmod(0o600)
    return secret


SECRET = _load_secret()

TOKEN_TTL_DAYS = int(os.environ.get("SARA_TOKEN_TTL_DAYS", "365"))

# Origines autorisées pour le front. En dev, Vite tourne sur 5174.
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "SARA_CORS",
        "http://localhost:5174,http://localhost:4178,http://127.0.0.1:5174",
    ).split(",")
    if o.strip()
]

# Service de génération. Deux protocoles cohabitent :
#
#   * le proxy local, POST /content avec {"prompt": "..."} ;
#   * l'API officielle DeepSeek, compatible OpenAI (chat/completions,
#     jeton porteur, réponse dans choices[0].message.content).
#
# Poser DEEPSEEK_API_KEY suffit à basculer sur l'API officielle : l'URL
# par défaut suit la clé. SARA_LLM_URL reste prioritaire sur les deux,
# pour pointer un autre fournisseur compatible OpenAI sans toucher au code.
LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
LLM_URL = os.environ.get("SARA_LLM_URL", "").strip() or (
    "https://api.deepseek.com/chat/completions"
    if LLM_API_KEY
    else "http://127.0.0.1:8003/content"
)
LLM_NAME = os.environ.get("SARA_LLM_NAME", "deepseek")
LLM_MODEL = os.environ.get("SARA_LLM_MODEL", "deepseek-chat")
LLM_TIMEOUT = float(os.environ.get("SARA_LLM_TIMEOUT", "180"))

# Une API facturée limite le débit ; le proxy local ne le faisait pas.
# Un 429 au milieu d'un lot ne doit pas jeter la centaine d'exercices
# déjà produits — on repasse, en espaçant.
LLM_RETRIES = int(os.environ.get("SARA_LLM_RETRIES", "3"))

# Optionnelle : DeepSeek applique sa propre valeur par défaut si on
# n'envoie rien, et c'est très bien pour de la rédaction d'exercices.
_temp = os.environ.get("SARA_LLM_TEMPERATURE", "").strip()
LLM_TEMPERATURE = float(_temp) if _temp else None

# Le plafond de sortie. Il n'était PAS envoyé, donc celui du fournisseur
# s'appliquait — 4 096 jetons chez DeepSeek. Un lot de dix QCM avec les
# retours d'option et les explications pèse 3 000 à 4 500 jetons : on
# écrivait juste au bord, et un lot sur quatre revenait coupé en plein
# objet. Le tableau JSON était alors illisible et les dix exercices
# perdus, y compris les huit déjà complets.
LLM_MAX_TOKENS = int(os.environ.get("SARA_LLM_MAX_TOKENS", "8192"))

# Le mode JSON du fournisseur : il garantit que la réponse est du JSON
# syntaxiquement valide. Il impose un OBJET — d'où le contrat de sortie
# qui enveloppe la liste dans une clé, et `_extract_json_array` qui sait
# la retrouver. Il ne protège pas de la troncature, seulement de la
# malformation : les deux autres garde-fous restent nécessaires.
#
# À couper avec SARA_LLM_JSON=0 si l'on change de fournisseur pour un
# point d'entrée qui ne connaît pas `response_format`.
LLM_JSON_MODE = os.environ.get("SARA_LLM_JSON", "1").strip() not in ("0", "false", "no")

# Anti-répétition : on écarte du feed les N derniers exercices vus.
FEED_RECENT_WINDOW = int(os.environ.get("SARA_FEED_RECENT", "20"))

# Les types servis dans le flux. Tout ce qui est en base mais absent
# d'ici reste stocké et redevient visible en modifiant cette ligne : on
# ne supprime rien, on filtre.
#
# Réglé sur le QCM seul à la demande du propriétaire — la réponse écrite
# rompait le « un tap par exercice ». Deux autres réglages possibles :
#
#   ("qcm",)                                    628 exercices — actuel
#   ("qcm", "find_error", "complete")           886 — tout ce qui se
#                                               répond d'un tap, seuls
#                                               short_answer et cloze
#                                               demandent d'écrire
#   ()                                          aucun filtre, les 916
#
# Surchargeable sans toucher au code : SARA_FEED_TYPES="qcm,complete".
_types = os.environ.get("SARA_FEED_TYPES", "qcm").strip()
FEED_TYPES = tuple(t.strip() for t in _types.split(",") if t.strip())

# Les types que le modèle a le droit de choisir en écrivant un programme.
# Ne concerne que les connaissances À VENIR : ce qui est déjà en base ne
# bouge pas, c'est `FEED_TYPES` qui décide de ce qu'on en sert.
#
# `cloze` n'y a jamais figuré — `llm.validate` perd le lien entre un
# candidat et son trou. Les autres sont écartés à la demande du
# propriétaire : la réponse écrite rompait le « un tap par exercice ».
#
#   ("qcm",)                                     actuel
#   ("qcm", "complete", "find_error")            sans la saisie clavier
#   ("qcm", "complete", "find_error", "short_answer")   d'origine
#
# Surchargeable : SARA_CHAPTER_TYPES="qcm,complete".
_chap = os.environ.get("SARA_CHAPTER_TYPES", "qcm").strip()
CHAPTER_TYPES = tuple(t.strip() for t in _chap.split(",") if t.strip())

# ----- VOIX ---------------------------------------------------------------
# Le même moteur que la classe avec Sara : Google Cloud Text-to-Speech,
# voix WaveNet, MP3. Pas la voix du navigateur, qui dépend de ce que la
# machine du visiteur a installé et sonne différemment d'un appareil à
# l'autre. Elle reste en repli, jamais en premier choix.
#
# La clé n'est PAS partagée depuis un autre service : elle se pose ici,
# dans le `.env` de ce projet. Sans clé, la route répond 501 et le front
# retombe sur la voix du navigateur — l'app parle toujours.
GOOGLE_TTS_KEY = os.environ.get("GOOGLE_TTS_API_KEY", "").strip()

# WaveNet et Neural2 sont au même tarif chez Google (~16 $/M caractères,
# 1 M offert par mois). Ce sont les voix retenues pour la classe ; on ne
# change pas de timbre d'un produit à l'autre.
TTS_VOICES = {
    "fr": {"languageCode": "fr-FR", "name": "fr-FR-Wavenet-D"},
    "en": {"languageCode": "en-US", "name": "en-US-Wavenet-D"},
}

# Un exercice est lu à l'identique par tous les apprenants : le cache
# disque fait qu'un texte donné n'est facturé qu'une fois, à vie. Sans
# lui, un feed sans fin serait une facture sans fin.
TTS_CACHE_DIR = Path(os.environ.get("SARA_TTS_CACHE", ROOT / "data" / "tts-cache"))
TTS_TIMEOUT = float(os.environ.get("SARA_TTS_TIMEOUT", "30"))
