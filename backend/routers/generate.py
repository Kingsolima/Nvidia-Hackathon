"""
POST /generate/building-image

Accepts either:
  - A natural language prompt (free-form description)
  - Direct structured parameters (building_type, style, floors, size)

Returns base64-encoded PNG + metadata.
"""

import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from rendering.ai_renderer import generate_ai_image

router = APIRouter(prefix="/generate", tags=["generate"])


class GenerateRequest(BaseModel):
    prompt: Optional[str] = None

    building_type: Optional[str] = None
    style:         Optional[str] = None
    floors:        Optional[int] = None
    size:          Optional[str] = None


class GenerateResponse(BaseModel):
    image_b64: str
    image_path: str
    metadata: dict


@router.post("/building-image", response_model=GenerateResponse)
def generate_image(req: GenerateRequest):
    building_type = req.building_type or "skyscraper"
    style         = req.style or "modern_glass_tower"
    floors        = req.floors or 20
    size          = req.size or "medium"
    user_desc     = req.prompt or f"{size} {style.replace('_',' ')} {building_type} {floors} floors"

    png, renderer = generate_ai_image(
        style=style,
        building_type=building_type,
        floors=floors,
        size=size,
        user_description=user_desc,
    )

    if png is None:
        raise HTTPException(status_code=503, detail="Image generation failed — check OPENAI_API_KEY")

    return GenerateResponse(
        image_b64=base64.b64encode(png).decode(),
        image_path=f"(in-memory) {building_type}_{style}_{floors}fl_{size}.png",
        metadata={
            "building_type": building_type,
            "style":         style,
            "floors":        floors,
            "size":          size,
            "renderer":      renderer,
            "canvas_px":     "800x1000",
            "background_hex": "#D3D3D3",
        },
    )
