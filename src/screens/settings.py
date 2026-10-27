"""Slideshow and caption settings."""
import copy

import pygame
import pygame_gui
from pygame_gui.windows import UIColourPickerDialog

import config_manager as cm
import fonts
import utils
from playback import MULTI_LABELS
from screens.base import Screen

LABEL_W, ROW_H = 260, 56


def to_hex(rgba):
    return "#%02x%02x%02x" % tuple(rgba[:3])


class SettingsScreen(Screen):
    def enter(self, **kwargs):
        self.picker = None
        self.picking = None
        self.build()

    def exit(self):
        self.apply_cutoff()
        self.app.save()

    def on_resize(self):
        self.app.manager.clear_and_reset()
        self.build()

    def build(self):
        cfg, mgr = self.app.cfg, self.app.manager
        w, h = self.app.screen.get_size()
        pygame_gui.elements.UILabel(pygame.Rect(20, 10, w - 40, 40), "Settings", mgr, object_id="#title")
        x, cw = 30 + LABEL_W, min(420, w - LABEL_W - 80)
        rows = ["Seconds per photo", "Multi-photo frames", "Fullscreen slideshow", "Caption cutoff date",
                "Caption font", "Caption text colour", "Caption background"]
        for i, text in enumerate(rows):
            y = 70 + i * ROW_H
            pygame_gui.elements.UILabel(pygame.Rect(20, y, LABEL_W, 36), text, mgr)
        r = lambda i, width=cw: pygame.Rect(x, 70 + i * ROW_H, width, 36)

        self.speed = pygame_gui.elements.UIHorizontalSlider(r(0, cw - 70), cfg["speed"],
                                                            (cfg["min_speed"], cfg["max_speed"]), mgr)
        self.speed_label = pygame_gui.elements.UILabel(pygame.Rect(x + cw - 60, 70, 60, 36), "", mgr)
        self.mix_options = {v: k for k, v in MULTI_LABELS.items()}
        self.mix = pygame_gui.elements.UIDropDownMenu(list(self.mix_options), MULTI_LABELS[cfg["multi_photo_source"]],
                                                      r(1), mgr)
        self.fullscreen = pygame_gui.elements.UIButton(r(2, 120), "", mgr)
        self.cutoff = pygame_gui.elements.UITextEntryLine(r(3, 160), mgr)
        self.cutoff.set_text(cfg["caption_cutoff_date"])
        self.cutoff_note = pygame_gui.elements.UILabel(pygame.Rect(x + 170, 70 + 3 * ROW_H, cw, 36),
                                                       "YYYY-MM-DD; photos taken before this show their year", mgr)
        names = fonts.family_names()
        if cfg["font_family"] not in names:
            names.append(cfg["font_family"])
        self.font = pygame_gui.elements.UIDropDownMenu(names, cfg["font_family"], r(4), mgr)
        self.text_btn = pygame_gui.elements.UIButton(r(5, 160), "", mgr)
        self.bg_btn = pygame_gui.elements.UIButton(r(6, 160), "", mgr)
        bg = utils.parse_color(cfg["text_bg_color"])
        self.bg_alpha = pygame_gui.elements.UIHorizontalSlider(pygame.Rect(x + 216, 70 + 6 * ROW_H, cw - 290, 36),
                                                               round(bg[3] / 255, 2), (0.0, 1.0), mgr)
        self.alpha_label = pygame_gui.elements.UILabel(pygame.Rect(x + cw - 60, 70 + 6 * ROW_H, 60, 36), "", mgr)
        y = h - 65
        self.reset = pygame_gui.elements.UIButton(pygame.Rect(20, y, 200, 45), "Reset to Defaults", mgr)
        self.back = pygame_gui.elements.UIButton(pygame.Rect(w - 220, y, 200, 45), "Back", mgr)
        self.swatches = []
        self.sync()

    def sync(self):
        """Refresh labels that mirror config values."""
        cfg = self.app.cfg
        self.speed_label.set_text(f"{cfg['speed']:.1f}s")
        self.fullscreen.set_text("On" if cfg["fullscreen"] else "Off")
        self.text_btn.set_text(to_hex(utils.parse_color(cfg["text_color"])))
        bg = utils.parse_color(cfg["text_bg_color"])
        self.bg_btn.set_text(to_hex(bg))
        self.alpha_label.set_text(f"{bg[3] / 255:.0%}")

    def apply_cutoff(self):
        text = self.cutoff.get_text().strip()
        if text == self.app.cfg["caption_cutoff_date"]:
            return True
        if cm.parse_cutoff(text):
            self.app.cfg["caption_cutoff_date"] = text
            self.app.library.rescan()
            self.cutoff_note.set_text("Saved - rescanning photos")
            return True
        self.cutoff_note.set_text("Invalid date - use YYYY-MM-DD")
        return False

    def draw(self, surface):
        for rect, colour in ((self.text_btn.rect.move(170, 0), self.app.cfg["text_color"]),
                             (self.bg_btn.rect.move(170, 0), self.app.cfg["text_bg_color"])):
            if rect.right + 40 < surface.get_width():
                pygame.draw.rect(surface, (90, 90, 90), (rect.x, rect.y, 36, 36), 2)
                pygame.draw.rect(surface, utils.parse_color(colour)[:3], (rect.x + 3, rect.y + 3, 30, 30))

    def open_picker(self, which):
        if self.picker:
            return
        self.picking = which
        key = "text_color" if which == "text" else "text_bg_color"
        c = utils.parse_color(self.app.cfg[key])
        w, h = self.app.screen.get_size()
        self.picker = UIColourPickerDialog(pygame.Rect(w // 2 - 200, h // 2 - 250, 400, 500), self.app.manager,
                                           window_title="Choose a colour", initial_colour=pygame.Color(*c[:3]))

    def handle_event(self, e):
        cfg = self.app.cfg
        if e.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if e.ui_element is self.speed:
                cfg["speed"] = cm.clamp_speed(cfg, round(e.value * 2) / 2)
            elif e.ui_element is self.bg_alpha:
                r, g, b = utils.parse_color(cfg["text_bg_color"])[:3]
                cfg["text_bg_color"] = f"rgba({r}, {g}, {b}, {round(e.value, 2)})"
            self.sync()
        elif e.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            if e.ui_element is self.mix:
                cfg["multi_photo_source"] = self.mix_options[e.text]
            elif e.ui_element is self.font:
                cfg["font_family"] = e.text
        elif e.type == pygame_gui.UI_TEXT_ENTRY_FINISHED and e.ui_element is self.cutoff:
            self.apply_cutoff()
        elif e.type == pygame_gui.UI_COLOUR_PICKER_COLOUR_PICKED:
            c = e.colour
            if self.picking == "text":
                cfg["text_color"] = to_hex(c)
            else:
                a = utils.parse_color(cfg["text_bg_color"])[3] / 255
                cfg["text_bg_color"] = f"rgba({c.r}, {c.g}, {c.b}, {round(a, 2)})"
            self.sync()
        elif e.type == pygame_gui.UI_WINDOW_CLOSE and e.ui_element is self.picker:
            self.picker = None
        elif e.type == pygame_gui.UI_BUTTON_PRESSED:
            if e.ui_element is self.back:
                if self.apply_cutoff():
                    self.app.save()
                    self.app.goto("menu")
            elif e.ui_element is self.fullscreen:
                cfg["fullscreen"] = not cfg["fullscreen"]
                self.sync()
            elif e.ui_element is self.text_btn:
                self.open_picker("text")
            elif e.ui_element is self.bg_btn:
                self.open_picker("bg")
            elif e.ui_element is self.reset:
                keep = {k: cfg[k] for k in ("source_folders", "enabled_templates", "last_session")}
                cfg.clear()
                cfg.update(copy.deepcopy(cm.DEFAULTS))
                cfg.update(keep)
                self.app.library.rescan()
                self.on_resize()
