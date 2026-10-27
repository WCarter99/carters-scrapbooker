"""User settings: built-in defaults merged with a JSON file in the per-user config dir."""
import copy
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import paths

log = logging.getLogger("scrapbook")
CONFIG_VERSION = 1
CONFIG_NAME = "config.json"

DEFAULTS = {
    "version": CONFIG_VERSION,
    "playback_mode": "random_all",        # random_all | rotating_folders
    "multi_photo_source": "mixed",        # mixed | same
    "speed": 7.0,
    "min_speed": 0.5,
    "max_speed": 30.0,
    "enabled_templates": None,            # None = all templates
    "source_folders": [],                 # [{"path": str, "enabled": bool}]
    "font_family": "Noto Serif",
    "font_size": 64,
    "text_color": "white",
    "text_bg_color": "rgba(0, 0, 0, 0.5)",
    "caption_cutoff_date": "2026-08-10",  # photos taken before this show their year
    "fullscreen": True,
    "last_session": {"folders_used": [], "photos_shown": 0},
}


def config_path() -> Path:
    return paths.user_dir() / CONFIG_NAME


def _migrate(raw: dict) -> dict:
    """Bring an old config.json up to CONFIG_VERSION (older files had no version)."""
    raw = dict(raw)
    if "selected_folders" in raw:  # pre-1.0 format: folder names under the bundled photos/ dir
        raw.pop("selected_folders")
    raw["version"] = CONFIG_VERSION
    return raw


def load_config(path=None) -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    path = Path(path) if path else config_path()
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                cfg.update(_migrate(raw))
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Ignoring unreadable %s: %s", path.name, e)
    cfg["speed"] = clamp_speed(cfg, cfg["speed"])
    if not parse_cutoff(cfg["caption_cutoff_date"]):
        cfg["caption_cutoff_date"] = DEFAULTS["caption_cutoff_date"]
    return cfg


def save_config(cfg: dict, path=None) -> None:
    """Write atomically so a crash mid-save can't leave a corrupt file."""
    path = Path(path) if path else config_path()
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as e:
        log.warning("Could not save %s: %s", path.name, e)


def clamp_speed(cfg: dict, value) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = DEFAULTS["speed"]
    return max(cfg["min_speed"], min(cfg["max_speed"], v))


def parse_cutoff(value):
    """YYYY-MM-DD -> datetime, or None if invalid."""
    try:
        return datetime.strptime(str(value), "%Y-%m-%d")
    except ValueError:
        return None


def text_env(cfg: dict) -> dict:
    """The font/colour defaults template rendering falls back to."""
    return {"FONT_FAMILY": cfg["font_family"], "FONT_SIZE": cfg["font_size"],
            "TEXT_COLOR": cfg["text_color"], "TEXT_BG_COLOR": cfg["text_bg_color"]}
