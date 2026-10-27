"""Choose which templates the slideshow may use."""
import pygame
import pygame_gui

from screens.base import Screen


class TemplatesScreen(Screen):
    def enter(self, **kwargs):
        self.selected = None
        self.build()

    def on_resize(self):
        self.app.manager.clear_and_reset()
        self.build()

    def enabled_ids(self):
        names = self.app.cfg.get("enabled_templates")
        return {t["id"] for t in self.app.templates} if names is None else \
            {t["id"] for t in self.app.templates if t["id"] in names or t["_file"] in names}

    def build(self):
        mgr = self.app.manager
        w, h = self.app.screen.get_size()
        pygame_gui.elements.UILabel(pygame.Rect(20, 15, w - 40, 40), "Templates", mgr, object_id="#title")
        self.list = pygame_gui.elements.UISelectionList(pygame.Rect(20, 70, w - 40, h - 150), [], mgr)
        bw, y = (w - 60) // 4, h - 65
        self.buttons = {}
        for i, (key, label) in enumerate((("toggle", "Enable / Disable"), ("all", "Enable All"),
                                          ("none", "Disable All"), ("back", "Back"))):
            self.buttons[key] = pygame_gui.elements.UIButton(pygame.Rect(20 + i * (bw + 6), y, bw, 45), label, mgr)
        self.buttons["toggle"].disable()
        self.refresh()

    def labels(self):
        on = self.enabled_ids()
        return [f"[{'x' if t['id'] in on else ' '}]  {t['name']}   ({len(t['photo_zones'])} photo"
                f"{'s' if len(t['photo_zones']) != 1 else ''}"
                f"{', user template' if t.get('_source') == 'user' else ''})" for t in self.app.templates]

    def refresh(self):
        self.list.set_item_list(self.labels())
        self.selected = None
        self.buttons["toggle"].disable()

    def set_enabled(self, ids):
        self.app.cfg["enabled_templates"] = sorted(ids)
        self.app.save()

    def handle_event(self, e):
        if e.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION and e.ui_element is self.list:
            labels = self.labels()
            if e.text in labels:
                self.selected = labels.index(e.text)
                self.buttons["toggle"].enable()
        elif e.type == pygame_gui.UI_BUTTON_PRESSED:
            b = self.buttons
            ids = self.enabled_ids()
            if e.ui_element is b["back"]:
                self.app.goto("menu")
            elif e.ui_element is b["toggle"] and self.selected is not None:
                ids ^= {self.app.templates[self.selected]["id"]}
                if not ids:  # never leave the slideshow with nothing to draw
                    ids = {self.app.templates[self.selected]["id"]}
                self.set_enabled(ids)
                self.refresh()
            elif e.ui_element is b["all"]:
                self.set_enabled({t["id"] for t in self.app.templates})
                self.refresh()
            elif e.ui_element is b["none"]:
                self.set_enabled({self.app.templates[0]["id"]})  # at least one must stay on
                self.refresh()
