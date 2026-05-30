"""
Deterministic 2D building elevation renderer.

Palette is derived from the user's natural language description — no hardcoded
style keys. Keywords like "brick", "gothic", "glass tower", "marble palace"
are detected and mapped to colors, window shapes, and roof styles.

Background is always #D3D3D3.
"""

from __future__ import annotations

from io import BytesIO
from typing import Tuple

from PIL import Image, ImageDraw

BG: Tuple[int, int, int] = (211, 211, 211)   # #D3D3D3
CANVAS_W = 800
CANVAS_H = 1000
GROUND_Y = 870

SKYSCRAPER_FLOOR_H = 14
SKYSCRAPER_BASE_W  = 190
HOUSE_STOREY_H     = 80
HOUSE_BASE_W       = 280
SUBURBAN_FLOOR_H   = 18
SUBURBAN_BASE_W    = 360
SIZE_MULT = {"small": 0.72, "medium": 1.0, "large": 1.32}


# ── Palette derivation from natural language ────────────────────────────────────

def _derive_palette(description: str) -> dict:
    """
    Build a rendering palette from free-form text.
    Checks material → archetype → color keywords in priority order.
    Falls back to a neutral stone palette if nothing matches.
    """
    t = description.lower()

    # ── Architectural archetypes (checked first — most specific) ──────────────
    if any(w in t for w in ['gothic', 'cathedral', 'medieval', 'castle', 'fortress',
                              'church', 'chapel', 'abbey', 'monastery', 'dungeon']):
        return {
            "facade_a": (100,  98, 108), "facade_b": (118, 116, 126),
            "window":   (140, 182, 210), "mullion":  ( 58,  56,  68),
            "podium":   ( 76,  74,  86), "roof":     ( 48,  46,  60),
            "shadow":   (190, 188, 192), "accent":   ( 80,  78,  92),
            "win_mode": "pointed",       "roof_style": "spire",
        }

    if any(w in t for w in ['baroque', 'palace', 'mansion', 'manor', 'chateau',
                              'château', 'estate', 'ornate', 'gilded', 'palatial',
                              'grand hotel', 'opera house']):
        return {
            "facade_a": (200, 182, 150), "facade_b": (216, 200, 168),
            "window":   (178, 212, 232), "mullion":  (140, 118,  88),
            "podium":   (168, 148, 116), "roof":     (130, 108,  78),
            "shadow":   (190, 184, 174), "accent":   (180, 150, 110),
            "win_mode": "arched",        "roof_style": "pediment",
        }

    if any(w in t for w in ['art deco', 'deco', '1920s', 'stepped crown',
                              'zigzag', 'gold fin', 'chrysler']):
        return {
            "facade_a": (232, 218, 192), "facade_b": (246, 232, 206),
            "window":   (196, 218, 236), "mullion":  (196, 156,  72),
            "podium":   (176, 136,  52), "roof":     (160, 120,  40),
            "shadow":   (190, 184, 174), "accent":   (196, 156,  72),
            "win_mode": "strip",         "roof_style": "stepped",
        }

    if any(w in t for w in ['neoclassical', 'classical', 'greek revival', 'roman column',
                              'museum', 'courthouse', 'parliament', 'capitol', 'senate',
                              'library', 'university', 'temple', 'pantheon', 'embassy',
                              'city hall', 'town hall', 'memorial']):
        return {
            "facade_a": (238, 234, 222), "facade_b": (248, 244, 232),
            "window":   (186, 216, 238), "mullion":  (176, 170, 156),
            "podium":   (210, 202, 184), "roof":     (196, 188, 170),
            "shadow":   (192, 190, 184), "accent":   (196, 188, 170),
            "win_mode": "arched",        "roof_style": "pediment",
        }

    if any(w in t for w in ['industrial', 'factory', 'warehouse', 'brewery',
                              'distillery', 'mill', 'loft', 'depot', 'shipyard',
                              'power station', 'power plant']):
        return {
            "facade_a": (136,  62,  46), "facade_b": (152,  76,  58),
            "window":   (196, 216, 224), "mullion":  ( 88, 100, 108),
            "podium":   ( 72,  84,  92), "roof":     ( 62,  74,  82),
            "shadow":   (182, 178, 176), "accent":   ( 80,  92, 100),
            "win_mode": "factory",       "roof_style": "parapet",
        }

    if any(w in t for w in ['brutalist', 'raw concrete', 'béton brut', 'prison',
                              'jail', 'bunker', 'car park', 'parking garage',
                              'soviet', 'bloc']):
        return {
            "facade_a": (148, 150, 154), "facade_b": (166, 168, 172),
            "window":   (192, 200, 210), "mullion":  (108, 110, 114),
            "podium":   (118, 120, 124), "roof":     ( 94,  96, 100),
            "shadow":   (186, 186, 186), "accent":   (120, 122, 126),
            "win_mode": "punched",       "roof_style": "flat",
        }

    if any(w in t for w in ['minimalist', 'contemporary', 'scandinavian',
                              'zen', 'sleek white', 'white facade']):
        return {
            "facade_a": (244, 244, 244), "facade_b": (232, 232, 232),
            "window":   (198, 220, 240), "mullion":  ( 32,  32,  32),
            "podium":   (200, 200, 200), "roof":     ( 28,  28,  28),
            "shadow":   (196, 196, 196), "accent":   ( 32,  32,  32),
            "win_mode": "floor2ceil",    "roof_style": "flat",
        }

    if any(w in t for w in ['retail', 'mall', 'shopping', 'commercial', 'market',
                              'supermarket', 'plaza', 'strip mall']):
        return {
            "facade_a": (198, 218, 234), "facade_b": (218, 234, 246),
            "window":   (228, 242, 252), "mullion":  ( 78,  98, 118),
            "podium":   ( 58,  78,  98), "roof":     ( 48,  66,  86),
            "shadow":   (186, 188, 190), "accent":   ( 90, 110, 130),
            "win_mode": "strip",         "roof_style": "flat",
        }

    # ── Material keywords (if no archetype matched) ────────────────────────────
    if any(w in t for w in ['glass', 'curtain wall', 'reflective', 'mirror glass',
                              'corporate', 'office tower', 'skyscraper', 'high rise',
                              'highrise', 'headquarters', 'hq', 'condo tower']):
        return {
            "facade_a": ( 82, 130, 158), "facade_b": (108, 166, 196),
            "window":   (190, 222, 242), "mullion":  ( 40,  55,  72),
            "podium":   ( 48,  62,  80), "roof":     ( 34,  46,  60),
            "shadow":   (190, 190, 190), "accent":   ( 60,  90, 120),
            "win_mode": "strip",         "roof_style": "penthouse",
        }

    if any(w in t for w in ['brick', 'red brick', 'terracotta', 'victorian house',
                              'townhouse', 'cottage', 'pub', 'inn', 'school',
                              'fire station', 'traditional']):
        return {
            "facade_a": (172,  96,  72), "facade_b": (196, 118,  88),
            "window":   (200, 218, 238), "mullion":  (128,  70,  52),
            "podium":   (138,  80,  58), "roof":     ( 96,  58,  44),
            "shadow":   (190, 184, 180), "accent":   (150,  90,  68),
            "win_mode": "punched",       "roof_style": "flat",
        }

    if any(w in t for w in ['concrete', 'cement', 'grey', 'gray']):
        return {
            "facade_a": (148, 150, 154), "facade_b": (166, 168, 172),
            "window":   (192, 200, 210), "mullion":  (108, 110, 114),
            "podium":   (118, 120, 124), "roof":     ( 94,  96, 100),
            "shadow":   (186, 186, 186), "accent":   (120, 122, 126),
            "win_mode": "punched",       "roof_style": "flat",
        }

    if any(w in t for w in ['marble', 'limestone', 'white stone', 'white marble',
                              'cream stone']):
        return {
            "facade_a": (238, 234, 222), "facade_b": (248, 244, 232),
            "window":   (186, 216, 238), "mullion":  (176, 170, 156),
            "podium":   (210, 202, 184), "roof":     (196, 188, 170),
            "shadow":   (192, 190, 184), "accent":   (196, 188, 170),
            "win_mode": "arched",        "roof_style": "flat",
        }

    if any(w in t for w in ['wood', 'timber', 'log cabin', 'cabin', 'chalet',
                              'farmhouse', 'barn']):
        return {
            "facade_a": (160, 120,  80), "facade_b": (178, 138,  96),
            "window":   (200, 218, 230), "mullion":  (110,  80,  50),
            "podium":   (128,  96,  64), "roof":     ( 90,  64,  40),
            "shadow":   (188, 182, 176), "accent":   (120,  90,  60),
            "win_mode": "punched",       "roof_style": "flat",
        }

    if any(w in t for w in ['dark', 'black', 'obsidian', 'onyx']):
        return {
            "facade_a": ( 50,  52,  58), "facade_b": ( 64,  66,  74),
            "window":   (160, 198, 228), "mullion":  ( 28,  30,  36),
            "podium":   ( 36,  38,  44), "roof":     ( 22,  24,  30),
            "shadow":   (170, 170, 172), "accent":   ( 70,  72,  80),
            "win_mode": "strip",         "roof_style": "flat",
        }

    # ── Default: neutral warm stone ────────────────────────────────────────────
    return {
        "facade_a": (190, 186, 178), "facade_b": (206, 202, 194),
        "window":   (192, 214, 234), "mullion":  (130, 126, 118),
        "podium":   (158, 154, 146), "roof":     (120, 116, 108),
        "shadow":   (190, 190, 188), "accent":   (150, 146, 138),
        "win_mode": "punched",       "roof_style": "flat",
    }


