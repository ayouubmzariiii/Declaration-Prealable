"""
Service d'intelligence artificielle pour la Déclaration Préalable.
Supporte deux modèles NVIDIA :
- nemotron : nvidia/nemotron-nano-12b-v2-vl (rapide, system /no_think pour JSON)
- qwen    : qwen/qwen3.5-397b-a17b (puissant, chat_template_kwargs)
"""

import os
import json
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# ─── Model configs ─────────────────────────────────────────────────
MODELS = {
    "nemotron": {
        "name": "nvidia/nemotron-nano-12b-v2-vl",
        "api_key_env": "NVIDIA_API_KEY_NEMOTRON",
        "label": "Rapide et Efficace",
    },
    "qwen": {
        "name": "qwen/qwen3.5-397b-a17b",
        "api_key_env": "NVIDIA_API_KEY",
        "label": "Lent et (accurate)",
    },
}

DEFAULT_MODEL = os.getenv("NVIDIA_MODEL", "nemotron")

# The fields we expect from the advanced architectural prompt
ALL_FIELDS = [
    "etat_initial", "etat_projete", "modifications_detaillees",
    "modification_volume", "modification_emprise_au_sol", "modification_surface_plancher",
    "nombre_ouvertures_existantes", "nombre_ouvertures_projetees",
    "hauteur_estimee_existante", "hauteur_estimee_projete",
    "justification", "coherence_architecturale", "insertion_paysagere",
    "impact_environnemental", "risques_reglementaires_potentiels",
    "facade_materiaux_existants", "facade_materiaux_projetes",
    "menuiseries_existantes", "menuiseries_projetees",
    "toiture_materiaux_existants", "toiture_materiaux_projetes",
    "couleur_facade", "couleur_menuiseries",
    "couleur_volets", "couleur_toiture", "niveau_confiance_global"
]


def get_available_models():
    """Return dict of available models for UI."""
    return {k: v["label"] for k, v in MODELS.items()}


def get_default_model():
    return DEFAULT_MODEL


def _get_model_config(model_key: str = None):
    """Get model config by key."""
    key = model_key or DEFAULT_MODEL
    if key not in MODELS:
        key = DEFAULT_MODEL
    cfg = MODELS[key]
    api_key = os.getenv(cfg["api_key_env"], "")
    return key, cfg["name"], api_key


# ─── API caller ────────────────────────────────────────────────────
def _call_api(messages: list, max_tokens: int = 4096, temperature: float = 0.5,
              model_key: str = None, think: bool = False) -> str:
    """
    Call NVIDIA API. Handles streaming and model-specific thinking modes.
    """
    key, model_name, api_key = _get_model_config(model_key)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "stream": True,
    }

    # Qwen uses chat_template_kwargs for thinking
    if key == "qwen" and think:
        payload["chat_template_kwargs"] = {"enable_thinking": True}

    print(f"[AI] Calling {model_name} (think={think})...")

    response = requests.post(INVOKE_URL, headers=headers, json=payload, stream=True)
    response.raise_for_status()

    full_text = ""

    for line in response.iter_lines():
        if not line:
            continue
        line_str = line.decode("utf-8")
        if not line_str.startswith("data: "):
            continue
        data_str = line_str[6:]
        if data_str.strip() == "[DONE]":
            break
        try:
            data = json.loads(data_str)
            choices = data.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                # Skip thinking/reasoning tokens
                if delta.get("reasoning_content"):
                    continue
                content = delta.get("content", "")
                if content:
                    full_text += content
        except json.JSONDecodeError:
            continue

    return full_text.strip()


# ─── Image encoding ───────────────────────────────────────────────
def _read_image_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _get_mime(path: str) -> str:
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp"}.get(ext, "image/jpeg")


