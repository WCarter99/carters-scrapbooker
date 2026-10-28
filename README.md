# Carter's Scrapbooker

Photo slideshow for events, using scrapbook-style templates, with a built-in template designer. Everything runs inside one window: pick photo folders, tweak settings, design templates and play, with no config files to edit.

## Run it
**From source** (Windows, macOS, Linux; Python 3.10+):
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```
**As a standalone app** (no Python needed on the machine that runs it): build it once, then copy the result anywhere.
```bash
python build.py
```
This produces `dist/CartersScrapbooker` (`dist/CartersScrapbooker.exe` on Windows). PyInstaller can't cross-compile, so build on the OS you want a program for: Windows for the `.exe`, macOS for a Mac app, Linux for a Linux binary.

## Using it
1. **Photo Sources** > Add Folder: choose any folders on your computer (photos in sub-folders are not included, add each folder you want). Folders can be switched off or removed without deleting anything.
2. **Play** in Random All (shuffle everything) or Rotating Folders (one folder at a time, in order).
3. **Settings:** seconds per photo, multi-photo mix, fullscreen, caption font and colours, caption cutoff date.
4. **Templates:** choose which scrapbook layouts may appear.
5. **Template Designer:** drag and resize photo and text zones, set colours, fonts and alignment, preview with a real photo, save. Your templates are saved separately from the built-in ones; saving an edited built-in template makes your own copy.

Everything you set is remembered between runs.

## Playback keys
| Key | Action |
|---|---|
| SPACE | Pause/resume |
| UP / DOWN | Faster / slower (shorter / longer per photo) |
| LEFT / RIGHT (or P / N) | Previous / next |
| M | Multi-photo frames: different folders vs. same folder |
| S | Reshuffle and restart |
| ESC (or R / Q) | Back to the menu |
| F11 | Toggle fullscreen (any screen) |

Each folder is its own pool: when a folder has shown all its photos it reshuffles and starts again on its own, so small folders just cycle more often.

## Designer shortcuts
Arrow keys nudge the selected zone by 1 px (hold Shift for 10), Delete removes it, Ctrl+Z / Ctrl+Y undo and redo, Ctrl+S saves.

## Captions
Photos with an EXIF date *before* the cutoff date show their year; later or missing dates show no caption.

## Where your data lives
Settings, your templates and a photo index cache are stored in your OS's per-user folders (for example `~/.config/CartersScrapbooker` on Linux, `%APPDATA%\CartersScrapbooker` on Windows). Your photos are only read, never copied or modified. To reset everything, delete that folder.

## Development
```bash
pip install -r requirements-dev.txt
python -m pytest
```

## License
MIT, see `LICENSE`. Bundled fonts (Noto Serif / Noto Sans) are under the SIL Open Font License, see `assets/fonts/LICENSE-fonts.txt`.
