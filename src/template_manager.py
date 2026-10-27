"""Load, validate and render scrapbook templates."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import pygame

import paths
from utils import (crop_image_to_fit, parse_color, render_text_on_surface)

log = logging.getLogger("scrapbook")
RECT_KEYS = ("x", "y", "width", "height")


def validate_template(t) -> bool:
    try:
        if not isinstance(t, dict):
            raise ValueError("not an object")
        for k in ("id", "name", "canvas_width", "canvas_height"):
            if k not in t:
                raise ValueError(f"missing '{k}'")
        if not t.get("photo_zones"):
            raise ValueError("needs at least one photo zone")
        for z in list(t["photo_zones"]) + list(t.get("text_zones", [])):
            for k in RECT_KEYS:
                if not isinstance(z.get(k), (int, float)):
                    raise ValueError(f"zone '{z.get('id')}' bad '{k}'")
            if z["width"] <= 0 or z["height"] <= 0:
                raise ValueError(f"zone '{z.get('id')}' has non-positive size")
        for z in t["photo_zones"]:
            r = z.get("aspect_ratio_range", [0, 100])
            if len(r) != 2 or r[0] > r[1]:
                raise ValueError(f"zone '{z.get('id')}' bad aspect_ratio_range")
        return True
    except (ValueError, TypeError, AttributeError) as e:
        log.warning("Invalid template: %s", e)
        return False


def load_templates(template_dir) -> List[Dict]:
    out = []
    for f in sorted(Path(template_dir).glob("*.json")):
        try:
            t = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Skipping %s: %s", f.name, e)
            continue
        if validate_template(t):
            t["_file"] = f.stem
            out.append(t)
        else:
            log.warning("Skipping invalid template %s", f.name)
    return out


def load_all_templates() -> List[Dict]:
    """Bundled templates plus the user's own; a user template replaces a bundled one with the same id."""
    merged = {}
    for source, d in (("bundled", paths.resource_path("templates")), ("user", paths.user_templates_dir())):
        for t in load_templates(d):
            t["_source"] = source
            merged[t["id"]] = t
    return sorted(merged.values(), key=lambda t: t["name"].lower())


def template_matches(t: Dict, names) -> bool:
    return t["_file"] in names or t["id"] in names


def _ratio_distance(ratio, rng) -> float:
    lo, hi = rng
    return 0.0 if lo <= ratio <= hi else min(abs(ratio - lo), abs(ratio - hi))


def zone_distance(photo: Dict, zone: Dict) -> float:
    return _ratio_distance(photo["aspect_ratio"], zone.get("aspect_ratio_range", [0, 100]))


def select_best_photo_for_zone(photos: List[Dict], photo_zone: Dict) -> Optional[Dict]:
    """First photo within the zone's ratio range, else the closest one."""
    if not photos:
        return None
    best = min(photos, key=lambda p: zone_distance(p, photo_zone))
    if zone_distance(best, photo_zone) > 0:
        log.warning("No photo in range for zone %s; using closest (%s)",
                    photo_zone.get("id"), best["filename"])
    return best


def pick_template(templates: List[Dict], photo: Dict, rng) -> Dict:
    """Random template among those with a zone accepting this photo's ratio,
    falling back to the template with the closest zone."""
    fits = [t for t in templates if any(zone_distance(photo, z) == 0 for z in t["photo_zones"])]
    if fits:
        return rng.choice(fits)
    return min(templates, key=lambda t: min(zone_distance(photo, z) for z in t["photo_zones"]))


def render_template(template: Dict, photo_paths, caption_text: Optional[str],
                    env: Optional[Dict] = None) -> pygame.Surface:
    """Render to a canvas-sized surface. `photo_paths` is a path or a list
    (one per photo zone, in order)."""
    env = env or {}
    if isinstance(photo_paths, (str, Path)):
        photo_paths = [photo_paths]
    cw, ch = int(template["canvas_width"]), int(template["canvas_height"])
    canvas = pygame.Surface((cw, ch))
    canvas.fill(parse_color(template.get("background_color", "#ffffff"))[:3])

    bg = template.get("background_image")
    if bg:
        try:
            canvas.blit(crop_image_to_fit(paths.resource_path(bg), cw, ch), (0, 0))
        except Exception as e:
            log.warning("Background image failed: %s", e)

    for zone, path in zip(template["photo_zones"], photo_paths):
        try:
            img = crop_image_to_fit(path, zone["width"], zone["height"])
            canvas.blit(img, (zone["x"], zone["y"]))
        except Exception as e:
            log.warning("Could not draw %s: %s", path, e)

    pygame.font.init()
    for zone in template.get("text_zones", []):
        size = int(zone.get("font_size", env.get("FONT_SIZE", 64)))
        font = pygame.font.SysFont(zone.get("font_family", env.get("FONT_FAMILY", "serif")), size)
        text = render_text_on_surface(
            caption_text, font,
            zone.get("text_color", env.get("TEXT_COLOR", "white")),
            zone.get("background_color", env.get("TEXT_BG_COLOR", "rgba(0,0,0,0.5)")),
            zone["width"], zone["height"], zone.get("padding", 20),
            zone.get("alignment", "center"), zone.get("vertical_align", "center"))
        canvas.blit(text, (zone["x"], zone["y"]))
    return canvas
