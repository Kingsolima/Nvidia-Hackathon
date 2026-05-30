"""
AI-powered building image generator.

Priority:
  1. Google Imagen 3   — hyperrealistic, LangChain-enhanced prompt (GOOGLE_API_KEY)
  2. Together AI       — FLUX.1-schnell free tier                  (TOGETHER_API_KEY)
  3. NVIDIA Build      — SDXL-Turbo                                (NGC_API_KEY)
  4. None              — caller falls back to PIL renderer

Set in .env:
  GOOGLE_API_KEY=...     (Google AI Studio — aistudio.google.com/app/apikey)
  TOGETHER_API_KEY=...   (get free key at api.together.xyz)
  NGC_API_KEY=...        (already set for NeMoTron — doubles as image API key)

Seed is derived from (style + building_type + floors + size) so the same
parameters always produce the same image — deterministic without PIL.
"""

from __future__ import annotations
import os, hashlib, base64
from io import BytesIO
from typing import Optional

import httpx
from PIL import Image

from rendering.gemini_renderer import generate_gemini_image
from rendering.dalle_renderer import generate_dalle_image

# ── Prompt templates per style ─────────────────────────────────────────────────
# Each prompt forces:  front elevation · grey background · architectural illustration
# Negative terms steer away from: perspective shots, people, realistic photography

_BASE_SUFFIX = (
    ", architectural front elevation view, perfectly symmetrical, "
    "isolated on solid flat light grey background #E0E0E0, "
    "no sky, no ground, no people, no trees, no cars, "
    "professional architectural illustration, clean lines"
)

_NEG = (
    "perspective view, isometric, 3d render, photorealistic photo, "
    "people, cars, trees, sky, clouds, blurry, watermark, text, "
    "fisheye, wide angle, distorted, cartoon, sketch, low quality"
)

STYLE_PROMPTS: dict[str, str] = {
    "gothic": (
        "gothic cathedral, soaring stone spire, pointed lancet arched windows, "
        "flying buttresses, intricate carved tracery, gargoyles, dark grey limestone, "
        "medieval ecclesiastical architecture, vertical emphasis"
        + _BASE_SUFFIX
    ),
    "baroque": (
        "baroque palace, grand ornate facade, curved pediment, decorative stone columns, "
        "arched windows with carved keystones, gilded balconies, warm cream limestone, "
        "symmetrical classical composition, elaborate cornice with sculptures"
        + _BASE_SUFFIX
    ),
    "art_deco": (
        "art deco skyscraper, geometric stepped crown, gold aluminium ornamental fins, "
        "cream limestone and bronze cladding, zigzag relief patterns, vertical emphasis, "
        "1920s New York aesthetic, stylised sunburst motifs, setback silhouette"
        + _BASE_SUFFIX
    ),
    "neoclassical": (
        "neoclassical government building, white marble facade, "
        "grand ionic columns supporting entablature, triangular pediment, "
        "symmetrical arched windows with stone keystones, wide stone steps, "
        "greek revival architecture, imposing civic presence"
        + _BASE_SUFFIX
    ),
    "industrial": (
        "industrial factory building, dark red exposed brick facade, "
        "large steel-framed multi-pane factory windows, sawtooth roofline, "
        "metal fire escape stairs, brick chimneys, cast-iron structural elements, "
        "victorian industrial warehouse aesthetic"
        + _BASE_SUFFIX
    ),
    "contemporary": (
        "contemporary minimalist building, pure white flat facade, "
        "full floor-to-ceiling glass windows, thin black aluminium frames, "
        "clean geometric rectangular form, flat roof, scandinavian modernist design, "
        "zero ornamentation, high-contrast white and black"
        + _BASE_SUFFIX
    ),
    "modern_glass_tower": (
        "modern glass skyscraper, blue-green reflective curtain wall, "
        "aluminium mullion grid, sleek corporate tower, tapered crown, "
        "reflective glass panels, contemporary high-rise office building"
        + _BASE_SUFFIX
    ),
    "traditional_brick": (
        "traditional red brick building, flemish bond brickwork, "
        "sash windows with white painted frames, stone lintels and sills, "
        "decorative brick corbelling, slate pitched roof, victorian architecture, "
        "warm terracotta brick colour"
        + _BASE_SUFFIX
    ),
    "brutalist_concrete": (
        "brutalist concrete building, raw béton brut surface texture, "
        "small deeply recessed punched windows, heavy cantilevered floors, "
        "bold geometric massing, rough board-marked concrete, "
        "oppressive monolithic presence, 1960s architectural brutalism"
        + _BASE_SUFFIX
    ),
    "retail_complex": (
        "modern retail complex, large glass storefront windows, "
        "aluminium canopy over entrance, contemporary commercial facade, "
        "signage band at parapet, wide horizontal emphasis, "
        "shopping centre architecture"
        + _BASE_SUFFIX
    ),
}

