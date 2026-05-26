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


class MainWindow:
    """The primary application window and event loop."""

    # Smooth zoom steps. Much nicer for pixel art work than pure doubling.
    # Feel free to tweak this list.
    ZOOM_LEVELS: list[int] = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64]

    def __init__(self, config: Config):
        self.config = config
        self.screen: pygame.Surface | None = None
        self.clock: pygame.time.Clock | None = None
        self.running = False

        # === Canvas state (will move to a proper Canvas class later) ===
        self.zoom: int = self.config.default_zoom
        self.logical_width: int = 32   # Size of the sprite in pixels (temporary)
        self.logical_height: int = 32

        # Screen position of the top-left corner of logical pixel (0,0)
        self.canvas_x: int = 0
        self.canvas_y: int = 0

        self.mouse_pos: tuple[int, int] = (0, 0)
        self._canvas_initialized: bool = False  # used to center on first draw

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

                # === Basic Zoom Controls (temporary, will move to Canvas) ===
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                    self.zoom_in(around=self.mouse_pos)
                elif event.key == pygame.K_MINUS:
                    self.zoom_out(around=self.mouse_pos)

            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos

            elif event.type == MOUSEWHEEL:
                # Ctrl + Scroll Wheel = Zoom (very common in pixel art editors)
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_CTRL:
                    if event.y > 0:
                        self.zoom_in(around=self.mouse_pos)
                    elif event.y < 0:
                        self.zoom_out(around=self.mouse_pos)

            # TODO: Forward events to active panels / tools
            # Example:
            # self.canvas.handle_event(event)

    def update(self, dt: float) -> None:
        """Update game / UI state (not rendering)."""
        # TODO: Update animations, hover states, etc.
        pass

    # === Temporary Zoom Helpers (will live in Canvas class later) ===

    def zoom_in(self, around: tuple[int, int] | None = None) -> None:
        """Increase zoom level using the smooth ZOOM_LEVELS list.
        If `around` (screen coords) is provided and valid, the zoom centers on that point."""
        new_zoom = self._get_next_zoom_level(self.zoom, direction=1)
        self._apply_zoom(new_zoom, around)

    def zoom_out(self, around: tuple[int, int] | None = None) -> None:
        """Decrease zoom level using the smooth ZOOM_LEVELS list."""
        new_zoom = self._get_next_zoom_level(self.zoom, direction=-1)
        self._apply_zoom(new_zoom, around)

    def _get_next_zoom_level(self, current: int, direction: int) -> int:
        """Return the next appropriate zoom level from ZOOM_LEVELS.
        direction = 1 for zoom in, -1 for zoom out."""
        levels = self.ZOOM_LEVELS
        if direction > 0:
            for level in levels:
                if level > current:
                    return level
            return levels[-1]  # already at max
        else:
            for level in reversed(levels):
                if level < current:
                    return level
            return levels[0]  # already at min

    def _apply_zoom(self, new_zoom: int, around: tuple[int, int] | None = None) -> None:
        """Core zoom logic. Zooms around the given screen point if provided and
        the point is inside the working area."""
        if new_zoom == self.zoom:
            return

        # Determine the anchor point in screen space
        if around is None:
            anchor_x, anchor_y = self.mouse_pos
        else:
            anchor_x, anchor_y = around

        # Only do cursor-centered zoom if the mouse is inside the working area
        # (between panels). Otherwise just change zoom and keep current offset.
        work_rect = self._get_working_rect()
        if not work_rect.collidepoint(anchor_x, anchor_y):
            self.zoom = new_zoom
            return

        # Convert anchor screen point to logical pixel coordinates (before zoom change)
        logical_x = (anchor_x - self.canvas_x) / self.zoom
        logical_y = (anchor_y - self.canvas_y) / self.zoom

        # Change zoom
        self.zoom = new_zoom

        # Reposition canvas so the same logical point stays under the anchor
        self.canvas_x = int(anchor_x - logical_x * self.zoom)
        self.canvas_y = int(anchor_y - logical_y * self.zoom)

    def _get_working_rect(self) -> pygame.Rect:
        """Returns the rectangle of the central working area (excluding fake panels)."""
        w, h = self.config.width, self.config.height
        top = 32 + 8
        left = 48 + 8
        right = w - 180 - 8
        bottom = h - 80 - 8
        return pygame.Rect(left, top, right - left, bottom - top)

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

        # === Right Layers Panel ===
        pygame.draw.rect(self.screen, panel_bg, (w - layers_width, top_height, layers_width, h - top_height - timeline_height))
        pygame.draw.line(self.screen, (60, 60, 65), (w - layers_width, top_height), (w - layers_width, h - timeline_height), 1)

        label = font_normal.render("Layers", True, accent)
        self.screen.blit(label, (w - layers_width + 10, top_height + 8))

        layers = ["Background", "Character", "Effects", "UI"]
        ly = top_height + 35
        for i, layer in enumerate(layers):
            prefix = "● " if i == 1 else "○ "
            surf = font_small.render(prefix + layer, True, text_col)
            self.screen.blit(surf, (w - layers_width + 10, ly))
            ly += 18

        # === Bottom Timeline ===
        pygame.draw.rect(self.screen, (35, 35, 40), (0, h - timeline_height, w, timeline_height))
        pygame.draw.line(self.screen, (60, 60, 65), (0, h - timeline_height), (w, h - timeline_height), 1)

        tlabel = font_normal.render(f"Timeline  |  Frame 1 / 12   FPS: 12   Zoom: {self.zoom}x", True, text_col)
        self.screen.blit(tlabel, (12, h - timeline_height + 8))

        fx = 20
        for i in range(8):
            color = accent if i == 0 else (70, 70, 75)
            pygame.draw.rect(self.screen, color, (fx, h - 55, 32, 32), border_radius=2)
            pygame.draw.rect(self.screen, (50, 50, 55), (fx, h - 55, 32, 32), 1, border_radius=2)
            fx += 38

        # ============================================================
        # === ZOOMABLE CANVAS WITH CURSOR-CENTERED ZOOM ===
        # ============================================================

        # Working area rect (used for zoom anchoring and layout)
        work_left = tools_width + 8
        work_right = w - layers_width - 8
        work_top = top_height + 8
        work_bottom = h - timeline_height - 8

        work_w = work_right - work_left
        work_h = work_bottom - work_top

        # Initialize canvas centered on first draw
        if not self._canvas_initialized:
            canvas_pixel_w = self.logical_width * self.zoom
            canvas_pixel_h = self.logical_height * self.zoom
            self.canvas_x = work_left + (work_w - canvas_pixel_w) // 2
            self.canvas_y = work_top + (work_h - canvas_pixel_h) // 2
            self._canvas_initialized = True

        cx, cy = self.canvas_x, self.canvas_y
        cw = self.logical_width * self.zoom
        ch = self.logical_height * self.zoom

        # Canvas background
        pygame.draw.rect(self.screen, self.config.canvas_bg, (cx, cy, cw, ch))
        pygame.draw.rect(self.screen, (90, 90, 95), (cx - 1, cy - 1, cw + 2, ch + 2), 2)

        # Label above the canvas
        clabel = font_normal.render(f"Canvas ({self.logical_width}×{self.logical_height})", True, text_col)
        self.screen.blit(clabel, (cx, cy - 20))

        # Draw scaled grid (one line per logical pixel)
        if self.config.show_grid and self.zoom >= 2:
            grid_color = self.config.grid_color
            for gx in range(self.logical_width + 1):
                x = cx + gx * self.zoom
                pygame.draw.line(self.screen, grid_color, (x, cy), (x, cy + ch))
            for gy in range(self.logical_height + 1):
                y = cy + gy * self.zoom
                pygame.draw.line(self.screen, grid_color, (cx, y), (cx + cw, y))

        # Draw a very simple placeholder "sprite" scaled by zoom
        sprite_screen_x = cx + 4 * self.zoom
        sprite_screen_y = cy + 4 * self.zoom
        sprite_screen_w = 24 * self.zoom
        sprite_screen_h = 24 * self.zoom

        pygame.draw.rect(
            self.screen,
            (255, 180, 80),
            (sprite_screen_x, sprite_screen_y, sprite_screen_w, sprite_screen_h),
            2
        )

        # Instructions
        hint_font = pygame.font.SysFont("Arial", 11)
        hint = hint_font.render("Ctrl+Scroll or + / - to zoom  |  Cursor-centered when mouse in working area", True, (150, 150, 155))
        self.screen.blit(hint, (cx, cy + ch + 6))

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
