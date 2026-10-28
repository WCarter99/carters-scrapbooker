import copy

import designer.geometry as g
import designer.model as m
import paths


def z(x=100, y=100, w=200, h=100):
    return {"x": x, "y": y, "width": w, "height": h}


def test_fit_scale():
    assert g.fit_scale(1920, 1080, 960, 960) == 0.5
    assert g.fit_scale(1000, 1000, 2000, 500) == 0.5


def test_canvas_screen_roundtrip():
    rect = g.canvas_to_screen(z(100, 50), 0.5, (10, 20))
    assert rect == (60, 45, 100, 50)
    assert g.screen_to_canvas((60, 45), 0.5, (10, 20)) == (100, 50)


def test_move_and_resize_edges():
    o = z()
    assert g.apply_drag(o, "move", 10, -5) == (110, 95, 200, 100)
    assert g.apply_drag(o, "se", 20, 30) == (100, 100, 220, 130)
    assert g.apply_drag(o, "nw", 20, 10) == (120, 110, 180, 90)  # far corner stays at (300, 200)
    x, y, w, h = g.apply_drag(o, "w", 500, 0)  # can't shrink below the minimum; right edge stays at 300
    assert (w, x + w) == (g.MIN_SIZE, 300)


def test_handle_and_zone_hit_testing():
    rect = (100, 100, 200, 100)
    assert g.handle_at(rect, (101, 99)) == "nw"
    assert g.handle_at(rect, (200, 201)) == "s"
    assert g.handle_at(rect, (200, 150)) is None
    low, high = z(0, 0, 100, 100), z(50, 50, 100, 100)
    assert g.zone_at([low, high], (60, 60), 1.0, (0, 0)) is high  # later zones draw on top
    assert g.zone_at([low, high], (10, 10), 1.0, (0, 0)) is low
    assert g.zone_at([low, high], (500, 500), 1.0, (0, 0)) is None


def test_unique_ids_and_duplicate():
    t = m.blank_template()
    assert m.new_photo_zone(t)["id"] == "photo_2"
    t["photo_zones"].append(m.new_photo_zone(t))
    assert m.new_photo_zone(t)["id"] == "photo_3"
    d = m.duplicate_zone(t, t["photo_zones"][0])
    assert d["id"] == "photo_3" and d["x"] == 90 and "aspect_ratio_range" in d


def test_history_undo_redo():
    t, h = m.blank_template(), m.History()
    h.push(t)
    t2 = copy.deepcopy(t)
    t2["name"] = "changed"
    assert h.step_back(t2)["name"] == ""
    assert h.step_forward(t)["name"] == "changed"
    assert h.step_forward(t) is None and m.History().step_back(t) is None


def test_save_and_delete_user_template(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "user_templates_dir", lambda: tmp_path)
    t = m.blank_template()
    path, err = m.save_user_template(t)
    assert path is None and "ID" in err
    t["id"], t["_file"], t["_source"] = "my new/one", "x", "bundled"
    path, err = m.save_user_template(t)
    assert err is None and path.name == "template_my_newone.json"
    saved = path.read_text()
    assert "_file" not in saved and '"name": "my_newone"' in saved
    t["photo_zones"][0]["width"] = 0
    assert m.save_user_template(t)[0] is None
    assert m.delete_user_template("my_newone") and not m.delete_user_template("my_newone")
