"""Template editing model: creating zones, undo history, saving to the user's template folder."""
import copy
import json
import re

import paths
from template_manager import validate_template

INTERNAL_KEYS = ("_file", "_source")


def safe_id(raw) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", str(raw).replace(" ", "_"))


def blank_template() -> dict:
    return {"id": "", "name": "", "description": "", "background_color": "#f5f5dc", "background_image": None,
            "canvas_width": 1920, "canvas_height": 1080,
            "photo_zones": [{"id": "photo_1", "x": 50, "y": 50, "width": 850, "height": 980,
                             "object_fit": "crop_center", "aspect_ratio_range": [0.7, 1.3]}],
            "text_zones": [{"id": "text_1", "x": 950, "y": 200, "width": 900, "height": 650,
                            "background_color": "rgba(255, 255, 255, 0.9)", "text_color": "#333333",
                            "padding": 20, "alignment": "center", "vertical_align": "center"}]}


def unique_zone_id(t, prefix) -> str:
    taken = {z["id"] for z in t["photo_zones"] + t.get("text_zones", [])}
    n = 1
    while f"{prefix}_{n}" in taken:
        n += 1
    return f"{prefix}_{n}"


def new_photo_zone(t) -> dict:
    return {"id": unique_zone_id(t, "photo"), "x": 100, "y": 100, "width": 500, "height": 600,
            "object_fit": "crop_center", "aspect_ratio_range": [0.6, 1.5]}


def new_text_zone(t) -> dict:
    return {"id": unique_zone_id(t, "text"), "x": 100, "y": 800, "width": 800, "height": 200,
            "background_color": "rgba(0, 0, 0, 0.5)", "text_color": "#ffffff", "padding": 20,
            "alignment": "center", "vertical_align": "center"}


def duplicate_zone(t, zone) -> dict:
    """Copy of a zone, offset a little, with a fresh id (caller appends it to the right list)."""
    z = copy.deepcopy(zone)
    z["id"] = unique_zone_id(t, "photo" if "aspect_ratio_range" in zone else "text")
    z["x"] += 40
    z["y"] += 40
    return z


def is_photo_zone(t, zone) -> bool:
    return any(zone is z for z in t["photo_zones"])


class History:
    """Snapshot-based undo/redo of a template dict."""

    def __init__(self, limit=100):
        self.undo, self.redo, self.limit = [], [], limit

    def push(self, t):
        self.undo.append(json.dumps(t))
        del self.undo[:-self.limit]
        self.redo.clear()

    def step_back(self, current):
        if not self.undo:
            return None
        self.redo.append(json.dumps(current))
        return json.loads(self.undo.pop())

    def step_forward(self, current):
        if not self.redo:
            return None
        self.undo.append(json.dumps(current))
        return json.loads(self.redo.pop())


def user_template_path(tid):
    tid = safe_id(tid)
    return paths.user_templates_dir() / f"template_{tid}.json" if tid else None


def clean_for_save(t) -> dict:
    out = copy.deepcopy(t)
    for k in INTERNAL_KEYS:
        out.pop(k, None)
    out["id"] = safe_id(out.get("id", ""))
    if not out.get("name"):
        out["name"] = out["id"]
    return out


def save_user_template(t):
    """Validate and write the template; returns (path, None) or (None, error message)."""
    out = clean_for_save(t)
    if not out["id"]:
        return None, "Enter a template ID"
    if not validate_template(out):
        return None, "Template failed validation (check zone sizes and aspect ranges)"
    path = user_template_path(out["id"])
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return path, None


def delete_user_template(tid) -> bool:
    p = user_template_path(tid)
    if p and p.exists():
        p.unlink()
        return True
    return False