# ─── JSON extraction ──────────────────────────────────────────────
def _extract_json(text: str) -> dict | None:
    """Robustly extract JSON from AI response."""
    cleaned = text.strip()

    # Remove markdown fences
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1]
        if "```" in cleaned:
            cleaned = cleaned.split("```", 1)[0]
        cleaned = cleaned.strip()
    elif "```" in cleaned:
        parts = cleaned.split("```")
        for part in parts[1:]:
            part = part.strip()
            if part.startswith("{"):
                cleaned = part
                break

    # Direct parse
    try:
        return _flatten_json(json.loads(cleaned))
    except (json.JSONDecodeError, ValueError):
        pass

    # Find { ... } with brace matching
    start = cleaned.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(cleaned)):
            if cleaned[i] == "{":
                depth += 1
            elif cleaned[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return _flatten_json(json.loads(cleaned[start:i + 1]))
                    except (json.JSONDecodeError, ValueError):
                        pass
                    break

    return None


def _flatten_json(data: dict) -> dict:
    """Flatten nested group headers into flat keys."""
    flat = {}
    for key, value in data.items():
        if isinstance(value, dict):
            for inner_key, inner_value in value.items():
                flat[inner_key] = inner_value
        else:
            flat[key] = value
    return flat


# ─── The JSON-forcing prompt ──────────────────────────────────────
def _build_analysis_prompt(n_avant: int, n_apres: int, projet_info: dict = None) -> str:
    """Build the advanced architectural analysis prompt."""
    context = ""
    if projet_info:
        context = f"""
INFORMATIONS DU PROJET :
- Adresse : {projet_info.get('adresse', 'Non renseigné')}
- Commune : {projet_info.get('commune', 'Non renseigné')} ({projet_info.get('code_postal', '')})
- Zone PLU : {projet_info.get('zone_plu', '')}
- Type : {projet_info.get('type_travaux', 'Non renseigné')}
- Description : {projet_info.get('description', 'Non renseigné')}
- Surface déclarée : {projet_info.get('surface_existante', '')} m²
"""

    return f"""Analyse ces {n_avant + n_apres} photos avec une précision architecturale et réglementaire maximale.

Les {n_avant} premières images correspondent à l'ÉTAT EXISTANT (avant). 
Les {n_apres} dernières images correspondent à l'ÉTAT PROJETÉ (après).
{context}
MISSION CRUCIALE :
Compare minutieusement l'avant et l'après.
Identifie CHAQUE modification physique visible.
Distingue clairement :
- Modifications esthétiques (couleur, texture, finition)
- Modifications géométriques (dimensions, hauteur, volume)
- Modifications structurelles (ouvertures créées/supprimées, extensions, démolitions)

Ignore totalement les éléments temporaires (météo, végétation, véhicules, ombres).

Détecte explicitement :
- Création, suppression ou modification d'ouvertures
- Modification du volume général
- Modification de l'emprise au sol
- Modification estimée de la surface de plancher

Évalue la cohérence architecturale avec un environnement résidentiel urbain typique d'une zone {projet_info.get('zone_plu', 'UB') if projet_info else 'UB'}.
Signale tout risque réglementaire potentiel.
Si un élément n'est pas clairement identifiable visuellement, indique "non déterminable visuellement".
Pour chaque détection matérielle ou colorimétrique, indique un niveau de confiance (faible, moyen, élevé).

Retourne un objet JSON PLAT avec EXACTEMENT ces clés au premier niveau :
{{
  "etat_initial": "...",
  "etat_projete": "...",
  "modifications_detaillees": "...",
  "modification_volume": "...",
  "modification_emprise_au_sol": "...",
  "modification_surface_plancher": "...",
  "nombre_ouvertures_existantes": "...",
  "nombre_ouvertures_projetees": "...",
  "hauteur_estimee_existante": "...",
  "hauteur_estimee_projete": "...",
  "justification": "...",
  "coherence_architecturale": "...",
  "insertion_paysagere": "...",
  "impact_environnemental": "...",
  "risques_reglementaires_potentiels": "...",
  "facade_materiaux_existants": "... (avec niveau de confiance)",
  "facade_materiaux_projetes": "... (avec niveau de confiance)",
  "menuiseries_existantes": "... (avec niveau de confiance)",
  "menuiseries_projetees": "... (avec niveau de confiance)",
  "toiture_materiaux_existants": "... (avec niveau de confiance)",
  "toiture_materiaux_projetes": "... (avec niveau de confiance)",
  "couleur_facade": "... (RAL estimé si possible + confiance)",
  "couleur_menuiseries": "... (RAL estimé si possible + confiance)",
  "couleur_volets": "... (RAL estimé si possible + confiance)",
  "couleur_toiture": "... (RAL estimé si possible + confiance)",
  "niveau_confiance_global": "..."
}}

RÈGLES STRICTES :
- Réponds UNIQUEMENT avec le JSON.
- PAS de sous-objets.
- COMMENCE par {{ et FINIS par }}.
- PAS de texte avant ou après."""


# ─── Main analysis function ───────────────────────────────────────
def analyser_photos(photos_avant: list, photos_apres: list,
                    projet_info: dict = None, model_key: str = None) -> dict:
    """
    Analyse photos and return a flat dict with all 15 fields.
    Uses system message + /no_think (nemotron) or no-thinking mode (qwen).
    If parsing fails, makes a second call to convert text to JSON.
    """
    key, model_name, api_key = _get_model_config(model_key)
    all_photos = photos_avant + photos_apres
    n_avant = len(photos_avant)
    n_apres = len(photos_apres)

    prompt = _build_analysis_prompt(n_avant, n_apres, projet_info)

    # ── Build messages ──
    # System message: /no_think for nemotron, plain instruction for qwen
    if key == "nemotron":
        system_content = "/no_think\nTu es un expert en urbanisme français. Réponds UNIQUEMENT en JSON."
    else:
        system_content = "Tu es un expert en urbanisme français. Réponds UNIQUEMENT en JSON valide. Commence par { et finis par }."

    # User message with images
    user_content = []
    for path in all_photos:
        b64 = _read_image_b64(path)
        mime = _get_mime(path)
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"}
        })
    user_content.append({"type": "text", "text": prompt})

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    # Call WITHOUT thinking to get clean JSON
    result = _call_api(messages, max_tokens=4096, temperature=0.3,
                       model_key=key, think=False)

    print(f"[AI] Response: {len(result)} chars")
    print(f"[AI] Preview: {result[:300]}")

    # Try to parse
    parsed = _extract_json(result)

    if parsed:
        found = sum(1 for k in ALL_FIELDS if parsed.get(k))
        print(f"[AI] ✓ Parsed {found}/{len(ALL_FIELDS)} fields")
        if found >= 5:
            return parsed
        print(f"[AI] Only {found} fields — trying fallback...")

    # ── FALLBACK: text-to-JSON conversion ──
    print(f"[AI] Primary parse failed. Running text→JSON fallback...")
    return _text_to_json(result, projet_info, model_key=key)


