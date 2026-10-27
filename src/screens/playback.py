"""Slideshow playback."""
import pygame

import fonts
import template_manager as tm
import config_manager as cm
from playback import MULTI_LABELS, MULTI_MODES, PhotoPool, build_slide
from screens.base import Screen

HINT = "SPACE pause  |  ← → prev/next  |  ↑ ↓ speed  |  M photo mix  |  S reshuffle  |  ESC menu"
KEYS = {pygame.K_ESCAPE: "menu", pygame.K_r: "menu", pygame.K_q: "menu", pygame.K_SPACE: "pause",
        pygame.K_n: "next", pygame.K_RIGHT: "next", pygame.K_p: "prev", pygame.K_LEFT: "prev",
        pygame.K_s: "reshuffle", pygame.K_m: "mix", pygame.K_UP: "faster", pygame.K_DOWN: "slower",
        pygame.K_LESS: "faster", pygame.K_COMMA: "faster", pygame.K_GREATER: "slower", pygame.K_PERIOD: "slower"}
MAX_HISTORY = 50


class PlaybackScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.cache = {}

    def enter(self, mode="random"):
        app, cfg = self.app, self.app.cfg
        self.mode = mode
        self.folders = app.library.active_folders()
        self.templates = app.enabled_templates()
        self.bail = not self.folders  # nothing to show (e.g. still rescanning): return to the menu
        if self.bail:
            return
        self.env = cm.text_env(cfg)
        cfg["playback_mode"] = "random_all" if mode == "random" else "rotating_folders"
        cfg["last_session"] = {"folders_used": [f["name"] for f in self.folders], "photos_shown": 0}
        self.was_fullscreen = app.fullscreen
        if cfg["fullscreen"] != app.fullscreen:
            app.set_fullscreen(cfg["fullscreen"])
        pygame.mouse.set_visible(False)
        self.small = fonts.get_font("Noto Sans", 28)
        self.big = fonts.get_font("Noto Sans", 72, True)
        self.shown, self.paused, self.elapsed = 0, False, 0.0
        self.flash, self.flash_t = HINT, 6.0
        self.cache = {}
        self.restart()

    def exit(self):
        if self.bail:
            return
        self.app.cfg["last_session"]["photos_shown"] = self.shown
        self.app.save()
        pygame.mouse.set_visible(True)
        if self.app.fullscreen:
            self.app.set_fullscreen(False)

    def on_resize(self):
        self.cache.clear()

    # ---- slide history -----------------------------------------------------
    def restart(self):
        self.pool = PhotoPool(self.folders)
        self.history, self.idx, self.elapsed = [], -1, 0.0
        self.go_next()

    def go_next(self):
        if self.idx + 1 < len(self.history):
            self.idx += 1
            return
        slide = build_slide(self.pool, self.templates, self.mode, self.app.cfg["multi_photo_source"])
        self.history.append(slide)
        self.idx = len(self.history) - 1
        self.shown += slide["count"]
        if len(self.history) > MAX_HISTORY:
            self.history.pop(0)
            self.idx -= 1

    def scaled(self, slide):
        key = id(slide)
        if key not in self.cache:
            canvas = tm.render_template(slide["template"], slide["paths"], slide["caption"], self.env)
            sw, sh = self.app.screen.get_size()
            s = min(sw / canvas.get_width(), sh / canvas.get_height())
            self.cache.clear()
            self.cache[key] = pygame.transform.smoothscale(
                canvas, (int(canvas.get_width() * s), int(canvas.get_height() * s)))
        return self.cache[key]

    # ---- loop hooks --------------------------------------------------------
    def handle_event(self, e):
        if self.bail or e.type != pygame.KEYDOWN or e.key not in KEYS:
            return
        act, cfg = KEYS[e.key], self.app.cfg
        lo, hi = cfg["min_speed"], cfg["max_speed"]
        if act == "menu":
            self.app.goto("menu")
        elif act == "pause":
            self.paused = not self.paused
        elif act == "next":
            self.go_next(); self.elapsed = 0.0
        elif act == "prev":
            self.idx = max(0, self.idx - 1); self.elapsed = 0.0
        elif act == "reshuffle":
            self.restart()
        elif act in ("slower", "faster"):  # slower = longer per photo
            step = 0.5 if act == "slower" else -0.5
            cfg["speed"] = max(lo, min(hi, round(cfg["speed"] + step, 1)))
            self.flash, self.flash_t = f"{cfg['speed']:.1f}s / photo", 2.0
        elif act == "mix":
            cur = cfg["multi_photo_source"]
            cfg["multi_photo_source"] = MULTI_MODES[(MULTI_MODES.index(cur) + 1) % len(MULTI_MODES)]
            self.flash, self.flash_t = f"Multi-photo frames: {MULTI_LABELS[cfg['multi_photo_source']]}", 3.0
            del self.history[self.idx + 1:]  # drop unseen future slides so the change applies now

    def update(self, dt):
        if self.bail:
            self.app.goto("menu")
            return
        if not self.paused:
            self.elapsed += dt
            if self.elapsed >= self.app.cfg["speed"]:
                self.go_next(); self.elapsed = 0.0
        if self.flash_t > 0:
            self.flash_t -= dt

    def draw(self, screen):
        screen.fill((0, 0, 0))
        if self.bail:
            return
        img = self.scaled(self.history[self.idx])
        sw, sh = screen.get_size()
        screen.blit(img, ((sw - img.get_width()) // 2, (sh - img.get_height()) // 2))
        if self.flash_t > 0:
            t = self.small.render(self.flash, True, (255, 255, 255))
            pad = pygame.Surface((t.get_width() + 20, t.get_height() + 10))
            pad.set_alpha(150)
            screen.blit(pad, (sw - pad.get_width() - 10, 10))
            screen.blit(t, (sw - pad.get_width(), 15))
        if self.paused:
            screen.blit(self.big.render("PAUSED", True, (255, 255, 255)), (30, 20))
