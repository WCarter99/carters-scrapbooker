"""Window, event loop and screen switching."""
import logging

import pygame
import pygame_gui

import config_manager as cm
import paths
import template_manager as tm
from library import Library

log = logging.getLogger("scrapbook")
WINDOW_SIZE = (1280, 720)
FPS = 30


class App:
    def __init__(self):
        self.cfg = cm.load_config()
        self.library = Library(self.cfg)
        self.templates = tm.load_all_templates()
        pygame.init()
        pygame.display.set_caption("Carter's Scrapbooker")
        self.fullscreen = False
        self.screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
        self.manager = self._new_manager()
        self.clock = pygame.time.Clock()
        self.screens = {}
        self.current = None
        self.running = True

    def _new_manager(self):
        theme = paths.resource_path("assets", "theme.json")
        return pygame_gui.UIManager(self.screen.get_size(), str(theme) if theme.exists() else None)

    def register(self, name, screen):
        self.screens[name] = screen

    def goto(self, name, **kwargs):
        if self.current:
            self.current.exit()
        self.manager.clear_and_reset()
        self.current = self.screens[name]
        self.current.enter(**kwargs)

    def enabled_templates(self):
        names = self.cfg.get("enabled_templates")
        if names is None:
            return self.templates
        picked = [t for t in self.templates if tm.template_matches(t, names)]
        return picked or self.templates

    def save(self):
        cm.save_config(self.cfg)

    def set_fullscreen(self, on):
        self.fullscreen = on
        if on:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
        self.manager.set_window_resolution(self.screen.get_size())
        if hasattr(self.current, "on_resize"):
            self.current.on_resize()

    def toggle_fullscreen(self):
        self.set_fullscreen(not self.fullscreen)

    def quit(self):
        self.running = False

    def run(self, first="menu"):
        self.library.scan()
        self.goto(first)
        try:
            while self.running:
                dt = self.clock.tick(FPS) / 1000
                for e in pygame.event.get():
                    if e.type == pygame.QUIT:
                        self.quit()
                    elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                        self.toggle_fullscreen()
                    elif e.type == pygame.VIDEORESIZE and not self.fullscreen:
                        self.manager.set_window_resolution(e.size)
                        if hasattr(self.current, "on_resize"):
                            self.current.on_resize()
                    self.manager.process_events(e)
                    self.current.handle_event(e)
                self.library.scan()  # picks up folders added while a scan was finishing
                self.manager.update(dt)
                self.current.update(dt)
                self.screen.fill((24, 24, 28))
                self.current.draw(self.screen)
                self.manager.draw_ui(self.screen)
                pygame.display.flip()
        finally:
            self.save()
            pygame.quit()