# ── Public API ──────────────────────────────────────────────────────────────────

def render_building(
    building_type: str,
    style: str,
    floors: int,
    size: str,
    user_description: str = "",
) -> bytes:
    floors = max(1, min(floors, 100))
    # Derive palette from user description; fall back to style name as hint
    p  = _derive_palette(user_description or style)
    sm = SIZE_MULT.get(size, 1.0)

    img  = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
    draw = ImageDraw.Draw(img)

    if building_type == "skyscraper":
        _skyscraper(draw, floors, sm, p)
    elif building_type == "house":
        _house(draw, floors, sm, p)
    else:
        _suburban(draw, floors, sm, p)

    _ground_line(draw)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_building_image(building_type, style, floors, size, user_description="") -> Image.Image:
    return Image.open(BytesIO(render_building(building_type, style, floors, size, user_description)))


# ── Shared helpers ──────────────────────────────────────────────────────────────

def _ground_line(draw):
    draw.line([(0, GROUND_Y), (CANVAS_W, GROUND_Y)], fill=(148, 148, 148), width=2)


def _shadow(draw, cx, rx, p):
    ry = max(8, rx // 8)
    draw.ellipse([cx - rx, GROUND_Y - ry, cx + rx, GROUND_Y + ry], fill=p["shadow"])


def _win(draw, x1, y1, x2, y2, p):
    mode  = p.get("win_mode", "punched")
    color = p["window"]
    mc    = p["mullion"]

    if mode == "arched":
        w = x2 - x1
        arch_h = min(w // 2, (y2 - y1) // 3)
        if arch_h > 2:
            draw.ellipse([x1, y1, x2, y1 + arch_h * 2], fill=color)
            draw.rectangle([x1, y1 + arch_h, x2, y2], fill=color)
        else:
            draw.rectangle([x1, y1, x2, y2], fill=color)

    elif mode == "pointed":
        mx     = (x1 + x2) // 2
        arch_h = (y2 - y1) // 3
        draw.polygon([(x1, y1 + arch_h), (mx, y1), (x2, y1 + arch_h)], fill=color)
        draw.rectangle([x1, y1 + arch_h, x2, y2], fill=color)

    elif mode == "factory":
        cols, rows = 2, 3
        pw = max(1, (x2 - x1) // cols)
        ph = max(1, (y2 - y1) // rows)
        for r in range(rows):
            for c in range(cols):
                draw.rectangle(
                    [x1 + c*pw + 1, y1 + r*ph + 1,
                     x1 + (c+1)*pw - 1, y1 + (r+1)*ph - 1],
                    fill=color,
                )

    elif mode == "floor2ceil":
        draw.rectangle([x1 + 1, y1 + 1, x2 - 1, y2 - 1], fill=color)
        mid = (y1 + y2) // 2
        draw.line([(x1 + 1, mid), (x2 - 1, mid)], fill=mc, width=1)

    else:
        draw.rectangle([x1, y1, x2, y2], fill=color)


def _podium_windows(draw, x1, y1, x2, y2, p):
    fh = y2 - y1
    wy1 = y1 + int(fh * 0.12)
    wy2 = wy1 + int(fh * 0.55)
    pw  = (x2 - x1) // 4
    for i in range(4):
        _win(draw, x1 + i*pw + 6, wy1, x1 + (i+1)*pw - 6, wy2, p)


# ── Roof treatments ─────────────────────────────────────────────────────────────

def _roof(draw, cx, t_x1, t_x2, t_y1, tw, p):
    rs = p.get("roof_style", "flat")
    rc = p["roof"]
    ac = p["accent"]

    if rs == "spire":
        spire_h = int(tw * 0.9)
        draw.polygon(
            [(t_x1 + int(tw*0.2), t_y1),
             (cx, t_y1 - spire_h),
             (t_x2 - int(tw*0.2), t_y1)],
            fill=rc,
        )
        draw.line([(cx, t_y1 - spire_h - 8), (cx, t_y1 - spire_h)], fill=ac, width=3)

    elif rs == "pediment":
        cornice_h = max(10, int(tw * 0.055))
        draw.rectangle([t_x1 - 6, t_y1 - cornice_h, t_x2 + 6, t_y1], fill=rc)
        ped_h = int(tw * 0.14)
        draw.polygon(
            [(t_x1 - 6, t_y1 - cornice_h),
             (cx, t_y1 - cornice_h - ped_h),
             (t_x2 + 6, t_y1 - cornice_h)],
            fill=ac,
        )
        draw.line(
            [(t_x1 - 6, t_y1 - cornice_h),
             (cx, t_y1 - cornice_h - ped_h),
             (t_x2 + 6, t_y1 - cornice_h)],
            fill=rc, width=2,
        )

    elif rs == "stepped":
        steps = [(1.0, 14), (0.75, 10), (0.52, 8), (0.32, 12)]
        y = t_y1
        for ratio, h in steps:
            sw = int(tw * ratio)
            draw.rectangle([cx - sw//2, y - h, cx + sw//2, y], fill=rc)
            y -= h
        draw.rectangle([cx - 5, y - 18, cx + 5, y], fill=ac)

    elif rs == "parapet":
        ph = max(12, int(tw * 0.06))
        draw.rectangle([t_x1, t_y1 - ph, t_x2, t_y1], fill=rc)
        notch_w = max(8, tw // 10)
        x = t_x1
        toggle = True
        while x < t_x2:
            if toggle:
                draw.rectangle([x, t_y1 - ph, min(x + notch_w, t_x2), t_y1 - ph//2], fill=BG)
            x += notch_w
            toggle = not toggle

    else:  # flat / penthouse
        roof_h = max(10, int(tw * 0.07))
        draw.rectangle([t_x1, t_y1 - roof_h, t_x2, t_y1], fill=rc)
        if rs == "penthouse":
            pen_w = int(tw * 0.34)
            pen_h = int(roof_h * 1.6)
            draw.rectangle(
                [cx - pen_w//2, t_y1 - roof_h - pen_h,
                 cx + pen_w//2, t_y1 - roof_h],
                fill=rc,
            )


# ── Skyscraper ──────────────────────────────────────────────────────────────────

def _skyscraper(draw, floors, sm, p):
    cx  = CANVAS_W // 2
    tw  = int(SKYSCRAPER_BASE_W * sm)
    pw  = int(tw * 1.22)
    wm  = p.get("win_mode", "strip")
    rs  = p.get("roof_style", "flat")

    podium_floors = min(4, floors)
    if GROUND_Y - floors * SKYSCRAPER_FLOOR_H < 60:
        floors = (GROUND_Y - 60) // SKYSCRAPER_FLOOR_H
    podium_floors = min(podium_floors, floors)

    tower_h  = floors * SKYSCRAPER_FLOOR_H
    podium_h = podium_floors * SKYSCRAPER_FLOOR_H

    t_x1 = cx - tw // 2;  t_x2 = cx + tw // 2
    p_x1 = cx - pw // 2;  p_x2 = cx + pw // 2
    t_y1 = GROUND_Y - tower_h
    p_y1 = GROUND_Y - podium_h

    _shadow(draw, cx, pw // 2, p)

    use_setback  = (rs not in ("stepped", "spire")) and floors > 6
    setback_start = floors - 2
    sb_w  = int(tw * 0.82)
    sb_x1 = cx - sb_w // 2;  sb_x2 = cx + sb_w // 2

    draw.rectangle([p_x1, p_y1, p_x2, GROUND_Y], fill=p["podium"])

    for i in range(podium_floors, floors):
        fy2 = GROUND_Y - i * SKYSCRAPER_FLOOR_H
        fy1 = fy2 - SKYSCRAPER_FLOOR_H

        is_sb = use_setback and i >= setback_start
        x1 = sb_x1 if is_sb else t_x1
        x2 = sb_x2 if is_sb else t_x2

        color = p["facade_a"] if i % 2 == 0 else p["facade_b"]
        draw.rectangle([x1, fy1, x2, fy2], fill=color)
        floor_w = x2 - x1

        if wm == "strip":
            wy1 = fy1 + int(SKYSCRAPER_FLOOR_H * 0.15)
            wy2 = fy1 + int(SKYSCRAPER_FLOOR_H * 0.82)
            _win(draw, x1 + 5, wy1, x2 - 5, wy2, p)
        elif wm == "floor2ceil":
            _win(draw, x1 + 3, fy1 + 1, x2 - 3, fy2 - 1, p)
        else:
            win_w = max(12, int(floor_w * 0.13))
            gap   = max(6,  int(floor_w * 0.06))
            count = max(1, (floor_w + gap) // (win_w + gap))
            total = count * win_w + (count - 1) * gap
            start_x = x1 + (floor_w - total) // 2
            wy1 = fy1 + int(SKYSCRAPER_FLOOR_H * 0.10)
            wy2 = fy2 - int(SKYSCRAPER_FLOOR_H * 0.10)
            for k in range(count):
                wx1 = start_x + k * (win_w + gap)
                _win(draw, wx1, wy1, wx1 + win_w, wy2, p)

    for i in range(podium_floors, floors + 1):
        fy  = GROUND_Y - i * SKYSCRAPER_FLOOR_H
        is_sb = use_setback and i >= setback_start
        x1  = sb_x1 if is_sb else t_x1
        x2  = sb_x2 if is_sb else t_x2
        draw.line([(x1, fy), (x2, fy)], fill=p["mullion"], width=1)

    if wm in ("strip", "floor2ceil"):
        gap = max(28, tw // 6)
        mx  = t_x1 + gap
        while mx < t_x2:
            draw.line([(mx, t_y1), (mx, p_y1)], fill=p["mullion"], width=2)
            mx += gap

    if wm == "arched":
        gap = max(30, tw // 5)
        mx  = t_x1
        while mx <= t_x2:
            draw.line([(mx, t_y1), (mx, p_y1)], fill=p["accent"], width=3)
            mx += gap

    if wm == "pointed":
        for i in range(podium_floors, floors, 4):
            fy = GROUND_Y - i * SKYSCRAPER_FLOOR_H
            draw.line([(t_x1, fy), (t_x2, fy)], fill=p["accent"], width=2)

    _roof(draw, cx, t_x1, t_x2, t_y1, tw, p)
    _podium_windows(draw, p_x1, p_y1, p_x2, GROUND_Y, p)


# ── House ───────────────────────────────────────────────────────────────────────

def _house(draw, floors, sm, p):
    floors = max(1, min(floors, 3))
    cx     = CANVAS_W // 2
    wm     = p.get("win_mode", "punched")
    w      = int(HOUSE_BASE_W * sm)
    wall_h = floors * HOUSE_STOREY_H

    roof_pitch = 0.55 if wm == "pointed" else (0.30 if wm == "floor2ceil" else 0.40)
    roof_h     = int(w * roof_pitch)

    x1       = cx - w // 2;  x2 = cx + w // 2
    wall_y1  = GROUND_Y - wall_h
    roof_top = wall_y1 - roof_h

    _shadow(draw, cx, w // 2, p)
    draw.rectangle([x1, wall_y1, x2, GROUND_Y], fill=p["facade_a"])

    for f in range(1, floors):
        fy = GROUND_Y - f * HOUSE_STOREY_H
        draw.line([(x1, fy), (x2, fy)], fill=p["mullion"], width=2)

    if wm == "pointed":
        draw.polygon([(x1 - 10, wall_y1), (cx, roof_top), (x2 + 10, wall_y1)], fill=p["roof"])
        draw.line([(x1-10, wall_y1),(cx, roof_top),(x2+10, wall_y1)], fill=p["mullion"], width=2)
        for fx in [cx - w//4, cx, cx + w//4]:
            draw.line([(fx, wall_y1 - 6), (fx, wall_y1 - 6 - int(roof_h*0.4))],
                      fill=p["accent"], width=3)
    elif wm == "arched":
        draw.polygon([(x1 - 14, wall_y1), (cx, roof_top), (x2 + 14, wall_y1)], fill=p["roof"])
        draw.line([(x1-14, wall_y1),(cx, roof_top),(x2+14, wall_y1)], fill=p["mullion"], width=2)
        draw.rectangle([x1 - 6, wall_y1 - 8, x2 + 6, wall_y1], fill=p["accent"])
    else:
        draw.polygon([(x1 - 14, wall_y1), (cx, roof_top), (x2 + 14, wall_y1)], fill=p["roof"])
        draw.line([(x1-14, wall_y1),(cx, roof_top),(x2+14, wall_y1)], fill=p["mullion"], width=2)

    win_w = int(w * 0.18);  win_h = int(HOUSE_STOREY_H * 0.48)
    mx    = int(w * 0.18)
    for f in range(floors):
        fy_top = GROUND_Y - (f + 1) * HOUSE_STOREY_H
        wy1    = fy_top + int(HOUSE_STOREY_H * 0.22)
        wy2    = wy1 + win_h
        _win(draw, x1 + mx, wy1, x1 + mx + win_w, wy2, p)
        _win(draw, x2 - mx - win_w, wy1, x2 - mx, wy2, p)

    dw = int(w * 0.14);  dh = int(HOUSE_STOREY_H * 0.64)
    draw.rectangle([cx - dw//2, GROUND_Y - dh, cx + dw//2, GROUND_Y], fill=p["mullion"])

    if wm in ("punched", "arched"):
        cw = int(w * 0.07);  ch = int(roof_h * 0.65)
        cx2 = cx + int(w * 0.18)
        draw.rectangle([cx2, roof_top + int(roof_h*0.1), cx2 + cw, wall_y1], fill=p["podium"])


# ── Suburban ────────────────────────────────────────────────────────────────────

def _suburban(draw, floors, sm, p):
    floors = max(2, min(floors, 15))
    cx     = CANVAS_W // 2
    wm     = p.get("win_mode", "strip")
    w      = int(SUBURBAN_BASE_W * sm)

    PF     = min(2, floors)
    bldg_h = floors * SUBURBAN_FLOOR_H
    if GROUND_Y - bldg_h < 80:
        floors = (GROUND_Y - 80) // SUBURBAN_FLOOR_H
        bldg_h = floors * SUBURBAN_FLOOR_H
    podium_h = min(PF, floors) * SUBURBAN_FLOOR_H

    x1   = cx - w // 2;     x2   = cx + w // 2
    b_y1 = GROUND_Y - bldg_h
    p_y1 = GROUND_Y - podium_h

    _shadow(draw, cx, w // 2 + 10, p)
    draw.rectangle([x1 - 16, p_y1, x2 + 16, GROUND_Y], fill=p["podium"])

    BAYS  = max(3, w // 90)
    bay_w = w // BAYS

    for i in range(PF, floors):
        fy2   = GROUND_Y - i * SUBURBAN_FLOOR_H
        fy1   = fy2 - SUBURBAN_FLOOR_H
        color = p["facade_a"] if i % 2 == 0 else p["facade_b"]
        draw.rectangle([x1, fy1, x2, fy2], fill=color)

        if wm == "strip":
            wy1 = fy1 + int(SUBURBAN_FLOOR_H * 0.14)
            wy2 = fy1 + int(SUBURBAN_FLOOR_H * 0.80)
            for bay in range(BAYS):
                bx1 = x1 + bay * bay_w
                _win(draw, bx1 + int(bay_w*0.08), wy1, bx1 + int(bay_w*0.44), wy2, p)
                _win(draw, bx1 + int(bay_w*0.56), wy1, bx1 + int(bay_w*0.92), wy2, p)
        elif wm == "floor2ceil":
            wy1 = fy1 + 1;  wy2 = fy2 - 1
            for bay in range(BAYS):
                bx1 = x1 + bay * bay_w
                _win(draw, bx1 + 3, wy1, bx1 + bay_w - 3, wy2, p)
        else:
            for bay in range(BAYS):
                bx1 = x1 + bay * bay_w
                bx2 = bx1 + bay_w
                mid = (bx1 + bx2) // 2
                ww  = max(10, int(bay_w * 0.28))
                wy1 = fy1 + int(SUBURBAN_FLOOR_H * 0.12)
                wy2 = fy2 - int(SUBURBAN_FLOOR_H * 0.10)
                _win(draw, mid - ww - 2, wy1, mid - 2, wy2, p)
                _win(draw, mid + 2, wy1, mid + ww + 2, wy2, p)

    for bay in range(1, BAYS):
        px = x1 + bay * bay_w
        draw.line([(px, b_y1), (px, p_y1)], fill=p["mullion"], width=3)

    for i in range(PF, floors + 1):
        fy = GROUND_Y - i * SUBURBAN_FLOOR_H
        draw.line([(x1, fy), (x2, fy)], fill=p["mullion"], width=1)

    rs = p.get("roof_style", "flat")
    ph = max(10, int(w * 0.028))
    if rs == "pediment":
        draw.rectangle([x1, b_y1 - ph, x2, b_y1], fill=p["accent"])
        ped_h = int(w * 0.06)
        draw.polygon(
            [(x1 - 6, b_y1 - ph), (cx, b_y1 - ph - ped_h), (x2 + 6, b_y1 - ph)],
            fill=p["roof"],
        )
    elif rs == "parapet":
        draw.rectangle([x1, b_y1 - ph, x2, b_y1], fill=p["roof"])
        draw.rectangle([x1 - 8, b_y1, x2 + 8, b_y1 + 4], fill=p["roof"])
        notch = max(8, w // 12)
        nx = x1; tog = True
        while nx < x2:
            if tog:
                draw.rectangle([nx, b_y1 - ph, min(nx+notch, x2), b_y1 - ph//2], fill=BG)
            nx += notch; tog = not tog
    else:
        draw.rectangle([x1, b_y1 - ph, x2, b_y1], fill=p["roof"])
        draw.rectangle([x1 - 8, b_y1, x2 + 8, b_y1 + 4], fill=p["roof"])

    _podium_windows(draw, x1 - 16, p_y1, x2 + 16, GROUND_Y, p)
