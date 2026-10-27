"""Image, EXIF and text-rendering helpers."""
import logging
import re
from datetime import datetime
from typing import Optional, Tuple

import pygame
from PIL import Image, ImageOps

log = logging.getLogger("scrapbook")

EXIF_IFD = 0x8769
TAG_DATETIME_ORIGINAL = 36867
TAG_DATETIME = 306
TAG_ORIENTATION = 274


def parse_color(value, default=(255, 255, 255, 255)) -> Tuple[int, int, int, int]:
    """Parse '#rrggbb', 'rgb()', 'rgba()' (alpha 0-1) or a named colour."""
    if value is None:
        return default
    if isinstance(value, (tuple, list)):
        return tuple(value) + (255,) * (4 - len(value))
    s = str(value).strip()
    m = re.match(r"rgba?\(([^)]*)\)", s, re.I)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        try:
            r, g, b = (int(float(p)) for p in parts[:3])
            a = float(parts[3]) if len(parts) > 3 else 1.0
            return (r, g, b, int(max(0.0, min(1.0, a)) * 255))
        except ValueError:
            return default
    try:
        c = pygame.Color(s)
        return (c.r, c.g, c.b, c.a)
    except ValueError:
        return default


def extract_exif_date(image_path) -> Optional[datetime]:
    try:
        with Image.open(image_path) as img:
            exif = img.getexif()
            raw = exif.get_ifd(EXIF_IFD).get(TAG_DATETIME_ORIGINAL) or exif.get(TAG_DATETIME)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode(errors="ignore")
        return datetime.strptime(raw.strip()[:19], "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def format_date_caption(date: datetime, full: bool = False) -> str:
    return date.strftime("%B %Y") if full else date.strftime("%Y")


def get_image_aspect_ratio(image_path) -> float:
    """width/height, accounting for EXIF rotation."""
    with Image.open(image_path) as img:
        w, h = img.size
        if img.getexif().get(TAG_ORIENTATION) in (5, 6, 7, 8):
            w, h = h, w
    return w / h if h else 1.0


def load_pil(image_path) -> Image.Image:
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def pil_to_surface(img: Image.Image) -> pygame.Surface:
    return pygame.image.frombytes(img.tobytes(), img.size, "RGB")


def crop_image_to_fit(image_path, target_width, target_height) -> pygame.Surface:
    """Centre-crop the image to exactly target size (object_fit: crop_center)."""
    img = load_pil(image_path)
    img = ImageOps.fit(img, (int(target_width), int(target_height)),
                       Image.LANCZOS, centering=(0.5, 0.5))
    return pil_to_surface(img)


def resize_and_crop_center(image: pygame.Surface, zone_width, zone_height,
                           aspect_ratio_range=None) -> pygame.Surface:
    """Scale an already-loaded surface to cover the zone, cropping from centre."""
    zw, zh = int(zone_width), int(zone_height)
    iw, ih = image.get_size()
    scale = max(zw / iw, zh / ih)
    nw, nh = max(zw, round(iw * scale)), max(zh, round(ih * scale))
    scaled = pygame.transform.smoothscale(image, (nw, nh))
    out = pygame.Surface((zw, zh))
    out.blit(scaled, ((zw - nw) // 2, (zh - nh) // 2))
    return out


def _wrap(text, font, max_w):
    lines = []
    for para in str(text).split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = f"{cur} {word}".strip()
            if font.size(trial)[0] <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def render_text_on_surface(text, font, color, bg_color, width, height,
                           padding=20, alignment="center",
                           vertical_align="center") -> pygame.Surface:
    surf = pygame.Surface((int(width), int(height)), pygame.SRCALPHA)
    surf.fill(parse_color(bg_color, (0, 0, 0, 0)))
    if not text:
        return surf
    col = parse_color(color)
    lines = _wrap(text, font, width - 2 * padding)
    lh = font.get_linesize()
    total = lh * len(lines)
    if vertical_align == "top":
        y = padding
    elif vertical_align == "bottom":
        y = height - padding - total
    else:
        y = (height - total) // 2
    for line in lines:
        r = font.render(line, True, col[:3])
        if alignment == "left":
            x = padding
        elif alignment == "right":
            x = width - padding - r.get_width()
        else:
            x = (width - r.get_width()) // 2
        surf.blit(r, (x, y))
        y += lh
    return surf
