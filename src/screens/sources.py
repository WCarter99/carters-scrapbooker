"""Choose which folders photos come from."""
from pathlib import Path

import pygame
import pygame_gui
from pygame_gui.windows import UIFileDialog

from screens.base import Screen


class SourcesScreen(Screen):
    def enter(self, **kwargs):
        self.dialog = None
        self.selected = None
        self.build()

    def on_resize(self):
        self.app.manager.clear_and_reset()
        self.build()

    def build(self):
        mgr = self.app.manager
        w, h = self.app.screen.get_size()
        pygame_gui.elements.UILabel(pygame.Rect(20, 15, w - 40, 40), "Photo Sources", mgr, object_id="#title")
        self.list = pygame_gui.elements.UISelectionList(pygame.Rect(20, 70, w - 40, h - 150), [], mgr)
        bw, y = (w - 60) // 4, h - 65
        self.buttons = {}
        for i, (key, label) in enumerate((("add", "Add Folder..."), ("toggle", "Enable / Disable"),
                                          ("remove", "Remove"), ("back", "Back"))):
            self.buttons[key] = pygame_gui.elements.UIButton(pygame.Rect(20 + i * (bw + 6), y, bw, 45), label, mgr)
        self.refresh()

    def label(self, source):
        f = self.app.library.scanned.get(source["path"])
        if not Path(source["path"]).is_dir():
            state = "folder not found"
        elif f is None:
            state = "scanning..." if self.app.library.scanning else "unreadable"
        else:
            state = f"{f['photo_count']} photos"
        return f"[{'x' if source['enabled'] else ' '}]  {source['path']}   ({state})"

    def refresh(self):
        self.list.set_item_list([self.label(s) for s in self.app.cfg["source_folders"]])
        self.selected = None
        for k in ("toggle", "remove"):
            self.buttons[k].disable()
        self._sig = self.signature()

    def signature(self):
        lib = self.app.library
        return (lib.scanning, len(lib.scanned), len(self.app.cfg["source_folders"]))

    def update(self, dt):
        if self.signature() != self._sig:
            keep = self.selected
            self.refresh()
            if keep is not None and keep < len(self.app.cfg["source_folders"]):
                self.select_index(keep)

    def select_index(self, i):
        self.selected = i
        for k in ("toggle", "remove"):
            self.buttons[k].enable()

    def handle_event(self, e):
        cfg, lib = self.app.cfg, self.app.library
        if e.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION and e.ui_element is self.list:
            items = [self.label(s) for s in cfg["source_folders"]]
            if e.text in items:
                self.select_index(items.index(e.text))
        elif e.type == pygame_gui.UI_BUTTON_PRESSED:
            b = self.buttons
            if e.ui_element is b["back"]:
                self.app.save()
                self.app.goto("menu")
            elif e.ui_element is b["add"] and not self.dialog:
                w, h = self.app.screen.get_size()
                start = cfg["source_folders"][-1]["path"] if cfg["source_folders"] else str(Path.home())
                self.dialog = UIFileDialog(pygame.Rect(w // 2 - 300, h // 2 - 220, 600, 440), self.app.manager,
                                           "Choose a photo folder", allow_picking_directories=True,
                                           initial_file_path=start)
            elif e.ui_element is b["toggle"] and self.selected is not None:
                s = cfg["source_folders"][self.selected]
                s["enabled"] = not s["enabled"]
                self.keep_and_refresh()
            elif e.ui_element is b["remove"] and self.selected is not None:
                lib.remove(cfg["source_folders"][self.selected]["path"])
                self.refresh()
            self.app.save()
        elif e.type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
            lib.add(e.text)
            self.app.save()
            self.refresh()
        elif e.type == pygame_gui.UI_WINDOW_CLOSE and e.ui_element is self.dialog:
            self.dialog = None

    def keep_and_refresh(self):
        keep = self.selected
        self.refresh()
        self.select_index(keep)
