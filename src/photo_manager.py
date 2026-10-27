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


def scan_photo_folders(root_path="photos/", cutoff_date: Optional[datetime] = None) -> List[Dict]:
    root = Path(root_path)
    cutoff = cutoff_date or datetime(2026, 8, 10)
    if not root.exists():
        root.mkdir(parents=True)
        (root / "README.txt").write_text(
            "Create one sub-folder per photo group here, e.g. photos/our_family/,\n"
            "and drop .jpg/.png files inside.\n")
        log.warning("Created %s - add photo sub-folders to it.", root)
        return []
    folders = []
    for sub in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        files = sorted(f for f in sub.iterdir() if f.suffix.lower() in IMAGE_EXTS)
        photos = [p for p in (_build_photo(f, cutoff, sub.name) for f in files) if p]
        folders.append({"name": sub.name, "path": str(sub),
                        "photo_count": len(photos), "photos": photos})
    return folders
