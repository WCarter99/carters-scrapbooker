"""Global defaults from .env, persisted user preferences in config.json."""
import json
import logging
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
log = logging.getLogger("scrapbook")


def load_env_config() -> dict:
    raw = dotenv_values(ROOT / ".env")

    def num(key, default):
        try:
            return float(raw.get(key, default))
        except ValueError:
            return float(default)

    return {
        "FONT_FAMILY": raw.get("FONT_FAMILY", "serif"),
        "FONT_SIZE": int(num("FONT_SIZE", 64)),
        "TEXT_COLOR": raw.get("TEXT_COLOR", "white"),
        "TEXT_BG_COLOR": raw.get("TEXT_BG_COLOR", "rgba(0, 0, 0, 0.5)"),
        "FULLSCREEN": str(raw.get("FULLSCREEN", "true")).lower() in ("1", "true", "yes"),
        "METADATA_CUTOFF_DATE": raw.get("METADATA_CUTOFF_DATE", "2026-08-10"),
        "DEFAULT_SPEED": num("DEFAULT_SPEED", 7),
        "MIN_SPEED": num("MIN_SPEED", 0.5),
        "MAX_SPEED": num("MAX_SPEED", 30),
        "DEFAULT_PLAYBACK_MODE": raw.get("DEFAULT_PLAYBACK_MODE", "random_all"),
        "ENABLED_TEMPLATES": [t.strip() for t in raw.get("ENABLED_TEMPLATES", "").split(",") if t.strip()],
        "DESIGNER_PORT": int(num("DESIGNER_PORT", 5000)),
    }


def load_user_config() -> dict:
    env = load_env_config()
    cfg = {
        "playback_mode": env["DEFAULT_PLAYBACK_MODE"],
        "speed": env["DEFAULT_SPEED"],
        "enabled_templates": env["ENABLED_TEMPLATES"],
        "selected_folders": None,  # None = all folders
        "last_session": {"folders_used": [], "photos_shown": 0},
    }
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text()))
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Ignoring unreadable config.json: %s", e)
    cfg["speed"] = max(env["MIN_SPEED"], min(env["MAX_SPEED"], float(cfg["speed"])))
    return cfg


def save_user_config(config: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(config, indent=2))
    except OSError as e:
        log.warning("Could not save config.json: %s", e)


def get_setting(key, default=None):
    """User config takes precedence over .env defaults."""
    user = load_user_config()
    if key in user:
        return user[key]
    return load_env_config().get(key, default)
