"""Configuration du service. Tout est surchargeable par variable d'environnement."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

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

# Service de génération. Les deux proxies locaux exposent POST /content
# avec {"prompt": "..."} — voir llm.py pour l'adaptation.
LLM_URL = os.environ.get("SARA_LLM_URL", "http://127.0.0.1:8003/content")
LLM_NAME = os.environ.get("SARA_LLM_NAME", "deepseek")
LLM_TIMEOUT = float(os.environ.get("SARA_LLM_TIMEOUT", "180"))

# Anti-répétition : on écarte du feed les N derniers exercices vus.
FEED_RECENT_WINDOW = int(os.environ.get("SARA_FEED_RECENT", "20"))
