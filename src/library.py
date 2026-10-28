"""The user's photo sources, scanned on a background thread."""
import json
import logging
import os
import threading
from pathlib import Path

import config_manager as cm
import paths
import photo_manager as pm

log = logging.getLogger("scrapbook")


class Library:
    def __init__(self, cfg):
        self.cfg = cfg
        self.scanned = {}      # path -> folder dict
        self.progress = (0, 0)  # folders done, folders total
        self._lock = threading.Lock()
        self._thread = None
        self.cache = self._load_cache()

    @staticmethod
    def _cache_file():
        return paths.cache_dir() / "photo_index.json"

    def _load_cache(self):
        try:
            data = json.loads(self._cache_file().read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_cache(self):
        tmp = self._cache_file().with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(self.cache), encoding="utf-8")
            os.replace(tmp, self._cache_file())
        except OSError as e:
            log.warning("Could not save photo cache: %s", e)

    @property
    def scanning(self):
        return self._thread is not None and self._thread.is_alive()

    def _pending(self):
        return [s["path"] for s in self.cfg["source_folders"] if s["path"] not in self.scanned]

    def scan(self):
        """Scan every configured source not scanned yet (a running scan also picks up newly added ones)."""
        if not self.scanning and self._pending():
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def _run(self):
        cutoff = cm.parse_cutoff(self.cfg["caption_cutoff_date"])
        done = 0
        while True:
            with self._lock:
                todo = self._pending()
                if not todo:
                    return
                path = todo[0]
                self.progress = (done, done + len(todo))
            try:
                folder = pm.scan_folder(path, cutoff, self.cache)
            except OSError as e:
                log.warning("Could not scan %s: %s", path, e)
                folder = None
            with self._lock:
                self.scanned[path] = folder
            self._save_cache()
            done += 1

    def rescan(self):
        """Forget scan results (e.g. after the caption cutoff date changed)."""
        self.scanned.clear()
        self.scan()

    def add(self, path):
        path = str(Path(path))
        if any(s["path"] == path for s in self.cfg["source_folders"]):
            return
        self.cfg["source_folders"].append({"path": path, "enabled": True})
        self.scan()

    def remove(self, path):
        self.cfg["source_folders"] = [s for s in self.cfg["source_folders"] if s["path"] != path]
        self.scanned.pop(path, None)

    def active_folders(self):
        """Enabled, scanned folders with at least one photo, with unique display names."""
        out, seen = [], set()
        with self._lock:
            for s in self.cfg["source_folders"]:
                f = self.scanned.get(s["path"])
                if not s["enabled"] or not f or not f["photos"]:
                    continue
                name = f["name"]
                if name in seen:
                    name = f"{Path(f['path']).parent.name}/{name}"
                seen.add(name)
                out.append({**f, "name": name})
        return out

    def total_photos(self):
        return sum(f["photo_count"] for f in self.active_folders())