def _text_to_json(raw_text: str, projet_info: dict = None,
                  model_key: str = None) -> dict:
    """Convert plain text to structured JSON via a second API call."""
    key, _, _ = _get_model_config(model_key)

    if key == "nemotron":
        sys_content = "/no_think\nTu es un outil de conversion texte→JSON. Réponds UNIQUEMENT avec un JSON valide."
    else:
        sys_content = "Tu es un outil de conversion texte→JSON. Réponds UNIQUEMENT avec un JSON valide."

    context = ""
    if projet_info:
        context = f"\nContexte: {projet_info.get('adresse', '')}, {projet_info.get('commune', '')}, {projet_info.get('type_travaux', '')}"

    user_content = f"""Convertis ce texte descriptif en JSON avec exactement ces 15 clés :
etat_initial, etat_projete, justification, insertion_paysagere, impact_environnemental,
facade_materiaux_existants, facade_materiaux_projetes, menuiseries_existantes,
menuiseries_projetees, toiture_materiaux_existants, toiture_materiaux_projetes,
couleur_facade, couleur_menuiseries, couleur_volets, couleur_toiture
{context}

TEXTE :
{raw_text[:3000]}

Commence par {{ et finis par }}. RIEN d'autre."""

    messages = [
        {"role": "system", "content": sys_content},
        {"role": "user", "content": user_content},
    ]

    result = _call_api(messages, max_tokens=4096, temperature=0.1,
                       model_key=key, think=False)

    print(f"[AI] Fallback response: {len(result)} chars")

    parsed = _extract_json(result)
    if parsed:
        found = sum(1 for k in ALL_FIELDS if parsed.get(k))
        print(f"[AI] ✓ Fallback parsed {found}/{len(ALL_FIELDS)} fields")
        return parsed

    print("[AI] ✗ Fallback also failed. Returning raw text in etat_initial.")
    result_dict = {k: "" for k in ALL_FIELDS}
    result_dict["etat_initial"] = raw_text[:500]
    return result_dict


# ─── Notice descriptive (text-only, no vision) ────────────────────
def generer_notice_descriptive(projet_data: dict, model_key: str = None) -> dict:
    """Generate notice descriptive without photos."""
    key, _, _ = _get_model_config(model_key)

    if key == "nemotron":
        sys_content = "/no_think\nTu es un expert en urbanisme. Réponds UNIQUEMENT en JSON. Commence par {."
    else:
        sys_content = "Tu es un expert en urbanisme. Réponds UNIQUEMENT en JSON valide."

    user_content = f"""Rédige la notice descriptive pour cette Déclaration Préalable :
TERRAIN : {projet_data.get('adresse', '')}, {projet_data.get('commune', '')}
TYPE : {projet_data.get('type_travaux', '')}
DESCRIPTION : {projet_data.get('description', '')}

JSON avec 5 clés :
{{
  "etat_initial": "3-5 phrases",
  "etat_projete": "3-5 phrases",
  "justification": "2-3 phrases",
  "insertion_paysagere": "2-3 phrases",
  "impact_environnemental": "2-3 phrases"
}}

Commence par {{ — RIEN d'autre."""

    messages = [
        {"role": "system", "content": sys_content},
        {"role": "user", "content": user_content},
    ]

    result = _call_api(messages, max_tokens=4096, temperature=0.4,
                       model_key=key, think=False)

    parsed = _extract_json(result)
    if parsed:
        return parsed

    return _text_to_json(result, projet_data, model_key=key)


# ─── Photo description (single photo) ─────────────────────────────
def generer_description_photo(photo_path: str, est_avant: bool = True,
                              model_key: str = None) -> str:
    """Generate a description for a single photo."""
    etat = "existant (avant travaux)" if est_avant else "projeté (après travaux)"

    b64 = _read_image_b64(photo_path)
    mime = _get_mime(photo_path)

    messages = [
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": f"Décris brièvement cette photo d'un bâtiment dans son état {etat} pour un dossier de Déclaration Préalable. Factuel et professionnel, 1-2 phrases."}
        ]}
    ]

    return _call_api(messages, max_tokens=512, temperature=0.3, model_key=model_key)
