"""Service Sara — app d'exercices.

    uvicorn api.main:app --host 0.0.0.0 --port 8010
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS, DB_PATH
from .db import connection, scalar
from .routers import admin, auth, feed, generate, progress, taxonomy, themes

app = FastAPI(
    title="Sara — app d'exercices",
    version="0.1.0",
    description="Un flux vertical d'exercices sans fin.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(taxonomy.router)
app.include_router(themes.router)
app.include_router(feed.router)
app.include_router(progress.router)
app.include_router(generate.router)
app.include_router(admin.router)


@app.get("/health", tags=["service"])
def health() -> dict:
    """Vérifie que la base répond et qu'elle a bien été initialisée."""
    with connection() as conn:
        return {
            "status": "ok",
            "db": str(DB_PATH),
            "exercises": scalar(
                conn, "SELECT COUNT(*) FROM exercise WHERE state = 'validated'"
            ),
            "themes": scalar(conn, "SELECT COUNT(*) FROM theme"),
            "prompts": scalar(conn, "SELECT COUNT(*) FROM prompt WHERE is_active = 1"),
        }
