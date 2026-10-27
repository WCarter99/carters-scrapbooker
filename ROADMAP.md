# Roadmap

Plans for Carter's Scrapbooker. Nothing here is promised or scheduled, and the order may change. Ideas and feedback are welcome (see [CONTRIBUTING.md](CONTRIBUTING.md)).

## Where it is today
- Pygame slideshow with scrapbook-style templates
- Browser-based template designer (Flask)
- Setup through a Python virtual environment, with options set in `.env` and `config.json`
- Photos are read from sub-folders of the `photos/` directory

## Next: self-contained app
Goal: a single executable anyone can download and run on any major OS (Windows, macOS, Linux), with no Python install, virtual environment, or file editing.

- [ ] **Main menu screen:** move options that are currently set before launch (via `.env` and the command line) into an in-app menu
- [ ] **Settings menu:** configure speed, playback mode, enabled templates, fonts, colours, caption cutoff date, and fullscreen from inside the app
- [ ] **Photo source picker:** choose any folders on disk to pull photos from, instead of relying on a bundled `photos/` folder
- [ ] **Persistent user config:** store settings and chosen folders in the OS-appropriate user config directory
- [ ] **Template designer inside pygame:** replace the Flask/browser designer so the app has no web server dependency
- [ ] **Packaging:** build executables for Windows, macOS and Linux (e.g. PyInstaller), ideally via automated releases on GitHub
- [ ] **Bundled assets:** ship default templates and fonts inside the executable

## Stretch goals
- [ ] **Music:** background audio during the slideshow
- [ ] **Eras mode:** put a set of folders in order, show every photo in one folder (randomly) before moving on to the next
- [ ] **Title cards:** customizable cards that can play at the start of a folder, or appear at intervals after a set number of slides
- [ ] **Slide transitions** exactly what it sounds like

## Not planned
- Cloud syncing or accounts
- Photo editing

Have an idea that isn't listed? Open an issue.
