# Contributing

Thanks for your interest in Carter's Scrapbooker! This is a small personal project, so contributions are welcome but reviewed at a relaxed pace.

## Ways to help
- **Report bugs:** open an issue with your OS, Python version, what you expected, and what happened. Include any error output.
- **Suggest features:** open an issue before building something large. Check [ROADMAP.md](ROADMAP.md) first, since it may already be planned.
- **Submit code:** fixes and improvements are welcome via pull request.
- **Share templates:** new scrapbook templates (`templates/template_<id>.json`) are a great, low-effort contribution.

## Getting set up
```bash
git clone https://github.com/<owner>/carters-scrapbooker.git
cd carters-scrapbooker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python src/slideshow.py
```
Set `FULLSCREEN=false` in `.env` for windowed testing.

## Pull requests
1. Open an issue first for anything beyond a small fix, so we can agree on the approach.
2. Fork the repo and create a branch from `main` (e.g. `fix-caption-crash`).
3. Keep each PR focused on one change.
4. Match the existing code style and naming.
5. Test by running the slideshow and the template designer to confirm nothing broke.
6. Describe what changed and why in the PR description.

PRs are merged at the maintainer's discretion. A PR may be declined if it doesn't fit the project's direction, and that's not a judgment on the work.

## Privacy
Never commit personal photos, `.env`, or `config.json`. They are gitignored, but check `git status` before committing. When sharing screenshots in issues or PRs, use sample images.

## License
By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
