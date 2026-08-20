"""Appel au service de génération, et validation stricte de sa réponse.

Deux protocoles, un seul appelant. Le proxy local expose POST /content
avec {"prompt": "..."} ; l'API officielle DeepSeek parle le dialecte
d'OpenAI — chat/completions, jeton porteur, texte dans
choices[0].message.content. C'est la présence d'une clé ET d'une URL de
complétion qui décide : poser DEEPSEEK_API_KEY suffit.

On reste volontairement tolérant sur la forme de la réponse (les proxies
ne répondent pas tous pareil) et intransigeant sur son contenu : un
exercice mal formé n'entre pas en base.
"""

from __future__ import annotations

import ast
import asyncio
import json
import re
from typing import Any

import httpx

from .config import (
    LLM_API_KEY,
    LLM_JSON_MODE,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_RETRIES,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    LLM_URL,
)

# Une clé posée sur une URL de proxy ne veut pas dire « parle OpenAI » :
# c'est le point d'entrée qui tranche, la clé seule ne suffit pas.
USES_CHAT_API = bool(LLM_API_KEY) and LLM_URL.rstrip("/").endswith(
    ("/chat/completions", "/completions")
)

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
}


class GenerationError(RuntimeError):
    pass


def render(template: str, **values: Any) -> str:
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out


def _request() -> tuple[dict[str, Any], dict[str, str]]:
    """Le corps et les en-têtes, selon le protocole du point d'entrée."""
    if not USES_CHAT_API:
        return {"prompt": ""}, {}

    body: dict[str, Any] = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": ""}],
        "stream": False,
        # Sans ce plafond c'est celui du fournisseur qui s'applique, et
        # il coupait un lot sur quatre en plein objet JSON.
        "max_tokens": LLM_MAX_TOKENS,
    }
    if LLM_TEMPERATURE is not None:
        body["temperature"] = LLM_TEMPERATURE
    if LLM_JSON_MODE:
        # Le fournisseur garantit alors du JSON valide. Il exige que le
        # mot « json » figure dans la consigne — tous nos contrats de
        # sortie disent « JSON », donc la condition est tenue.
        body["response_format"] = {"type": "json_object"}
    return body, {"Authorization": f"Bearer {LLM_API_KEY}"}


def _fill(body: dict[str, Any], prompt: str) -> dict[str, Any]:
    if USES_CHAT_API:
        body["messages"] = [{"role": "user", "content": prompt}]
    else:
        body["prompt"] = prompt
    return body


