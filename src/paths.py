"""Where files live: bundled read-only resources vs. writable per-user data."""
import sys
from pathlib import Path

from platformdirs import user_cache_dir, user_config_dir

APP_NAME = "CartersScrapbooker"


def resource_root() -> Path:
    """Folder holding bundled files (templates, assets): PyInstaller's unpack dir, else the repo root."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def resource_path(*parts) -> Path:
    return resource_root().joinpath(*parts)


def user_dir() -> Path:
    """Writable config/data folder (created on demand)."""
    p = Path(user_config_dir(APP_NAME, appauthor=False))
    p.mkdir(parents=True, exist_ok=True)
    return p


def user_templates_dir() -> Path:
    p = user_dir() / "templates"
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_dir() -> Path:
    p = Path(user_cache_dir(APP_NAME, appauthor=False))
    p.mkdir(parents=True, exist_ok=True)
    return p
