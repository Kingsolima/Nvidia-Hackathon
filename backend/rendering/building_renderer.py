"""
Building image generator — delegates entirely to DALL-E 3 (gpt-image-1).
No PIL drawing. Every image is AI-generated from the user's query.
"""

from __future__ import annotations
from typing import Optional
from rendering.dalle_renderer import generate_dalle_image


def render_building(
    building_type: str,
    style: str,
    floors: int,
    size: str,
    user_description: str = "",
) -> Optional[bytes]:
    description = user_description or f"{size} {style.replace('_', ' ')} {building_type} {floors} floors"
    return generate_dalle_image(user_description=description)