async def ask(prompt: str) -> str:
    body, headers = _request()
    _fill(body, prompt)

    # 429 et 5xx sont transitoires : on repasse. 400 et 401 ne le sont
    # pas — insister sur une clé refusée ne fait que perdre du temps.
    last: Exception | None = None
    resp: httpx.Response | None = None

    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        for attempt in range(max(1, LLM_RETRIES)):
            try:
                resp = await client.post(LLM_URL, json=body, headers=headers)
                resp.raise_for_status()
                break
            except httpx.HTTPStatusError as exc:
                last = exc
                code = exc.response.status_code
                if code != 429 and code < 500:
                    raise GenerationError(
                        f"Le service de génération refuse l'appel (HTTP {code}) : "
                        f"{exc.response.text[:200]}"
                    ) from exc
                resp = None
            except httpx.HTTPError as exc:
                last = exc
                resp = None

            if attempt + 1 < max(1, LLM_RETRIES):
                await asyncio.sleep(2 ** attempt * 2)

    if resp is None:
        raise GenerationError(f"Service de génération injoignable : {last}")

    try:
        payload = resp.json()
    except ValueError:
        return resp.text

    if isinstance(payload, str):
        return payload

    if isinstance(payload, dict):
        # Dialecte OpenAI d'abord : le texte est enfoui d'un cran.
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content

        for key in ("content", "response", "text", "result", "message", "answer"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value

    return json.dumps(payload, ensure_ascii=False)


def _objets_complets(text: str) -> list[Any]:
    """Les objets d'un tableau tronqué, un par un, jusqu'à la coupure.

    LE FILET. `raw_decode` sur le tableau entier est tout ou rien : un
    lot coupé au huitième exercice faisait perdre les sept précédents,
    pourtant complets et valides. On avance donc objet par objet et on
    garde ceux qui se ferment.

    Le décodeur s'arrête de lui-même à la fin de chaque objet et rend la
    position atteinte : on repart de là, on saute la virgule, et on
    recommence. Le premier objet incomplet met fin à la lecture — ce qui
    suit ne peut être que la queue tronquée.
    """
    dec = json.JSONDecoder()
    out: list[Any] = []
    i = 0
    n = len(text)
    while i < n:
        while i < n and text[i] in " \t\r\n,":
            i += 1
        if i >= n or text[i] == "]":
            break
        try:
            obj, i = dec.raw_decode(text, i)
        except json.JSONDecodeError:
            break
        out.append(obj)
    return out


def sans_virgules_orphelines(text: str) -> str:
    """Retire les virgules qui ne précèdent qu'une fermeture.

    `{"a": 1,}` n'est pas du JSON, et le modèle en produit. Le coût n'est
    pas la virgule : c'est le lot. `_objets_complets` prend la faute pour
    une troncature et s'arrête là, donc un lot de dix exercices dont le
    cinquième traîne une virgule en rend quatre. Mesuré sur trois lots
    d'affilée : 10 gardés, puis 4, puis 1 — trois appels payés au même
    prix pour des récoltes qui n'ont rien à voir.

    On lit caractère par caractère plutôt qu'à coups d'expression
    régulière : une virgule dans un texte d'explication (« … la lumière,
    elle, ralentit ») ne doit pas être touchée, et seul le suivi de
    l'état « dans une chaîne » le garantit. L'antislash protège le
    caractère d'après, sinon un guillemet échappé rouvrirait la chaîne.
    """
    out: list[str] = []
    dans_chaine = False
    echappe = False
    for i, c in enumerate(text):
        if dans_chaine:
            out.append(c)
            if echappe:
                echappe = False
            elif c == "\\":
                echappe = True
            elif c == '"':
                dans_chaine = False
            continue
        if c == '"':
            dans_chaine = True
            out.append(c)
            continue
        if c == ",":
            j = i + 1
            while j < len(text) and text[j] in " \t\r\n":
                j += 1
            if j < len(text) and text[j] in "}]":
                continue  # la virgule ne sépare rien : elle saute
        out.append(c)
    return "".join(out)


# Les clés sous lesquelles le mode JSON du fournisseur range la liste.
# Il impose un objet : le contrat de sortie demande « exercises », mais
# un modèle qui rend « items » ou « questions » ne doit pas faire perdre
# le lot pour un nom.
_CLES_LISTE = ("exercises", "items", "questions", "exercices", "data", "results")


def _extract_json_array(raw: str) -> list[Any]:
    """Le modèle encadre souvent sa réponse — on récupère le tableau.

    Trois formes acceptées, chacune payée par un échec observé :

      · le tableau nu, `[{…}, {…}]` — le contrat historique ;
      · un objet qui l'enveloppe, `{"exercises": [{…}]}` — c'est ce que
        le mode JSON du fournisseur impose, il ne rend jamais un tableau
        à la racine ;
      · un tableau COUPÉ, quand la sortie a buté sur le plafond de
        jetons. On garde alors les objets complets au lieu de tout jeter.

    Et une réparation avant toute lecture : la virgule en trop devant une
    fermeture, qui coûtait des lots entiers — voir
    `sans_virgules_orphelines`.
    """
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    text = sans_virgules_orphelines(text)

    # Un objet enveloppant : on va chercher la liste dedans, et on
    # retombe sur la lecture tolérante si l'objet lui-même est coupé.
    if text.startswith("{"):
        try:
            data, _ = json.JSONDecoder().raw_decode(text)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            for cle in _CLES_LISTE:
                if isinstance(data.get(cle), list):
                    return data[cle]
            # Une seule valeur, et c'est une liste : le nom importe peu.
            listes = [v for v in data.values() if isinstance(v, list)]
            if len(listes) == 1:
                return listes[0]
            raise GenerationError("L'objet rendu ne contient aucune liste d'exercices.")

    start = text.find("[")
    if start == -1:
        raise GenerationError("Aucun tableau JSON dans la réponse du modèle.")
    # raw_decode s'arrête à la fin du tableau et ignore ce qui suit. Le
    # modèle ajoute parfois un commentaire après sa réponse — ce n'était
    # pas une raison de jeter les exercices.
    try:
        data, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        # Coupé. On récupère ce qui tient debout ; ne rien récupérer du
        # tout reste une erreur, c'est alors autre chose qu'une troncature.
        sauves = _objets_complets(text[start + 1 :])
        if sauves:
            return sauves
        raise GenerationError("JSON invalide et rien de récupérable.") from None
    if not isinstance(data, list):
        raise GenerationError("La réponse n'est pas un tableau.")
    return data


def extract_json_object(raw: str) -> dict:
    """Récupère l'objet JSON, quoi que le modèle ait mis autour.

    Pendant de `_extract_json_array` pour les appels qui attendent un
    objet — la présentation d'une connaissance, le prompt d'un chapitre.

    Trois tolérances, chacune payée par un échec observé :

      · le bloc de code, que le modèle ajoute une fois sur deux ;
      · le texte AVANT l'objet (« Voici la fiche : { … »), d'où l'essai
        sur chaque accolade et pas seulement la première ;
      · les guillemets simples — `{'title': …}`, du Python et non du
        JSON. `literal_eval` les lit sans rien exécuter : c'est un
        analyseur de littéraux, pas un interpréteur.

    Et la virgule orpheline, retirée avant lecture comme pour les
    tableaux.
    """
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    text = sans_virgules_orphelines(text)

    decoder = json.JSONDecoder()
    first_error: Exception | None = None
    for start in (m.start() for m in re.finditer(r"\{", text)):
        try:
            data, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError as exc:
            first_error = first_error or exc
            try:
                data = ast.literal_eval(text[start:])
            except (ValueError, SyntaxError):
                continue
        if isinstance(data, dict):
            return data

    if first_error is None:
        raise GenerationError("Aucun objet JSON dans la réponse du modèle.")
    raise GenerationError(f"JSON invalide : {first_error}")


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


# Les deux titres de repli, quand le modèle a omis les siens. Ils sont
# AFFICHÉS À L'ÉLÈVE : un « Bien vu. » sous une question anglaise se voit
# tout de suite. Ils suivent donc la langue du thème, comme le reste.
FALLBACK_TITLES = {
    "fr": ("Bien vu.", "Presque."),
    "en": ("Nice one.", "Not quite."),
}


def validate(raw: str, type_question: str, lang: str = "fr") -> list[dict]:
    """Ne garde que les exercices exploitables. Le reste est écarté sans bruit."""
    kept: list[dict] = []
    ok_default, ko_default = FALLBACK_TITLES.get(lang, FALLBACK_TITLES["fr"])

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

        # Les mots de la photo d'ambiance. Facultatif et sans borne de
        # forme : `photos.revele` les jugera contre l'exercice lui-même,
        # et une requête absente veut simplement dire pas de photo.
        image_query = str(item.get("image_query") or "").strip()[:120] or None

        kept.append(
            {
                "image_query": image_query,
                "prompt": prompt,
                "body": body,
                "options": options,
                "correct_index": correct,
                "ok_title": _clean(item.get("ok_title"), "ok_title") or ok_default,
                "ok_line": _clean(item.get("ok_line"), "ok_line"),
                "ko_title": _clean(item.get("ko_title"), "ko_title") or ko_default,
                "ko_line": _clean(item.get("ko_line"), "ko_line"),
                "exp_title": _clean(item.get("exp_title"), "exp_title"),
                "exp_text": exp_text,
            }
        )

    return kept
