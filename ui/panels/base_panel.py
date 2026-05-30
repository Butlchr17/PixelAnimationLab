"""
ui/panels/base_panel.py

Base class for all UI panels in PixelAnimationLab.

A Panel is a rectangular region that:
- Draws itself inside a given rect
- Can handle mouse and keyboard events
- Can be laid out by the MainWindow or a future layout system

This is intentionally lightweight. It is **not** a full retained-mode GUI framework.
The goal is to have clean, reusable pieces without over-engineering early.
"""

from __future__ import annotations

from typing import Optional

import pygame


class Panel:
    """
    Base class for UI panels (Tools, Layers, Timeline, Color Palette, etc.).
    """

    def __init__(self, name: str = "Panel"):
        self.name = name
        self.rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)  # Set by parent during layout
        self.visible: bool = True
        self.enabled: bool = True

        # Optional: background color override
        self.bg_color: Optional[tuple[int, int, int]] = None

    def set_rect(self, rect: pygame.Rect) -> None:
        """Called by the parent layout system to position the panel."""
        self.rect = rect

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle a pygame event.

        Return True if the event was consumed by this panel (so other panels
        or the canvas should ignore it).
        """
        return False

    def update(self, dt: float) -> None:
        """Per-frame update logic (hover states, animations, etc.)."""
        pass

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the panel into its rect."""
        if not self.visible:
            return

        # Default background
        bg = self.bg_color or (45, 45, 50)
        pygame.draw.rect(surface, bg, self.rect)
        pygame.draw.rect(surface, (70, 70, 75), self.rect, 1)

        # Default title (can be overridden)
        font = pygame.font.SysFont("Arial", 14)
        title = font.render(self.name, True, (230, 230, 235))
        surface.blit(title, (self.rect.x + 8, self.rect.y + 6))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, rect={self.rect})"
