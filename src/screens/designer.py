"""Template designer: drag/resize zones on a canvas, edit their properties, save to the user's templates."""
import copy
import random

import pygame
import pygame_gui
from pygame_gui.windows import UIColourPickerDialog, UIConfirmationDialog, UIFileDialog

import fonts
import paths
import template_manager as tm
import utils
from designer import geometry as geo
from designer import model
from screens.base import Screen

LEFT_W, RIGHT_W, ROW, GAP = 300, 290, 30, 5
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
NUMBERS, DECIMALS = list("0123456789"), list("0123456789.")
PHOTO_FILL, TEXT_EDGE, PHOTO_EDGE = (70, 170, 255), (255, 170, 70), (70, 170, 255)


def to_hex(rgba):
    return "#%02x%02x%02x" % tuple(rgba[:3])


class DesignerScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.sample = None       # pygame.Surface of the preview photo
        self.sample_cache = {}
        self.bg_cache = None
        self.caption = "2015"

    # ---- lifecycle ---------------------------------------------------------
    def enter(self, **kwargs):
        self.modal = None
        self.pending = None       # callable to run if the user confirms discarding changes
        self.pick_setter = None
        self.drag = None
        self.status = ""
        self.new_template()
        if self.sample is None:
            self.load_library_sample()
        self.build()

    def exit(self):
        self.modal = None

    def on_resize(self):
        self.app.manager.clear_and_reset()
        self.build()

    # ---- template state ----------------------------------------------------
    def new_template(self):
        self.load(model.blank_template(), dirty=False)

    def load(self, t, dirty=False):
        self.T = t
        self.sel = None
        self.history = model.History()
        self.dirty = dirty
        self.last_group = None
        self.bg_cache = None

    def checkpoint(self, group=None):
        """Remember the state before an edit. Repeated edits in one `group` (e.g. typing in one field) coalesce."""
        if group is not None and group == self.last_group:
            return
        self.history.push(self.T)
        self.last_group = group
        self.dirty = True

    def restore(self, t):
        if t is None:
            return
        sel_id = self.sel["id"] if self.sel else None
        self.T = t
        self.sel = next((z for z in self.zones() if z["id"] == sel_id), None)
        self.last_group, self.dirty, self.bg_cache = None, True, None
        self.sync_all()

    def zones(self):
        return self.T["photo_zones"] + self.T["text_zones"]

    def is_photo(self, z):
        return model.is_photo_zone(self.T, z)

    # ---- layout ------------------------------------------------------------
    def build(self):
        mgr = self.app.manager
        w, h = self.app.screen.get_size()
        self.syncing = False
        self.bindings = {}
        self.prop_elems = []
        lx = 10
        self.left_rect = pygame.Rect(0, 0, LEFT_W, h)
        self.right_rect = pygame.Rect(w - RIGHT_W, 0, RIGHT_W, h)
        self.canvas_area = pygame.Rect(LEFT_W + 15, 15, w - LEFT_W - RIGHT_W - 30, h - 30)

        y = [8]

        def row(height=ROW):
            r = pygame.Rect(lx, y[0], LEFT_W - 2 * lx, height)
            y[0] += height + GAP
            return r

        def split(r, n=2):
            gap = 6
            cw = (r.width - gap * (n - 1)) // n
            return [pygame.Rect(r.x + i * (cw + gap), r.y, cw, r.height) for i in range(n)]

        def label_entry(text, rect, label_w=88):
            pygame_gui.elements.UILabel(pygame.Rect(rect.x, rect.y, label_w, rect.height), text, mgr)
            return pygame_gui.elements.UITextEntryLine(pygame.Rect(rect.x + label_w, rect.y, rect.width - label_w,
                                                                   rect.height), mgr)

        pygame_gui.elements.UILabel(row(36), "Template Designer", mgr, object_id="#subtitle")
        self.existing = None
        self.build_existing_dropdown(row())
        a, b = split(row())
        self.btn_new = pygame_gui.elements.UIButton(a, "New", mgr)
        self.btn_delete = pygame_gui.elements.UIButton(b, "Delete", mgr)
        self.e_id = label_entry("ID", row())
        self.e_name = label_entry("Name", row())
        self.e_desc = label_entry("Description", row())
        a, b = split(row())
        self.e_cw = label_entry("Width", a, 52)
        self.e_ch = label_entry("Height", b, 56)
        for e in (self.e_cw, self.e_ch):
            e.set_allowed_characters(NUMBERS)
        r = row()
        pygame_gui.elements.UILabel(pygame.Rect(r.x, r.y, 120, r.height), "Background", mgr)
        self.btn_bg = pygame_gui.elements.UIButton(pygame.Rect(r.x + 120, r.y, r.width - 120, r.height), "", mgr)
        y[0] += 6
        a, b = split(row())
        self.btn_add_photo = pygame_gui.elements.UIButton(a, "+ Photo zone", mgr)
        self.btn_add_text = pygame_gui.elements.UIButton(b, "+ Text zone", mgr)
        a, b = split(row())
        self.btn_remove = pygame_gui.elements.UIButton(a, "Remove zone", mgr)
        self.btn_dup = pygame_gui.elements.UIButton(b, "Duplicate", mgr)
        a, b = split(row())
        self.btn_undo = pygame_gui.elements.UIButton(a, "Undo", mgr)
        self.btn_redo = pygame_gui.elements.UIButton(b, "Redo", mgr)
        y[0] += 6
        self.btn_sample = pygame_gui.elements.UIButton(row(), "Choose sample photo...", mgr)
        self.e_caption = label_entry("Caption", row(), 70)
        self.e_caption.set_text(self.caption)
        y[0] += 6
        a, b = split(row(36))
        self.btn_save = pygame_gui.elements.UIButton(a, "Save", mgr)
        self.btn_back = pygame_gui.elements.UIButton(b, "Back", mgr)
        self.status_label = pygame_gui.elements.UILabel(pygame.Rect(lx, y[0], LEFT_W - 2 * lx, ROW), "", mgr)

        self.build_props()
        self.sync_all()

    def build_existing_dropdown(self, rect):
        names = [t["name"] + ("  (yours)" if t.get("_source") == "user" else "") for t in self.app.templates]
        self.existing_names = dict(zip(names, self.app.templates))
        self.existing = pygame_gui.elements.UIDropDownMenu(["Load a template..."] + names, "Load a template...",
                                                           rect, self.app.manager)

    def build_props(self):
        """(Re)create the right-hand zone property controls for the current selection."""
        for e in self.prop_elems:
            e.kill()
        self.prop_elems.clear()
        for k in [k for k in self.bindings if getattr(k, "_prop", False)]:
            del self.bindings[k]
        mgr, z = self.app.manager, self.sel
        self.num_boxes = {}
        x0, y = self.right_rect.x + 10, 8
        inner = RIGHT_W - 20

        def add(el):
            self.prop_elems.append(el)
            return el

        def title(text):
            nonlocal y
            add(pygame_gui.elements.UILabel(pygame.Rect(x0, y, inner, 36), text, mgr, object_id="#subtitle"))
            y += 36 + GAP

        if z is None:
            title("Zone")
            add(pygame_gui.elements.UILabel(pygame.Rect(x0, y, inner, ROW), "Click a zone to edit it", mgr))
            return
        photo = self.is_photo(z)
        title(f"{'Photo' if photo else 'Text'} zone: {z['id']}")

        def num(label, key, x, width, chars=NUMBERS, cast=int, lw=38, sub=None):
            add(pygame_gui.elements.UILabel(pygame.Rect(x, y, lw, ROW), label, mgr))
            e = add(pygame_gui.elements.UITextEntryLine(pygame.Rect(x + lw, y, width - lw, ROW), mgr))
            e.set_allowed_characters(chars)
            e._prop = True
            e.set_text(str(self.get_value(z, key, sub)))
            self.bindings[e] = (key, cast, sub)
            return e

        half = inner // 2
        self.num_boxes["x"] = num("X", "x", x0, half - 3)
        self.num_boxes["y"] = num("Y", "y", x0 + half + 3, half - 3)
        y += ROW + GAP
        self.num_boxes["width"] = num("W", "width", x0, half - 3)
        self.num_boxes["height"] = num("H", "height", x0 + half + 3, half - 3)
        y += ROW + GAP
        if photo:
            num("Min", "aspect_ratio_range", x0, half - 3, DECIMALS, float, sub=0)
            num("Max", "aspect_ratio_range", x0 + half + 3, half - 3, DECIMALS, float, sub=1)
            y += ROW + GAP
            add(pygame_gui.elements.UITextBox("Aspect = width / height. Photos are matched to zones whose range "
                                              "contains their aspect when possible.",
                                              pygame.Rect(x0, y, inner, ROW * 3), mgr))
            return
        num("Pad", "padding", x0, half - 3)
        num("Size", "font_size", x0 + half + 3, half - 3, lw=44)
        y += ROW + GAP
        fam = ["(default)"] + fonts.family_names()
        cur = z.get("font_family", "(default)")
        if cur not in fam:
            fam.append(cur)
        self.dd_font = add(pygame_gui.elements.UIDropDownMenu(fam, cur, pygame.Rect(x0, y, inner, ROW), mgr))
        y += ROW + GAP
        self.dd_align = add(pygame_gui.elements.UIDropDownMenu(["left", "center", "right"], z.get("alignment", "center"),
                                                               pygame.Rect(x0, y, half - 3, ROW), mgr))
        self.dd_valign = add(pygame_gui.elements.UIDropDownMenu(["top", "center", "bottom"],
                                                                z.get("vertical_align", "center"),
                                                                pygame.Rect(x0 + half + 3, y, half - 3, ROW), mgr))
        y += ROW + GAP
        add(pygame_gui.elements.UILabel(pygame.Rect(x0, y, 110, ROW), "Text colour", mgr))
        self.btn_text_col = add(pygame_gui.elements.UIButton(pygame.Rect(x0 + 110, y, inner - 110, ROW), "", mgr))
        y += ROW + GAP
        add(pygame_gui.elements.UILabel(pygame.Rect(x0, y, 110, ROW), "Box colour", mgr))
        self.btn_box_col = add(pygame_gui.elements.UIButton(pygame.Rect(x0 + 110, y, inner - 110, ROW), "", mgr))
        y += ROW + GAP
        add(pygame_gui.elements.UILabel(pygame.Rect(x0, y, 110, ROW), "Box opacity", mgr))
        self.e_alpha = add(pygame_gui.elements.UITextEntryLine(pygame.Rect(x0 + 110, y, 70, ROW), mgr))
        self.e_alpha.set_allowed_characters(DECIMALS)
        self.sync_colours()

    # ---- value sync --------------------------------------------------------
    @staticmethod
    def get_value(z, key, sub=None):
        v = z.get(key, "")
        if sub is not None:
            v = v[sub]
        return int(v) if isinstance(v, float) and v.is_integer() and key != "aspect_ratio_range" else v

    def sync_all(self):
        self.syncing = True
        T = self.T
        self.e_id.set_text(T.get("id", ""))
        self.e_name.set_text(T.get("name", ""))
        self.e_desc.set_text(T.get("description", ""))
        self.e_cw.set_text(str(T["canvas_width"]))
        self.e_ch.set_text(str(T["canvas_height"]))
        self.btn_bg.set_text(to_hex(utils.parse_color(T.get("background_color"))))
        self.syncing = False
        self.build_props()
        self.sync_buttons()

    def sync_geometry_boxes(self):
        """Refresh X/Y/W/H boxes while dragging (skipped for a box being typed in)."""
        if not self.sel or not hasattr(self, "num_boxes"):
            return
        self.syncing = True
        for key, box in self.num_boxes.items():
            if not box.is_focused:
                box.set_text(str(int(self.sel[key])))
        self.syncing = False

    def sync_colours(self):
        z = self.sel
        if not z or self.is_photo(z):
            return
        self.syncing = True
        self.btn_text_col.set_text(to_hex(utils.parse_color(z.get("text_color"), (255, 255, 255, 255))))
        bg = utils.parse_color(z.get("background_color"), (0, 0, 0, 0))
        self.btn_box_col.set_text(to_hex(bg))
        if not self.e_alpha.is_focused:
            self.e_alpha.set_text(f"{bg[3] / 255:.2f}")
        self.syncing = False

    def sync_buttons(self):
        can = self.sel is not None
        for b in (self.btn_remove, self.btn_dup):
            (b.enable if can else b.disable)()
        (self.btn_undo.enable if self.history.undo else self.btn_undo.disable)()
        (self.btn_redo.enable if self.history.redo else self.btn_redo.disable)()
        user_file = model.user_template_path(self.T.get("id", ""))
        (self.btn_delete.enable if user_file and user_file.exists() else self.btn_delete.disable)()

    def say(self, text):
        self.status = text
        self.status_label.set_text(text if len(text) <= 36 else text[:35] + "…")

    def select(self, z):
        if z is not self.sel:
            self.sel = z
            self.last_group = None
            self.build_props()
            self.sync_buttons()

    # ---- actions -----------------------------------------------------------
    def guard(self, action):
        """Run action now, or after the user agrees to discard unsaved changes."""
        if not self.dirty:
            action()
            return
        self.pending = action
        self.open_modal(UIConfirmationDialog(self.centered(420, 200),
                                             "You have unsaved changes. Discard them?", self.app.manager,
                                             window_title="Unsaved changes", action_short_name="Discard"))

    def centered(self, w, h):
        sw, sh = self.app.screen.get_size()
        return pygame.Rect(sw // 2 - w // 2, sh // 2 - h // 2, w, h)

    def open_modal(self, dialog):
        self.modal = dialog

    def do_save(self):
        self.apply_text_fields()
        path, err = model.save_user_template(self.T)
        if err:
            self.say(err)
            return
        self.T["id"] = model.safe_id(self.T["id"])
        self.dirty = False
        self.app.templates = tm.load_all_templates()
        self.say(f"Saved {path.name}")
        self.on_resize()

    def apply_text_fields(self):
        """Make sure id/name/description reflect the boxes even if no change event was seen."""
        self.T["id"], self.T["name"] = self.e_id.get_text(), self.e_name.get_text()
        self.T["description"] = self.e_desc.get_text()

    def do_delete(self):
        tid = self.T.get("id", "")
        if model.delete_user_template(tid):
            self.app.templates = tm.load_all_templates()
            self.say(f"Deleted your '{tid}' template")
            self.new_template()
            self.on_resize()

    def add_zone(self, photo):
        self.checkpoint()
        z = model.new_photo_zone(self.T) if photo else model.new_text_zone(self.T)
        (self.T["photo_zones"] if photo else self.T["text_zones"]).append(z)
        self.select(z)

    def remove_zone(self):
        z = self.sel
        if z is None:
            return
        if self.is_photo(z) and len(self.T["photo_zones"]) == 1:
            self.say("Need at least one photo zone")
            return
        self.checkpoint()
        self.T["photo_zones"] = [q for q in self.T["photo_zones"] if q is not z]
        self.T["text_zones"] = [q for q in self.T["text_zones"] if q is not z]
        self.sel = None
        self.build_props()
        self.sync_buttons()

    def duplicate_zone(self):
        if self.sel is None:
            return
        self.checkpoint()
        d = model.duplicate_zone(self.T, self.sel)
        (self.T["photo_zones"] if self.is_photo(self.sel) else self.T["text_zones"]).append(d)
        self.select(d)

    def load_library_sample(self):
        """Start with a photo from the user's library, if any, so zones preview with a real picture."""
        photos = [p for f in self.app.library.active_folders() for p in f["photos"]]
        if photos:
            self.load_sample(random.choice(photos)["path"])

    def load_sample(self, path):
        try:
            img = utils.load_pil(path)
            img.thumbnail((900, 900))
            self.sample = utils.pil_to_surface(img)
            self.sample_cache.clear()
        except Exception as e:  # unreadable image: keep whatever we had
            self.say(f"Could not open photo: {e}"[:60])

    def open_picker(self, setter, initial):
        if self.modal:
            return
        self.pick_setter = setter
        c = utils.parse_color(initial)
        self.open_modal(UIColourPickerDialog(self.centered(400, 500), self.app.manager,
                                             window_title="Choose a colour", initial_colour=pygame.Color(*c[:3])))

    # ---- events ------------------------------------------------------------
    def handle_event(self, e):
        if e.type == pygame_gui.UI_WINDOW_CLOSE and e.ui_element is self.modal:
            self.modal = None
        elif e.type == pygame_gui.UI_BUTTON_PRESSED:
            self.on_button(e.ui_element)
        elif e.type == pygame_gui.UI_TEXT_ENTRY_CHANGED and not self.syncing:
            self.on_text(e.ui_element, e.text)
        elif e.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            self.on_dropdown(e.ui_element, e.text)
        elif e.type == pygame_gui.UI_COLOUR_PICKER_COLOUR_PICKED and self.pick_setter:
            self.pick_setter(e.colour)
            self.pick_setter = None
        elif e.type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
            self.load_sample(e.text)
        elif e.type == pygame_gui.UI_CONFIRMATION_DIALOG_CONFIRMED and self.pending:
            action, self.pending = self.pending, None
            action()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse_down(e.pos)
        elif e.type == pygame.MOUSEMOTION and self.drag:
            self.mouse_move(e.pos)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.drag = None
        elif e.type == pygame.KEYDOWN:
            self.on_key(e)

    def on_button(self, b):
        T = self.T
        if b is self.btn_new:
            self.guard(lambda: (self.new_template(), self.on_resize()))
        elif b is self.btn_delete:
            self.pending = self.do_delete
            self.open_modal(UIConfirmationDialog(self.centered(420, 200),
                                                 f"Delete your template '{T.get('id')}'? This cannot be undone.",
                                                 self.app.manager,
                                                 window_title="Delete template", action_short_name="Delete"))
        elif b is self.btn_save:
            self.do_save()
        elif b is self.btn_back:
            self.guard(lambda: self.app.goto("menu"))
        elif b is self.btn_add_photo:
            self.add_zone(True)
        elif b is self.btn_add_text:
            self.add_zone(False)
        elif b is self.btn_remove:
            self.remove_zone()
        elif b is self.btn_dup:
            self.duplicate_zone()
        elif b is self.btn_undo:
            self.restore(self.history.step_back(T))
        elif b is self.btn_redo:
            self.restore(self.history.step_forward(T))
        elif b is self.btn_sample and not self.modal:
            self.open_modal(UIFileDialog(self.centered(600, 440), self.app.manager, "Choose a sample photo",
                                         allowed_suffixes=PHOTO_EXTS, allow_existing_files_only=True))
        elif b is self.btn_bg:
            self.open_picker(self.set_background, T.get("background_color"))
        elif getattr(self, "btn_text_col", None) is b and self.sel:
            self.open_picker(lambda c: self.set_zone_value("text_color", to_hex(c)), self.sel.get("text_color"))
        elif getattr(self, "btn_box_col", None) is b and self.sel:
            self.open_picker(self.set_box_colour, self.sel.get("background_color"))

    def set_background(self, c):
        self.checkpoint()
        self.T["background_color"] = to_hex(c)
        self.btn_bg.set_text(to_hex(c))

    def set_box_colour(self, c):
        a = utils.parse_color(self.sel.get("background_color"), (0, 0, 0, 128))[3] / 255
        self.set_zone_value("background_color", f"rgba({c.r}, {c.g}, {c.b}, {round(a, 2)})")

    def set_zone_value(self, key, value):
        self.checkpoint()
        self.sel[key] = value
        self.sync_colours()

    def on_text(self, el, text):
        T = self.T
        simple = {self.e_id: "id", self.e_name: "name", self.e_desc: "description"}
        if el in simple:
            self.checkpoint(el)
            T[simple[el]] = text
        elif el in (self.e_cw, self.e_ch):
            if text.isdigit() and int(text) > 0:
                self.checkpoint(el)
                T["canvas_width" if el is self.e_cw else "canvas_height"] = int(text)
        elif el is self.e_caption:
            self.caption = text
        elif el in self.bindings and self.sel:
            key, cast, sub = self.bindings[el]
            try:
                v = cast(text)
            except ValueError:
                if text == "" and key == "font_size":  # blank = use the global default size
                    self.checkpoint(el)
                    self.sel.pop("font_size", None)
                return
            self.checkpoint(el)
            if sub is not None:
                self.sel[key][sub] = v
            else:
                self.sel[key] = max(1, v) if key in ("width", "height") else v
        elif getattr(self, "e_alpha", None) is el and self.sel:
            try:
                a = max(0.0, min(1.0, float(text)))
            except ValueError:
                return
            r, g, b = utils.parse_color(self.sel.get("background_color"), (0, 0, 0, 0))[:3]
            self.checkpoint(el)
            self.sel["background_color"] = f"rgba({r}, {g}, {b}, {a})"
        self.sync_buttons()

    def on_dropdown(self, el, text):
        if el is self.existing:
            t = self.existing_names.get(text)
            if t:
                self.guard(lambda: self.load_chosen(t))
            return
        if not self.sel:
            return
        if el is getattr(self, "dd_font", None):
            self.checkpoint()
            if text == "(default)":
                self.sel.pop("font_family", None)
            else:
                self.sel["font_family"] = text
        elif el is getattr(self, "dd_align", None):
            self.set_zone_value("alignment", text)
        elif el is getattr(self, "dd_valign", None):
            self.set_zone_value("vertical_align", text)

    def load_chosen(self, t):
        self.load(copy.deepcopy(t))
        self.on_resize()
        self.say(f"Loaded {t['name']}" + (" (save = your copy)" if t.get("_source") == "bundled" else ""))

    def typing(self):
        return any(getattr(e, "is_focused", False) for e in
                   (self.e_id, self.e_name, self.e_desc, self.e_cw, self.e_ch, self.e_caption,
                    *[x for x in self.prop_elems if isinstance(x, pygame_gui.elements.UITextEntryLine)]))

    def on_key(self, e):
        ctrl = e.mod & pygame.KMOD_CTRL
        if ctrl and e.key == pygame.K_z:
            self.restore(self.history.step_back(self.T))
        elif ctrl and e.key == pygame.K_y:
            self.restore(self.history.step_forward(self.T))
        elif ctrl and e.key == pygame.K_s:
            self.do_save()
        elif self.typing() or self.modal:
            return
        elif e.key == pygame.K_DELETE:
            self.remove_zone()
        elif self.sel and e.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
            step = 10 if e.mod & pygame.KMOD_SHIFT else 1
            dx = {pygame.K_LEFT: -step, pygame.K_RIGHT: step}.get(e.key, 0)
            dy = {pygame.K_UP: -step, pygame.K_DOWN: step}.get(e.key, 0)
            self.checkpoint(("nudge", id(self.sel)))
            self.sel["x"] += dx
            self.sel["y"] += dy
            self.sync_geometry_boxes()

    # ---- canvas interaction ------------------------------------------------
    def view(self):
        """(scale, origin) placing the canvas centred inside the canvas area."""
        T, a = self.T, self.canvas_area
        s = geo.fit_scale(T["canvas_width"], T["canvas_height"], a.width, a.height)
        ox = a.x + (a.width - T["canvas_width"] * s) / 2
        oy = a.y + (a.height - T["canvas_height"] * s) / 2
        return s, (ox, oy)

    def mouse_down(self, pos):
        if self.modal or not self.canvas_area.collidepoint(pos):
            return
        scale, origin = self.view()
        if self.sel:
            handle = geo.handle_at(geo.canvas_to_screen(self.sel, scale, origin), pos)
            if handle:
                self.start_drag(handle, pos)
                return
        z = geo.zone_at(self.zones(), pos, scale, origin)
        self.select(z)
        if z:
            self.start_drag("move", pos)

    def start_drag(self, mode, pos):
        self.drag = {"mode": mode, "start": pos, "orig": dict(self.sel), "zone": self.sel, "pushed": False}

    def mouse_move(self, pos):
        d, scale = self.drag, self.view()[0]
        dx, dy = round((pos[0] - d["start"][0]) / scale), round((pos[1] - d["start"][1]) / scale)
        if not d["pushed"] and (dx or dy):
            backup = dict(d["zone"])
            d["zone"].update(d["orig"])  # snapshot the pre-drag state, not the half-dragged one
            self.checkpoint()
            d["zone"].update(backup)
            d["pushed"] = True
        x, y, w, h = geo.apply_drag(d["orig"], d["mode"], dx, dy)
        d["zone"].update(x=x, y=y, width=w, height=h)
        self.sync_geometry_boxes()

    # ---- drawing -----------------------------------------------------------
    def update(self, dt):
        if self.drag is None:
            self.sync_buttons()

    def background_surface(self, w, h):
        bg = self.T.get("background_image")
        if not bg:
            return None
        key = (bg, w, h)
        if not self.bg_cache or self.bg_cache[0] != key:
            try:
                self.bg_cache = (key, utils.crop_image_to_fit(paths.resource_path(bg), w, h))
            except Exception:
                self.bg_cache = (key, None)
        return self.bg_cache[1]

    def photo_surface(self, w, h):
        if self.sample is None or w < 2 or h < 2:
            return None
        key = (w, h)
        if key not in self.sample_cache:
            if len(self.sample_cache) > 32:
                self.sample_cache.clear()
            self.sample_cache[key] = utils.resize_and_crop_center(self.sample, w, h)
        return self.sample_cache[key]

    def draw(self, surf):
        scale, (ox, oy) = self.view()
        T = self.T
        stage = pygame.Rect(round(ox), round(oy), round(T["canvas_width"] * scale), round(T["canvas_height"] * scale))
        pygame.draw.rect(surf, utils.parse_color(T.get("background_color"))[:3], stage)
        prev_clip = surf.get_clip()
        surf.set_clip(stage)
        bg = self.background_surface(stage.width, stage.height)
        if bg:
            surf.blit(bg, stage)
        label_font = fonts.get_font("Noto Sans", 12)
        for z in self.zones():
            r = pygame.Rect(*[round(v) for v in geo.canvas_to_screen(z, scale, (ox, oy))])
            if self.is_photo(z):
                img = self.photo_surface(r.width, r.height)
                if img:
                    surf.blit(img, r)
                else:
                    tint = pygame.Surface(r.size, pygame.SRCALPHA)
                    tint.fill((*PHOTO_FILL, 60))
                    surf.blit(tint, r)
            else:
                size = max(6, int(z.get("font_size", self.app.cfg["font_size"]) * scale))
                font = fonts.get_font(z.get("font_family", self.app.cfg["font_family"]), size)
                surf.blit(utils.render_text_on_surface(
                    self.caption, font, z.get("text_color", self.app.cfg["text_color"]),
                    z.get("background_color", self.app.cfg["text_bg_color"]), r.width, r.height,
                    max(0, z.get("padding", 20) * scale), z.get("alignment", "center"),
                    z.get("vertical_align", "center")), r)
            edge = PHOTO_EDGE if self.is_photo(z) else TEXT_EDGE
            pygame.draw.rect(surf, edge, r, 1 if z is not self.sel else 3)
            tag = label_font.render(z["id"], True, (255, 255, 255))
            shade = pygame.Surface((tag.get_width() + 6, tag.get_height() + 2), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 170))
            surf.blit(shade, r.topleft)
            surf.blit(tag, (r.x + 3, r.y + 1))
        surf.set_clip(prev_clip)
        pygame.draw.rect(surf, (90, 90, 100), stage.inflate(2, 2), 1)
        if self.sel:
            r = geo.canvas_to_screen(self.sel, scale, (ox, oy))
            for hx, hy in geo.handle_positions(r).values():
                pygame.draw.rect(surf, (255, 255, 255), (hx - 5, hy - 5, 10, 10))
                pygame.draw.rect(surf, (0, 0, 0), (hx - 5, hy - 5, 10, 10), 1)
        for panel in (self.left_rect, self.right_rect):
            pygame.draw.rect(surf, (30, 30, 36), panel)
        if self.dirty:
            tag = fonts.get_font("Noto Sans", 14).render("unsaved changes", True, (255, 200, 120))
            surf.blit(tag, (self.canvas_area.x, self.canvas_area.bottom - 18))
