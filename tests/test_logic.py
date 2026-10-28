import json
import random

import config_manager as cm
import paths
import template_manager as tm
from playback import PhotoPool, build_slide
from utils import parse_color


def photo(name, ratio=1.5, folder="a", caption=None):
    return {"path": f"/x/{folder}/{name}", "filename": name, "folder": folder,
            "aspect_ratio": ratio, "caption_text": caption}


def folders():
    return [{"name": n, "photos": [photo(f"{n}{i}.jpg", folder=n) for i in range(3)]} for n in ("a", "b", "c")]


def tpl(n_zones, lo=0, hi=100):
    return {"id": f"t{n_zones}", "name": "t", "canvas_width": 100, "canvas_height": 100,
            "photo_zones": [{"id": f"p{i}", "x": 0, "y": 0, "width": 10, "height": 10,
                             "aspect_ratio_range": [lo, hi]} for i in range(n_zones)]}


def test_pool_rotates_in_order():
    pool = PhotoPool(folders())
    assert [pool.next_folder(True) for _ in range(4)] == ["a", "b", "c", "a"]


def test_pool_random_visits_every_folder_per_round():
    pool = PhotoPool(folders())
    assert sorted(pool.next_folder(False) for _ in range(3)) == ["a", "b", "c"]


def test_pool_refills_when_exhausted():
    pool = PhotoPool(folders())
    for _ in range(7):
        p = pool.peek("a", 1)[0]
        pool.take("a", p)
        assert p["folder"] == "a"


def test_build_slide_fills_zones_without_repeats():
    random.seed(1)
    pool = PhotoPool(folders())
    slide = build_slide(pool, [tpl(3)], "rotating", "mixed")
    assert len(slide["paths"]) == 3 and slide["count"] == 3


def test_build_slide_same_source_stays_in_folder():
    pool = PhotoPool(folders())
    slide = build_slide(pool, [tpl(3)], "random", "same")
    assert len({p.split("/")[2] for p in slide["paths"]}) == 1


def test_pick_template_prefers_fitting_zone():
    wide, tall = tpl(1, 1.5, 3), tpl(1, 0.3, 0.8)
    assert tm.pick_template([wide, tall], photo("w.jpg", 2.0), random) is wide
    assert tm.pick_template([wide, tall], photo("t.jpg", 0.5), random) is tall


def test_validate_template():
    assert tm.validate_template(tpl(1))
    bad = tpl(1)
    bad["photo_zones"][0]["width"] = 0
    assert not tm.validate_template(bad)
    assert not tm.validate_template({"id": "x"})


def test_bundled_templates_all_valid():
    loaded = tm.load_templates(paths.resource_path("templates"))
    assert len(loaded) == len(list((paths.resource_path("templates")).glob("*.json"))) >= 10


def test_parse_color():
    assert parse_color("rgba(0, 0, 0, 0.5)") == (0, 0, 0, 127)
    assert parse_color("#ff0000")[:3] == (255, 0, 0)
    assert parse_color("nonsense-colour") == (255, 255, 255, 255)


def test_config_defaults_and_roundtrip(tmp_path):
    p = tmp_path / "config.json"
    cfg = cm.load_config(p)
    assert cfg["speed"] == 7.0 and cfg["source_folders"] == []
    cfg["speed"] = 3.5
    cm.save_config(cfg, p)
    assert cm.load_config(p)["speed"] == 3.5


def test_config_clamps_speed_and_ignores_corrupt(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"speed": 999}))
    assert cm.load_config(p)["speed"] == 30.0
    p.write_text("{not json")
    assert cm.load_config(p)["speed"] == 7.0


def test_config_migrates_legacy_keys_and_bad_cutoff(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"selected_folders": ["x"], "caption_cutoff_date": "garbage"}))
    cfg = cm.load_config(p)
    assert "selected_folders" not in cfg and cfg["caption_cutoff_date"] == "2026-08-10"


def test_scan_cache_skips_unchanged_files(tmp_path, monkeypatch):
    from datetime import datetime

    from PIL import Image

    import photo_manager as pm
    for i in range(3):
        Image.new("RGB", (40, 20)).save(tmp_path / f"{i}.jpg")
    cache, cutoff = {}, datetime(2026, 1, 1)
    first = pm.scan_folder(tmp_path, cutoff, cache)
    assert first["photo_count"] == 3 and len(cache) == 3 and first["photos"][0]["aspect_ratio"] == 2.0
    monkeypatch.setattr(pm, "get_aspect_ratio", lambda p: (_ for _ in ()).throw(AssertionError("re-read")))
    again = pm.scan_folder(tmp_path, cutoff, cache)
    assert again["photo_count"] == 3
