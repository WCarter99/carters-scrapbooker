"""Main menu."""
import pygame
import pygame_gui
from pygame_gui.windows import UIFileDialog

from playback import MULTI_LABELS
from screens.base import Screen


class MenuScreen(Screen):
    def enter(self, **kwargs):
        self.dialog = None
        self.build()

    def on_resize(self):
        self.app.manager.clear_and_reset()
        self.build()

    def build(self):
        mgr = self.app.manager
        w, h = self.app.screen.get_size()
        cx, bw, bh, gap = w // 2, 360, 52, 14
        y = max(20, h // 2 - 250)
        pygame_gui.elements.UILabel(pygame.Rect(cx - 300, y, 600, 50), "Carter's Scrapbooker", mgr,
                                    object_id="#title")
        y += 70
        self.status = pygame_gui.elements.UILabel(pygame.Rect(cx - 300, y, 600, 30), "", mgr)
        y += 50
        self.buttons = {}
        for key, label in (("random", "Play: Random All"), ("rotating", "Play: Rotating Folders"),
                           ("add", "Add Photo Folder..."), ("quit", "Quit")):
            self.buttons[key] = pygame_gui.elements.UIButton(pygame.Rect(cx - bw // 2, y, bw, bh), label, mgr)
            y += bh + gap
        self.folder_box = pygame_gui.elements.UITextBox("", pygame.Rect(cx - 300, y + 10, 600, max(80, h - y - 30)), mgr)
        self.refresh_text()

    def refresh_text(self):
        lib = self.app.library
        folders = lib.active_folders()
        if lib.scanning:
            done, total = lib.progress
            self.status.set_text(f"Scanning photos... folder {done}/{total}")
        elif not self.app.cfg["source_folders"]:
            self.status.set_text("No photo folders yet - add one to begin")
        else:
            self.status.set_text(f"{lib.total_photos()} photos in {len(folders)} folders, "
                                 f"{len(self.app.enabled_templates())} templates, {self.app.cfg['speed']:.1f}s per photo, "
                                 f"{MULTI_LABELS[self.app.cfg['multi_photo_source']]}")
        lines = [f"{f['name']} ({f['photo_count']} photos)" for f in folders]
        self.folder_box.set_text("<br>".join(lines))
        playable = not lib.scanning and bool(folders)
        for k in ("random", "rotating"):
            (self.buttons[k].enable if playable else self.buttons[k].disable)()
        self._shown = (lib.scanning, lib.progress, len(folders))

    def update(self, dt):
        lib = self.app.library
        if self._shown != (lib.scanning, lib.progress, len(lib.active_folders())):
            self.refresh_text()

    def handle_event(self, e):
        if e.type == pygame_gui.UI_BUTTON_PRESSED:
            if e.ui_element is self.buttons["random"]:
                self.app.goto("playback", mode="random")
            elif e.ui_element is self.buttons["rotating"]:
                self.app.goto("playback", mode="rotating")
            elif e.ui_element is self.buttons["add"] and not self.dialog:
                w, h = self.app.screen.get_size()
                self.dialog = UIFileDialog(pygame.Rect(w // 2 - 300, h // 2 - 220, 600, 440), self.app.manager,
                                           "Choose a photo folder", allow_picking_directories=True)
            elif e.ui_element is self.buttons["quit"]:
                self.app.quit()
        elif e.type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
            self.app.library.add(e.text)
            self.app.save()
        elif e.type == pygame_gui.UI_WINDOW_CLOSE and e.ui_element is self.dialog:
            self.dialog = None
