"""Appel au service de génération, et validation stricte de sa réponse.

Le service local expose POST /content avec {"prompt": "..."}. On reste
volontairement tolérant sur la forme de la réponse (les proxies ne
répondent pas tous pareil) et intransigeant sur son contenu : un
exercice mal formé n'entre pas en base.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import LLM_TIMEOUT, LLM_URL

# Limites reprises du schéma : les dépasser ferait sauter la contrainte
# SQL de toute façon, autant écarter proprement ici.
LIMITS = {
    "prompt": 240,
    "body": 400,
    "ok_title": 80,
    "ok_line": 200,
    "ko_title": 80,
    "ko_line": 200,
    "exp_title": 160,
    "exp_text": 600,
    "exp_tip": 240,
}


class GenerationError(RuntimeError):
    pass


def render(template: str, **values: Any) -> str:
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out


async def ask(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        try:
            resp = await client.post(LLM_URL, json={"prompt": prompt})
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise GenerationError(f"Service de génération injoignable : {exc}") from exc

    try:
        payload = resp.json()
    except ValueError:
        return resp.text

    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in ("content", "response", "text", "result", "message", "answer"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return json.dumps(payload, ensure_ascii=False)


def _extract_json_array(raw: str) -> list[Any]:
    """Le modèle encadre souvent sa réponse — on récupère le tableau."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start = text.find("[")
    if start == -1:
        raise GenerationError("Aucun tableau JSON dans la réponse du modèle.")
    # raw_decode s'arrête à la fin du tableau et ignore ce qui suit. Le
    # modèle ajoute parfois un commentaire après sa réponse — ce n'était
    # pas une raison de jeter les exercices.
    try:
        data, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise GenerationError(f"JSON invalide : {exc}") from exc
    if not isinstance(data, list):
        raise GenerationError("La réponse n'est pas un tableau.")
    return data


def _clean(value: Any, field: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    limit = LIMITS.get(field)
    if limit and len(text) > limit:
        # On tronque au dernier séparateur plutôt que de couper un mot,
        # et on écarte si même tronqué ça n'a plus de sens.
        cut = text[:limit]
        pivot = max(cut.rfind(". "), cut.rfind(" · "), cut.rfind(", "))
        text = (cut[: pivot + 1] if pivot > limit * 0.6 else cut).strip()
    return text or None


def validate(raw: str, type_question: str) -> list[dict]:
    """Ne garde que les exercices exploitables. Le reste est écarté sans bruit."""
    kept: list[dict] = []

    for item in _extract_json_array(raw):
        if not isinstance(item, dict):
            continue

        prompt = _clean(item.get("prompt"), "prompt")
        exp_text = _clean(item.get("exp_text"), "exp_text")
        options_raw = item.get("options")
        correct = item.get("correct_index")

        if not prompt or not exp_text or not isinstance(options_raw, list):
            continue
        if not isinstance(correct, int) or not 0 <= correct <= 3:
            continue

        options = []
        for opt in options_raw:
            # On ne tronque PAS un libellé trop long : couper « doit prendre
            # un s » à 60 caractères produit une réponse fausse. On écarte.
            if isinstance(opt, str):
                options.append({"label": opt.strip()})
            elif isinstance(opt, dict):
                label = str(opt.get("label", "")).strip()
                if not label:
                    continue
                entry: dict[str, str] = {"label": label}
                feedback = _clean(opt.get("feedback"), "ko_line")
                if feedback:
                    entry["feedback"] = feedback
                options.append(entry)

        if len(options) < 2 or correct >= len(options):
            continue
        # Deux libellés identiques rendent la bonne réponse indécidable.
        if len({o["label"].casefold() for o in options}) != len(options):
            continue

        if type_question == "true_false" and len(options) != 2:
            continue
        if any(len(o["label"]) > 60 for o in options):
            continue
        # Les gabarits en demandent quatre : trois, c'est une génération
        # incomplète, et l'écran est dimensionné pour quatre.
        if type_question in {"qcm", "complete"} and len(options) != 4:
            continue

        body = _clean(item.get("body"), "body")
        if type_question == "find_error" and not body:
            continue

        kept.append(
            {
                "prompt": prompt,
                "body": body,
                "options": options,
                "correct_index": correct,
                "ok_title": _clean(item.get("ok_title"), "ok_title") or "Bien vu.",
                "ok_line": _clean(item.get("ok_line"), "ok_line"),
                "ko_title": _clean(item.get("ko_title"), "ko_title") or "Presque.",
                "ko_line": _clean(item.get("ko_line"), "ko_line"),
                "exp_title": _clean(item.get("exp_title"), "exp_title"),
                "exp_text": exp_text,
                "exp_tip": _clean(item.get("exp_tip"), "exp_tip"),
            }
        )

    return kept
