"""Entry point (also what PyInstaller builds)."""
import logging

from app import App
from screens.menu import MenuScreen
from screens.playback import PlaybackScreen


def main():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    app = App()
    app.register("menu", MenuScreen(app))
    app.register("playback", PlaybackScreen(app))
    app.run("menu")


if __name__ == "__main__":
    main()
