# Carter's Scrapbooker

Photo slideshow for events, using scrapbook-style templates, plus a browser-based template designer.

## Setup (virtual environment)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Put photos in sub-folders of `photos/` (e.g. `photos/our_family/`), then:
```bash
python src/slideshow.py
```
Uninstall = delete the `.venv/` folder. Nothing is installed globally.

## Menu
A/B start playback (random all / rotating folders), C opens the template designer
at http://127.0.0.1:5000, D is settings (speed, templates, folders).

## Playback keys
| Key | Action |
|---|---|
| SPACE | Pause/resume |
| `<` | Slower (longer per photo, up to MAX_SPEED s) |
| `>` | Faster (shorter per photo, down to MIN_SPEED s) |
| N / P or ← / → | Next / previous |
| M | Multi-photo frames: different folders vs. same folder |
| S | Reshuffle and restart |
| R | Back to menu |
| ESC / Q | Quit |

Each folder is its own pool: when a folder has shown all its photos it reshuffles and starts again on its own, so small folders just cycle more often. Rotating mode and "same" photo-source mode take folders in order, one per frame; Random picks folders at random with no repeats until each has had a turn.

Keys also work from the terminal if the slideshow window doesn't have focus.

## Config
- `.env` (git-ignored; copy `.env.example` to create it): fonts, text colours, `METADATA_CUTOFF_DATE`, speed limits, enabled templates, `FULLSCREEN=false` for windowed testing.
- `config.json` (auto-created, git-ignored): speed, mode, enabled templates, selected folders.
- Captions: photos with an EXIF date *before* the cutoff show their year; later or missing dates show none.
- Templates live in `templates/template_<id>.json`; per-text-zone `text_color`, `font_size`, `font_family` override `.env`.

## License
MIT, see `LICENSE`.
