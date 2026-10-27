"""Scrapbook slideshow: terminal menu + pygame playback."""
import logging
import os
import os
import random
import select
import subprocess
import sys
import termios
import tty
import webbrowser
from datetime import datetime
from pathlib import Path

import pygame

import config_manager as cm
import photo_manager as pm
import template_manager as tm

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("scrapbook")
LOOKAHEAD = 10  # photos considered when filling extra zones
MULTI_MODES = ("mixed", "same")  # extra zones: prefer other folders / lead's folder
MULTI_LABELS = {"mixed": "different folders where possible", "same": "same folder"}
HINT = "SPACE pause  |  \u2190 \u2192 prev/next  |  < > speed  |  M photo mix  |  S reshuffle  |  R menu  |  ESC quit"
TERM_KEYS = {" ": "pause", "n": "next", "p": "prev", "s": "reshuffle", "r": "menu", "q": "quit",
             "m": "mix", "<": "slower", ",": "slower", ">": "faster", ".": "faster",
             "\x1b[C": "next", "\x1b[D": "prev", "\x1b[A": "faster", "\x1b[B": "slower",
             "\x1b": "quit", "\x03": "quit"}
PYGAME_KEYS = {pygame.K_ESCAPE: "quit", pygame.K_q: "quit", pygame.K_r: "menu", pygame.K_SPACE: "pause",
               pygame.K_n: "next", pygame.K_RIGHT: "next", pygame.K_p: "prev", pygame.K_LEFT: "prev",
               pygame.K_s: "reshuffle", pygame.K_m: "mix", pygame.K_UP: "faster", pygame.K_DOWN: "slower"}


def read_terminal_keys():
    """Non-blocking keypresses from the terminal (works when the window lacks focus)."""
    out = []
    fd = sys.stdin.fileno()
    while select.select([fd], [], [], 0)[0]:
        data = os.read(fd, 16).decode(errors="ignore")
        if not data:
            break
        i = 0
        while i < len(data):
            tok = data[i:i + 3] if data[i] == "\x1b" and data[i + 1:i + 2] == "[" else data[i]
            i += len(tok)
            if tok.lower() in TERM_KEYS or tok in TERM_KEYS:
                out.append(TERM_KEYS.get(tok) or TERM_KEYS[tok.lower()])
    return out


class PhotoPool:
    """One self-refilling shuffled pool per folder, plus the order folders take turns in."""

    def __init__(self, folders):
        self.photos = {f["name"]: f["photos"] for f in folders if f["photos"]}
        self.names = list(self.photos)
        self.pools = {}
        self.turn = 0
        self.bag = []

    def next_folder(self, sequential):
        """Next lead folder: strictly in order, or random without repeats until all have had a turn."""
        if sequential:
            name = self.names[self.turn % len(self.names)]
            self.turn += 1
            return name
        if not self.bag:
            self.bag = random.sample(self.names, len(self.names))
        return self.bag.pop()

    def following(self, name):
        """The other folders, in turn order, starting after `name`."""
        i = self.names.index(name)
        return self.names[i + 1:] + self.names[:i]

    def peek(self, name, k, exclude=()):
        """Up to k upcoming photos from the folder (refilling it when exhausted), skipping `exclude` paths."""
        pool = self.pools.setdefault(name, [])
        cands = [p for p in reversed(pool) if p["path"] not in exclude][:k]
        if not cands:
            fresh = [p for p in self.photos[name] if p["path"] not in exclude]
            random.shuffle(fresh)
            pool[:0] = fresh  # unseen photos stay at the end and are used first
            cands = [p for p in reversed(pool) if p["path"] not in exclude][:k]
        return cands or list(self.photos[name])[:k]  # folder smaller than the frame: allow repeats

    def take(self, name, photo):
        pool = self.pools.get(name, [])
        if photo in pool:
            pool.remove(photo)


