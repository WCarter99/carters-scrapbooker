# Roadmap

Plans for Carter's Scrapbooker. Nothing here is promised or scheduled, and the order may change. Ideas and feedback are welcome (see [CONTRIBUTING.md](CONTRIBUTING.md)).

## Where it is today
- Pygame app with an in-window menu: photo folder picker, settings, template picker and a template designer
- Scrapbook-style templates; settings, folders and your own templates saved in the OS user config directory
- Fonts and default templates bundled; `python build.py` makes a standalone executable (no Python needed to run it)

## Next: polish the self-contained app
- [x] **Main menu, settings, photo source picker, persistent config**
- [x] **Template designer inside pygame** (no web server)
- [x] **Bundled assets:** default templates and fonts ship inside the executable
- [x] **Packaging:** `build.py` (PyInstaller) builds for the OS it runs on
- [ ] **Tested builds on Windows and macOS:** so far only built and run on Linux
- [ ] **Automated releases:** GitHub Actions builds for all three OSes and attaches them to a GitHub Release
- [ ] **App icon and installer-style polish**

## Stretch goals
- [ ] **Music:** background audio during the slideshow
- [ ] **Eras mode:** put a set of folders in order, show every photo in one folder (randomly) before moving on to the next
- [ ] **Title cards:** customizable cards that can play at the start of a folder, or appear at intervals after a set number of slides
- [ ] **Slide transitions** exactly what it sounds like

## Not planned
- Cloud syncing or accounts
- Photo editing

Have an idea that isn't listed? Open an issue.
