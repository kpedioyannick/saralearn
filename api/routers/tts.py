"""La voix de l'app.

Même moteur que la classe avec Sara — Google Cloud Text-to-Speech, voix
WaveNet, MP3 — et pour la même raison : la voix du navigateur dépend de
ce que la machine du visiteur a installé. Elle est absente sur certaines,
robotique sur d'autres, et ne sonne jamais pareil d'un appareil au
suivant. Une question lue par l'app doit avoir une seule voix.

Le navigateur envoie le texte, reçoit un MP3. La clé reste ici : la
poser dans le bundle la rendrait publique.

Deux garde-fous sur la facture, tous deux repris de `saraClasse.js` :

  · un cache disque indexé par `sha1(voix|débit|texte)`. Les exercices
    sont identiques pour tout le monde — un texte n'est payé qu'une
    fois, à vie. C'est ce qui rend un feed sans fin tenable ;
  · une session obligatoire, même anonyme. Sans elle, la route est un
    synthétiseur vocal gratuit ouvert sur l'internet, facturé à nous.

Sans clé configurée : 501, et le front retombe sur la voix du
navigateur. L'app parle toujours, moins bien.
"""

from __future__ import annotations

import hashlib
import re

import httpx
from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from ..config import GOOGLE_TTS_KEY, TTS_CACHE_DIR, TTS_TIMEOUT, TTS_VOICES
from ..security import CurrentUser

router = APIRouter(tags=["voix"])

GOOGLE_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"

# Google refuse au-delà de ~5000 octets par requête. On découpe plus bas
# pour garder de la marge sur les accents, qui pèsent deux octets.
CHUNK_BYTES = 4200


class SpeakIn(BaseModel):
    text: str = Field(max_length=6000)
    lang: str = "fr"
    # Le débit est borné des deux côtés : au-delà la voix devient
    # inintelligible, et chaque valeur distincte crée une entrée de cache
    # de plus — donc un appel facturé de plus.
    rate: float = Field(default=1.0, ge=0.7, le=1.3)


def _chunks(text: str) -> list[str]:
    """Découpe aux fins de phrase, pour que la coupure s'entende le moins."""
    sentences = re.findall(r"[^.!?…]+[.!?…]*", text) or [text]
    out: list[str] = []
    buf = ""
    for sentence in sentences:
        if len((buf + sentence).encode("utf-8")) <= CHUNK_BYTES:
            buf += sentence
            continue
        if buf.strip():
            out.append(buf.strip())
        buf = sentence
    if buf.strip():
        out.append(buf.strip())
    return out


async def _synthesize(client: httpx.AsyncClient, chunk: str, voice: dict, rate: float) -> bytes:
    resp = await client.post(
        GOOGLE_URL,
        params={"key": GOOGLE_TTS_KEY},
        json={
            "input": {"text": chunk},
            "voice": voice,
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": rate},
        },
    )
    payload = resp.json() if resp.content else {}
    audio = payload.get("audioContent")
    if resp.status_code != 200 or not audio:
        detail = str(payload.get("error", {}))[:200]
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Google TTS {resp.status_code} {detail}")
    import base64

    return base64.b64decode(audio)


@router.post(
    "/tts",
    responses={200: {"content": {"audio/mpeg": {}}}},
    response_class=Response,
)
async def speak(payload: SpeakIn, user: CurrentUser) -> Response:
    if not GOOGLE_TTS_KEY:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "GOOGLE_TTS_API_KEY absente — le front retombe sur la voix du navigateur.",
        )

    text = payload.text.strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Texte vide.")

    lang = payload.lang if payload.lang in TTS_VOICES else "fr"
    voice = TTS_VOICES[lang]
    rate = round(payload.rate, 2)

    # La même formule de hachage que `saraClasse.js`, au format du débit
    # près : JavaScript écrit `1` là où Python écrirait `1.0`, et deux
    # graphies donnent deux empreintes. `%g` rend la forme courte, donc la
    # même clé — les deux services peuvent partager un dossier de cache
    # sans repayer les mêmes textes. Vérifié : sha1 identique des deux côtés.
    key = "%s|%g|%s" % (voice["name"], rate, text)
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    cached = TTS_CACHE_DIR / f"{digest}.mp3"

    if cached.exists():
        return Response(cached.read_bytes(), media_type="audio/mpeg")

    async with httpx.AsyncClient(timeout=TTS_TIMEOUT) as client:
        parts = [await _synthesize(client, chunk, voice, rate) for chunk in _chunks(text)]

    audio = b"".join(parts)
    # Écrit après coup seulement : un MP3 tronqué en cache se rejouerait
    # tronqué pour toujours, sans que rien ne le signale.
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(audio)

    return Response(audio, media_type="audio/mpeg")
