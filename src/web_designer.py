"""Flask server for the web-based template designer."""
import json
import logging
import re
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

import config_manager as cm
from template_manager import validate_template

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "templates"
UPLOAD_DIR = ROOT / ".designer_uploads"
ALLOWED = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


def safe_id(raw) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", str(raw).replace(" ", "_"))


@app.get("/")
def index():
    return send_from_directory(ROOT / "web", "index.html")


@app.post("/api/upload_sample")
def upload_sample():
    f = request.files.get("photo")
    if not f or Path(f.filename).suffix.lower() not in ALLOWED:
        return jsonify(error="Upload an image file"), 400
    UPLOAD_DIR.mkdir(exist_ok=True)
    name = uuid.uuid4().hex + Path(f.filename).suffix.lower()
    f.save(UPLOAD_DIR / name)
    return jsonify(url=f"/uploads/{name}")


@app.get("/uploads/<name>")
def uploads(name):
    return send_from_directory(UPLOAD_DIR, name)


@app.get("/api/templates")
def list_templates():
    out = []
    for f in sorted(TEMPLATE_DIR.glob("*.json")):
        try:
            t = json.loads(f.read_text())
            out.append({"id": t["id"], "name": t.get("name", t["id"])})
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    return jsonify(out)


def _path_for(tid):
    tid = safe_id(tid)
    return TEMPLATE_DIR / f"template_{tid}.json" if tid else None


@app.get("/api/template/<tid>")
def get_template(tid):
    p = _path_for(tid)
    if not p or not p.exists():
        return jsonify(error="Not found"), 404
    return jsonify(json.loads(p.read_text()))


@app.delete("/api/template/<tid>")
def delete_template(tid):
    p = _path_for(tid)
    if not p or not p.exists():
        return jsonify(error="Not found"), 404
    p.unlink()
    return jsonify(ok=True)


@app.post("/api/save_template")
def save_template():
    t = request.get_json(silent=True) or {}
    t["id"] = safe_id(t.get("id", ""))
    if not t["id"]:
        return jsonify(error="Template ID required"), 400
    if not validate_template(t):
        return jsonify(error="Template failed validation"), 400
    TEMPLATE_DIR.mkdir(exist_ok=True)
    _path_for(t["id"]).write_text(json.dumps(t, indent=2))
    return jsonify(ok=True, file=f"templates/template_{t['id']}.json")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    port = cm.load_env_config()["DESIGNER_PORT"]
    app.run(host="127.0.0.1", port=port, debug=False)
