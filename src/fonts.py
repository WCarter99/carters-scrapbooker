"""Bundled fonts, with a system-font fallback for names we don't ship."""
from functools import lru_cache

import pygame

import paths

# family -> (regular file, bold file) under assets/fonts/
BUNDLED = {
    "Noto Serif": ("NotoSerif-Regular.ttf", "NotoSerif-Bold.ttf"),
    "Noto Sans": ("NotoSans-Regular.ttf", "NotoSans-Bold.ttf"),
}
DEFAULT_FAMILY = "Noto Serif"


def family_names():
    return list(BUNDLED)


@lru_cache(maxsize=64)
def get_font(family, size, bold=False) -> pygame.font.Font:
    pygame.font.init()
    files = BUNDLED.get(family) or BUNDLED.get(str(family).title())
    if files:
        path = paths.resource_path("assets", "fonts", files[1] if bold else files[0])
        if path.exists():
            return pygame.font.Font(str(path), int(size))
    return pygame.font.SysFont(family, int(size), bold=bold)  # legacy names such as "serif"
