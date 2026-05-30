"""
ui/main_window.py

The main application window and game loop for PixelAnimationLab.

This class is responsible for:
- Initializing pygame and opening the window
- Running the main event + render loop
- Coordinating high-level UI components (canvas, panels, timeline, etc.)

Current state: Minimal scaffolding. The goal is to get a clean, running
pygame window as quickly as possible so we can iteratively build the real UI
on top of it.

Design goals:
- Keep the main loop simple and readable
- Make it easy to add new panels and input handling later
- Separate "application state" from "rendering" where practical
"""

import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, MOUSEWHEEL

from utils.config import Config
from ui.canvas import Canvas
from core.layer import Layer

from ui.panels.layers_panel import LayersPanel


class MainWindow:
    """The primary application window and event loop."""

    def __init__(self, config: Config):
        self.config = config
        self.screen: pygame.Surface | None = None
        self.clock: pygame.time.Clock | None = None
        self.running = False

        # === Real Canvas ===
        self.canvas: Canvas
        self._init_demo_canvas()

        # === Real Panels ===
        self.layers_panel = LayersPanel()

        # Mouse tracking (used by Canvas for cursor-centered zoom)
        self.mouse_pos: tuple[int, int] = (0, 0)

    def _init_demo_canvas(self) -> None:
        """Create a small demo layer so the Canvas has something to display."""
        demo_layer = Layer(32, 32, name="Demo Layer")
        # Draw a simple test pattern
        for y in range(32):
            for x in range(32):
                if (x + y) % 8 == 0:
                    demo_layer.set_pixel(x, y, (255, 200, 80, 255))
                elif x % 4 == 0 or y % 4 == 0:
                    demo_layer.set_pixel(x, y, (60, 60, 80, 255))

        self.canvas = Canvas(32, 32, layer=demo_layer)

        # Future: We will store references to panels here
        # self.canvas = None
        # self.layers_panel = None
        # self.timeline = None
        # etc.

    def init(self) -> None:
        """Initialize pygame and create the window."""
        pygame.init()
        pygame.display.set_caption(self.config.title)

        self.screen = pygame.display.set_mode(
            (self.config.width, self.config.height),
            pygame.RESIZABLE
        )
        self.clock = pygame.time.Clock()
        self.running = True

        # TODO: Initialize UI components here once they exist

    def handle_events(self) -> None:
        """Process all pending pygame events."""
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False

                # Note: + / - zoom handling was moved to the Canvas class.
                # These keys are now free for future shortcuts (e.g. tool options).

            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos

            # Forward to real panels (they return True if they consumed the event)
            if self.layers_panel.handle_event(event):
                pass  # event consumed

            # TODO: Forward events to active panels / tools
            # For now, the Canvas handles its own panning and zoom input
            self.canvas.handle_event(event)

    def update(self, dt: float) -> None:
        """Update game / UI state (not rendering)."""
        self.layers_panel.update(dt)
        # TODO: Update animations, hover states, etc.

    # Note: Zoom and pan logic now lives in the Canvas class (ui-step2)

    def draw(self) -> None:
        """Render everything to the screen."""
        assert self.screen is not None

        # Clear background
        self.screen.fill(self.config.bg_color)

        # Placeholder content - will be replaced by real UI panels
        self._draw_placeholder()

        pygame.display.flip()

    def _draw_placeholder(self) -> None:
        """Rough editor-style layout using fake panels + a properly centered, zoomable canvas.

        The central canvas is now dynamically centered in the available working area
        and respects the current zoom level.
        """
        assert self.screen is not None
        w, h = self.config.width, self.config.height

        # Colors
        panel_bg = self.config.panel_bg
        text_col = self.config.text_color
        accent = self.config.accent_color

        # Fonts
        font_title = pygame.font.SysFont("Arial", 18, bold=True)
        font_normal = pygame.font.SysFont("Arial", 14)
        font_small = pygame.font.SysFont("Arial", 12)

        # === Dimensions for fake panels (will become real components) ===
        top_height = 32
        tools_width = 48
        layers_width = 180
        timeline_height = 80

        # === Top Bar ===
        pygame.draw.rect(self.screen, (25, 25, 28), (0, 0, w, top_height))
        title = font_title.render("PixelAnimationLab", True, text_col)
        self.screen.blit(title, (12, 7))

        menus = ["File", "Edit", "View", "Image", "Animation"]
        x = 180
        for menu in menus:
            surf = font_normal.render(menu, True, text_col)
            self.screen.blit(surf, (x, 8))
            x += surf.get_width() + 18

        # === Left Tools Panel ===
        pygame.draw.rect(self.screen, panel_bg, (0, top_height, tools_width, h - top_height))
        pygame.draw.line(self.screen, (60, 60, 65), (tools_width, top_height), (tools_width, h), 1)

        tools = ["Pencil", "Eraser", "Fill", "Select", "Move", "Zoom"]
        y = top_height + 12
        for tool in tools:
            surf = font_small.render(tool, True, text_col)
            self.screen.blit(surf, (6, y))
            y += 22

        # === Real Layers Panel ===
        layers_rect = pygame.Rect(w - layers_width, top_height, layers_width, h - top_height - timeline_height)
        self.layers_panel.set_rect(layers_rect)
        self.layers_panel.draw(self.screen)

        # === Bottom Timeline ===
        pygame.draw.rect(self.screen, (35, 35, 40), (0, h - timeline_height, w, timeline_height))
        pygame.draw.line(self.screen, (60, 60, 65), (0, h - timeline_height), (w, h - timeline_height), 1)

        tlabel = font_normal.render(f"Timeline  |  Frame 1 / 12   FPS: 12   Zoom: {self.canvas.get_zoom()}x", True, text_col)
        self.screen.blit(tlabel, (12, h - timeline_height + 8))

        fx = 20
        for i in range(8):
            color = accent if i == 0 else (70, 70, 75)
            pygame.draw.rect(self.screen, color, (fx, h - 55, 32, 32), border_radius=2)
            pygame.draw.rect(self.screen, (50, 50, 55), (fx, h - 55, 32, 32), 1, border_radius=2)
            fx += 38

        # ============================================================
        # === REAL CANVAS (ui-step2) ===
        # ============================================================

        # Define the working area for the canvas
        work_left = tools_width + 8
        work_right = w - layers_width - 8
        work_top = top_height + 8
        work_bottom = h - timeline_height - 8

        canvas_rect = pygame.Rect(
            work_left,
            work_top,
            work_right - work_left,
            work_bottom - work_top,
        )

        # Let the real Canvas draw itself
        self.canvas.draw(self.screen, canvas_rect)

        # Small label above the real canvas (temporary)
        clabel = font_normal.render("Real Canvas (ui-step2)", True, text_col)
        self.screen.blit(clabel, (canvas_rect.x + 8, canvas_rect.y - 18))

    def run(self) -> None:
        """Main application loop."""
        self.init()

        while self.running:
            dt = self.clock.tick(self.config.fps) / 1000.0

            self.handle_events()
            self.update(dt)
            self.draw()

        self.shutdown()

    def shutdown(self) -> None:
        """Clean up pygame resources."""
        pygame.quit()
        print("PixelAnimationLab closed cleanly.")