# Extra building-type detail injected into the prompt
_TYPE_DETAIL: dict[str, str] = {
    "skyscraper":        "tall multi-storey tower, {floors} floors high, ",
    "house":             "residential house, {floors} storey, ",
    "suburban_building": "mid-rise building, {floors} floors, wide facade, ",
}


def _seed(style: str, building_type: str, floors: int, size: str) -> int:
    h = hashlib.md5(f"{style}{building_type}{floors}{size}".encode()).hexdigest()
    return int(h[:8], 16) % 2_147_483_647


def _build_prompt(style: str, building_type: str, floors: int, size: str) -> str:
    base = STYLE_PROMPTS.get(style, STYLE_PROMPTS["modern_glass_tower"])
    type_detail = _TYPE_DETAIL.get(building_type, "").format(floors=floors)
    size_detail = {"small": "small scale, ", "large": "large grand scale, "}.get(size, "")
    return size_detail + type_detail + base


# ── Together AI (FLUX.1-schnell — free tier) ───────────────────────────────────

def _together(prompt: str, seed: int) -> Optional[bytes]:
    key = os.getenv("TOGETHER_API_KEY")
    if not key:
        return None
    try:
        r = httpx.post(
            "https://api.together.xyz/v1/images/generations",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model":  "black-forest-labs/FLUX.1-schnell-Free",
                "prompt": prompt,
                "width":  832,
                "height": 1216,
                "n":      1,
                "seed":   seed,
                "response_format": "b64_json",
            },
            timeout=45.0,
        )
        r.raise_for_status()
        data = r.json()
        b64 = (data.get("data") or [{}])[0].get("b64_json")
        if b64:
            return _normalise(base64.b64decode(b64))
        url = (data.get("data") or [{}])[0].get("url")
        if url:
            return _normalise(httpx.get(url, timeout=20).content)
    except Exception as e:
        print(f"[ai_renderer] Together AI failed: {e}")
    return None


# ── NVIDIA Build API (SDXL-Turbo) ─────────────────────────────────────────────

def _nvidia(prompt: str, seed: int) -> Optional[bytes]:
    key = os.getenv("NGC_API_KEY")
    if not key or key == "your_ngc_api_key_here":
        return None
    try:
        r = httpx.post(
            "https://ai.api.nvidia.com/v1/genai/stabilityai/sdxl-turbo",
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            json={
                "text_prompts": [
                    {"text": prompt,  "weight": 1},
                    {"text": _NEG,    "weight": -1},
                ],
                "cfg_scale": 0,
                "seed":      seed,
                "steps":     4,
                "width":     512,
                "height":    768,
            },
            timeout=30.0,
        )
        r.raise_for_status()
        b64 = r.json()["artifacts"][0]["base64"]
        return _normalise(base64.b64decode(b64))
    except Exception as e:
        print(f"[ai_renderer] NVIDIA failed: {e}")
    return None


# ── Background normalisation ───────────────────────────────────────────────────

def _normalise(raw: bytes) -> bytes:
    """
    Resize to 800×1000 and place on a guaranteed #E0E0E0 canvas.
    The generated image sits centred; any gaps filled with grey.
    """
    img = Image.open(BytesIO(raw)).convert("RGB")

    canvas = Image.new("RGB", (800, 1000), (224, 224, 224))
    img.thumbnail((800, 1000), Image.LANCZOS)
    x = (800 - img.width)  // 2
    y = (1000 - img.height) // 2
    canvas.paste(img, (x, y))

    buf = BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


# ── Public entry point ─────────────────────────────────────────────────────────

def generate_ai_image(
    style: str,
    building_type: str,
    floors: int,
    size: str,
    user_description: str = "",
) -> tuple[Optional[bytes], str]:
    """
    Returns (png_bytes, source_label).
    source_label is "together" | "nvidia" | "pil" (caller handles pil fallback).
    """
    prompt = _build_prompt(style, building_type, floors, size)
    seed   = _seed(style, building_type, floors, size)

    result = generate_dalle_image(
        user_description=user_description or f"{size} {building_type} {style}",
        style=style,
        building_type=building_type,
        floors=floors,
        size=size,
    )
    if result:
        return result, "DALL-E 3 · OpenAI"

    result = generate_gemini_image(style, building_type, floors, size)
    if result:
        return result, "Imagen 3 · Google"

    result = _together(prompt, seed)
    if result:
        return result, "FLUX · Together AI"

    result = _nvidia(prompt, seed)
    if result:
        return result, "SDXL · NVIDIA Build"

    return None, "pil"
