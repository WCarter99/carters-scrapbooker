"""Entry point (also what PyInstaller builds)."""
import logging

from app import App
from screens.menu import MenuScreen
from screens.playback import PlaybackScreen
from screens.settings import SettingsScreen
from screens.sources import SourcesScreen
from screens.templates import TemplatesScreen


def main():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    app = App()
    app.register("menu", MenuScreen(app))
    for name, cls in (("playback", PlaybackScreen), ("sources", SourcesScreen),
                      ("templates", TemplatesScreen), ("settings", SettingsScreen)):
        app.register(name, cls(app))
    app.run("menu")


if __name__ == "__main__":
    main()
