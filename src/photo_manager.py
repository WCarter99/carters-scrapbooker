"""Photo discovery, EXIF captions and aspect ratios."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from utils import (extract_exif_date, format_date_caption,
                   get_image_aspect_ratio)

log = logging.getLogger("scrapbook")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}


def get_aspect_ratio(image_path) -> float:
    return get_image_aspect_ratio(image_path)


def get_photo_caption(exif_date: Optional[datetime], cutoff_date: datetime) -> Optional[str]:
    """No EXIF or date >= cutoff -> no caption; earlier -> the year."""
    if exif_date is None or exif_date >= cutoff_date:
        return None
    return format_date_caption(exif_date)


def _build_photo(path: Path, cutoff: datetime, folder: str = "") -> Optional[Dict]:
    try:
        ratio = get_aspect_ratio(path)
    except Exception as e:
        log.warning("Skipping unreadable image %s: %s", path, e)
        return None
    date = extract_exif_date(path)
    return {
        "filename": path.name,
        "folder": folder,
        "path": str(path),
        "exif_date": date.isoformat() if date else None,
        "caption_text": get_photo_caption(date, cutoff),
        "aspect_ratio": ratio,
    }


def scan_folder(path, cutoff: datetime) -> Dict:
    """Scan one folder (non-recursive) into {name, path, photo_count, photos}."""
    path = Path(path)
    files = sorted(f for f in path.iterdir() if f.suffix.lower() in IMAGE_EXTS) if path.is_dir() else []
    photos = [p for p in (_build_photo(f, cutoff, path.name) for f in files) if p]
    return {"name": path.name, "path": str(path), "photo_count": len(photos), "photos": photos}
