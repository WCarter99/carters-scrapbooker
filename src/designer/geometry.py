"""Pure geometry for the template designer canvas (no pygame needed, so it is unit-testable)."""

HANDLES = ("nw", "n", "ne", "e", "se", "s", "sw", "w")
MIN_SIZE = 40


def fit_scale(canvas_w, canvas_h, area_w, area_h):
    """Scale that fits the canvas inside the area."""
    return min(area_w / canvas_w, area_h / canvas_h) if canvas_w > 0 and canvas_h > 0 else 1.0


def canvas_to_screen(zone, scale, origin):
    """Zone rect (x, y, w, h) in screen pixels."""
    return (origin[0] + zone["x"] * scale, origin[1] + zone["y"] * scale,
            zone["width"] * scale, zone["height"] * scale)


def screen_to_canvas(pos, scale, origin):
    return ((pos[0] - origin[0]) / scale, (pos[1] - origin[1]) / scale)


def handle_positions(rect):
    """Centre point of each resize handle for a screen rect (x, y, w, h)."""
    x, y, w, h = rect
    xs = {"w": x, "": x + w / 2, "e": x + w}
    ys = {"n": y, "": y + h / 2, "s": y + h}
    return {name: (xs[name.replace("n", "").replace("s", "")], ys[name.replace("e", "").replace("w", "")])
            for name in HANDLES}


def handle_at(rect, pos, radius=8):
    """Which resize handle of the rect is under pos, or None."""
    for name, (hx, hy) in handle_positions(rect).items():
        if abs(pos[0] - hx) <= radius and abs(pos[1] - hy) <= radius:
            return name
    return None


def zone_at(zones, pos, scale, origin):
    """Topmost zone under pos. `zones` is in drawing order (last = on top)."""
    for z in reversed(zones):
        x, y, w, h = canvas_to_screen(z, scale, origin)
        if x <= pos[0] <= x + w and y <= pos[1] <= y + h:
            return z
    return None


def apply_drag(orig, mode, dx, dy, min_size=MIN_SIZE):
    """New (x, y, width, height) after dragging by (dx, dy) canvas units.

    mode is "move" or a handle name ("n", "se", ...). Edges opposite the dragged one stay put,
    and a zone can't shrink below min_size.
    """
    x, y, w, h = orig["x"], orig["y"], orig["width"], orig["height"]
    if mode == "move":
        return x + dx, y + dy, w, h
    if "e" in mode:
        w = max(min_size, orig["width"] + dx)
    if "s" in mode:
        h = max(min_size, orig["height"] + dy)
    if "w" in mode:
        w = max(min_size, orig["width"] - dx)
        x = orig["x"] + orig["width"] - w
    if "n" in mode:
        h = max(min_size, orig["height"] - dy)
        y = orig["y"] + orig["height"] - h
    return x, y, w, h