class App:
    def __init__(self):
        self.env = cm.load_env_config()
        self.cfg = cm.load_user_config()
        cutoff = datetime.strptime(self.env["METADATA_CUTOFF_DATE"], "%Y-%m-%d")
        self.folders = pm.scan_photo_folders(ROOT / "photos", cutoff)
        self.all_templates = tm.load_templates(ROOT / "templates")
        self.designer = None

    # ---- selection helpers -------------------------------------------------
    def selected_folders(self):
        sel = self.cfg.get("selected_folders")
        return [f for f in self.folders if sel is None or f["name"] in sel]

    def enabled_templates(self):
        names = self.cfg.get("enabled_templates") or []
        enabled = [t for t in self.all_templates if tm.template_matches(t, names)]
        return enabled or self.all_templates

    def save(self):
        cm.save_user_config(self.cfg)

    # ---- slides ------------------------------------------------------------
    def build_slide(self, pool, templates, mode):
        source = self.cfg.get("multi_photo_source", "mixed")
        folder = pool.next_folder(mode == "rotating" or source == "same")
        lead = pool.peek(folder, 1)[0]
        pool.take(folder, lead)
        template = tm.pick_template(templates, lead, random)
        zones = template["photo_zones"]
        lead_idx = min(range(len(zones)), key=lambda i: tm.zone_distance(lead, zones[i]))
        photos = [None] * len(zones)
        photos[lead_idx] = lead
        others = pool.following(folder)
        for i, zone in enumerate(zones):
            if photos[i] is not None:
                continue
            if source == "same" or not others:
                src = folder
            else:  # mixed: next folder in turn, wrapping only if there are fewer folders than zones
                src = others.pop(0)
                others.append(src)
            taken = [p["path"] for p in photos if p]
            best = tm.select_best_photo_for_zone(pool.peek(src, LOOKAHEAD, taken), zone)
            pool.take(src, best)
            photos[i] = best
        caption = next((p["caption_text"] for p in photos if p["caption_text"]), None) \
            if template.get("text_zones") else None
        return {"template": template, "paths": [p["path"] for p in photos],
                "caption": caption, "count": len({p["path"] for p in photos})}

    # ---- playback ----------------------------------------------------------
    def play(self, mode):
        folders = self.selected_folders()
        if sum(f["photo_count"] for f in folders) == 0:
            print("\nNo photos in the selected folders.")
            return "menu"
        templates = self.enabled_templates()
        if not templates:
            print("\nNo valid templates found in templates/.")
            return "menu"

        self.cfg["playback_mode"] = "random_all" if mode == "random" else "rotating_folders"
        self.cfg["last_session"] = {"folders_used": [f["name"] for f in folders], "photos_shown": 0}
        self.save()

        pygame.init()
        flags = pygame.FULLSCREEN if self.env["FULLSCREEN"] else 0
        size = (0, 0) if self.env["FULLSCREEN"] else (1280, 720)
        screen = pygame.display.set_mode(size, flags)
        pygame.display.set_caption("Scrapbook Slideshow")
        pygame.mouse.set_visible(False)
        small = pygame.font.SysFont(self.env["FONT_FAMILY"], 28)
        big = pygame.font.SysFont(self.env["FONT_FAMILY"], 72, bold=True)
        clock = pygame.time.Clock()
        lo, hi = self.env["MIN_SPEED"], self.env["MAX_SPEED"]

        term_ok, old_term = sys.stdin.isatty(), None
        if term_ok:
            try:
                old_term = termios.tcgetattr(sys.stdin.fileno())
                tty.setcbreak(sys.stdin.fileno())
            except termios.error:
                term_ok = False

        pool = PhotoPool(folders)
        history, idx = [], -1
        cache = {}
        shown = 0
        paused = False
        elapsed = 0.0
        flash, flash_t = HINT, 6.0
        result = "menu"

        def scaled(slide):
            key = id(slide)
            if key not in cache:
                canvas = tm.render_template(slide["template"], slide["paths"],
                                            slide["caption"], self.env)
                sw, sh = screen.get_size()
                s = min(sw / canvas.get_width(), sh / canvas.get_height())
                cache.clear()
                cache[key] = pygame.transform.smoothscale(
                    canvas, (int(canvas.get_width() * s), int(canvas.get_height() * s)))
            return cache[key]

        def go_next():
            nonlocal idx, shown
            if idx + 1 < len(history):
                idx += 1
                return
            history.append(self.build_slide(pool, templates, mode))
            idx = len(history) - 1
            shown += history[-1]["count"]
            if len(history) > 50:
                history.pop(0)
                idx -= 1

        def restart():
            nonlocal pool, history, idx, elapsed
            pool = PhotoPool(folders)
            history, idx, elapsed = [], -1, 0.0
            go_next()

        go_next()
        running = True
        while running:
            dt = clock.tick(30) / 1000
            actions = read_terminal_keys() if term_ok else []
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    actions.append("quit")
                elif e.type == pygame.KEYDOWN:
                    act = PYGAME_KEYS.get(e.key) or TERM_KEYS.get(e.unicode)
                    if act:
                        actions.append(act)
            for act in actions:
                if act == "quit":
                    result, running = "quit", False
                elif act == "menu":
                    result, running = "menu", False
                elif act == "pause":
                    paused = not paused
                elif act == "next":
                    go_next(); elapsed = 0.0
                elif act == "prev":
                    if idx > 0:
                        idx -= 1
                    elapsed = 0.0
                elif act == "reshuffle":
                    restart()
                elif act == "slower":  # longer per photo
                    self.cfg["speed"] = min(hi, round(self.cfg["speed"] + 0.5, 1))
                    flash, flash_t = f"{self.cfg['speed']:.1f}s / photo", 2.0
                elif act == "faster":  # shorter per photo
                    self.cfg["speed"] = max(lo, round(self.cfg["speed"] - 0.5, 1))
                    flash, flash_t = f"{self.cfg['speed']:.1f}s / photo", 2.0
                elif act == "mix":
                    cur = self.cfg.get("multi_photo_source", "mixed")
                    self.cfg["multi_photo_source"] = MULTI_MODES[(MULTI_MODES.index(cur) + 1) % len(MULTI_MODES)]
                    flash, flash_t = f"Multi-photo frames: {MULTI_LABELS[self.cfg['multi_photo_source']]}", 3.0
                    # drop the unseen future slides so the change applies immediately
                    del history[idx + 1:]
            if not paused:
                elapsed += dt
                if elapsed >= self.cfg["speed"]:
                    go_next(); elapsed = 0.0

            screen.fill((0, 0, 0))
            img = scaled(history[idx])
            sw, sh = screen.get_size()
            screen.blit(img, ((sw - img.get_width()) // 2, (sh - img.get_height()) // 2))
            if flash_t > 0:
                flash_t -= dt
                t = small.render(flash, True, (255, 255, 255))
                pad = pygame.Surface((t.get_width() + 20, t.get_height() + 10))
                pad.set_alpha(150)
                screen.blit(pad, (sw - pad.get_width() - 10, 10))
                screen.blit(t, (sw - pad.get_width(), 15))
            if paused:
                t = big.render("PAUSED", True, (255, 255, 255))
                screen.blit(t, (30, 20))
            pygame.display.flip()

        if old_term:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, old_term)
        self.cfg["last_session"]["photos_shown"] = shown
        self.save()
        pygame.quit()
        return result

    # ---- terminal UI -------------------------------------------------------
    def print_menu(self):
        bar = "═" * 40
        print(f"\n{bar}\n    ENGAGEMENT PHOTO SLIDESHOW\n{bar}\n")
        sel = {f["name"] for f in self.selected_folders()}
        if not self.folders:
            print("📁 No photo folders found. Add sub-folders of images to photos/\n")
        else:
            print("📁 Photo Folders Found:")
            for i, f in enumerate(self.folders, 1):
                mark = " " if f["name"] in sel else "✗"
                print(f"   [{i}]{mark}{f['name']:<30} ({f['photo_count']} photos)")
            print("   (✗ = deselected in Settings)")
        en = self.enabled_templates()
        print(f"\n🎨 Templates Enabled: {len(en)}")
        for t in en:
            print(f"   • {t['name']}")
        print(f"\nSpeed: {self.cfg['speed']}s per photo")
        print(f"Multi-photo frames: {MULTI_LABELS[self.cfg.get('multi_photo_source', 'mixed')]}")
        print("""
─────────────────────────────────────────
PLAYBACK MODE:
   [A] Random All          (shuffle all photos)
   [B] Rotating Folders    (1 from each folder in turn)
   [C] Template Designer   (opens in your browser)
   [D] Settings            (speed, templates, folders)
   [Q] Quit
""")

    def settings(self):
        while True:
            print("\nSETTINGS:  [1] Speed  [2] Templates  [3] Folders  [4] Multi-photo source  [B] Back")
            c = input("> ").strip().lower()
            if c == "1":
                try:
                    v = float(input(f"Seconds per photo ({self.env['MIN_SPEED']}-{self.env['MAX_SPEED']}): "))
                    self.cfg["speed"] = max(self.env["MIN_SPEED"], min(self.env["MAX_SPEED"], v))
                except ValueError:
                    print("Not a number.")
            elif c == "2":
                self.toggle("enabled_templates", [(t["_file"], t["name"]) for t in self.all_templates],
                            {t["_file"] for t in self.enabled_templates()})
            elif c == "3":
                self.toggle("selected_folders", [(f["name"], f["name"]) for f in self.folders],
                            {f["name"] for f in self.selected_folders()})
            elif c == "4":
                cur = self.cfg.get("multi_photo_source", "mixed")
                self.cfg["multi_photo_source"] = MULTI_MODES[(MULTI_MODES.index(cur) + 1) % len(MULTI_MODES)]
                print(f"Frames with several photos now use: {MULTI_LABELS[self.cfg['multi_photo_source']]}")
            elif c == "b":
                break
            self.save()

    def toggle(self, key, items, current):
        while True:
            for i, (k, label) in enumerate(items, 1):
                print(f"  [{i}] [{'x' if k in current else ' '}] {label}")
            c = input("Number to toggle, Enter when done: ").strip()
            if not c:
                break
            if c.isdigit() and 1 <= int(c) <= len(items):
                k = items[int(c) - 1][0]
                current ^= {k}
        self.cfg[key] = sorted(current)

    def open_designer(self):
        if self.designer and self.designer.poll() is None:
            print("Designer already running.")
        else:
            self.designer = subprocess.Popen([sys.executable, str(ROOT / "src" / "web_designer.py")])
        url = f"http://127.0.0.1:{self.env['DESIGNER_PORT']}"
        print(f"Template designer at {url} (restart the slideshow app to load new templates)")
        webbrowser.open(url)

    def run(self):
        try:
            while True:
                self.print_menu()
                c = input("Choose (A/B/C/D/Q): ").strip().lower()
                if c in ("a", "b"):
                    if self.play("random" if c == "a" else "rotating") == "quit":
                        break
                elif c == "c":
                    self.open_designer()
                elif c == "d":
                    self.settings()
                elif c == "q":
                    break
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            if self.designer and self.designer.poll() is None:
                self.designer.terminate()
            self.save()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    App().run()
