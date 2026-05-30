"""
ui/canvas.py

The main drawing surface for PixelAnimationLab.

This class is responsible for:
- Displaying pixel data from a Layer (and later Frame/Sprite)
- Handling zoom and pan
- Converting between screen coordinates and logical pixel coordinates
- Drawing the pixel grid at appropriate zoom levels

It is designed to be embedded inside MainWindow (or a future Panel system).
It does **not** own the Layer — it receives a reference to one.

Current limitations (will be addressed in later steps):
- Only displays a single Layer for now
- No drawing tools yet (see ui-step4)
- No onion skinning, selection, or guides yet
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pygame

from core.layer import Layer


class Canvas:
    """
    Zoomable and pannable view of a Layer's pixel data.
    """

    # Smooth zoom steps for pixel art (much nicer than pure doubling)
    ZOOM_LEVELS: list[int] = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64]

    # Reasonable zoom range for pixel art work
    MIN_ZOOM = 1
    MAX_ZOOM = 64

    def __init__(
        self,
        logical_width: int,
        logical_height: int,
        layer: Optional[Layer] = None,
    ):
        self.logical_width = logical_width
        self.logical_height = logical_height

        self.zoom: int = 8
        self.offset_x: int = 0   # Screen x position of logical (0,0)
        self.offset_y: int = 0   # Screen y position of logical (0,0)

        self.layer: Optional[Layer] = None

        # Internal dragging state for panning (right mouse button only)
        self._dragging: bool = False
        self._last_mouse: Tuple[int, int] = (0, 0)

        # For centering on first valid viewport
        self._has_been_centered: bool = False
        self.viewport_rect: Optional[pygame.Rect] = None

        if layer is not None:
            self.set_layer(layer)

    def set_layer(self, layer: Layer) -> None:
        """Attach a Layer to be displayed. The canvas does not own the layer."""
        self.layer = layer
        # Optional: auto-fit or keep current zoom/offset
        # For now we keep whatever zoom/offset the user has.

    # ------------------------------------------------------------------
    # Coordinate Conversion (critical for tools later)
    # ------------------------------------------------------------------

    def screen_to_pixel(self, sx: int, sy: int) -> Optional[Tuple[int, int]]:
        """
        Convert screen coordinates to logical pixel coordinates.
        Returns None if the point is outside the logical canvas.
        """
        if self.layer is None:
            return None

        px = (sx - self.offset_x) // self.zoom
        py = (sy - self.offset_y) // self.zoom

        if 0 <= px < self.logical_width and 0 <= py < self.logical_height:
            return (px, py)
        return None

    def pixel_to_screen(self, px: int, py: int) -> Tuple[int, int]:
        """Convert logical pixel coordinates to screen coordinates (top-left of the pixel)."""
        sx = self.offset_x + px * self.zoom
        sy = self.offset_y + py * self.zoom
        return (sx, sy)

    # ------------------------------------------------------------------
    # Centering and Constraints
    # ------------------------------------------------------------------

    def center_in_rect(self, rect: pygame.Rect) -> None:
        """Center the canvas inside the given rectangle (usually the working area)."""
        if rect.width <= 0 or rect.height <= 0:
            return

        canvas_w = self.logical_width * self.zoom
        canvas_h = self.logical_height * self.zoom

        self.offset_x = rect.centerx - canvas_w // 2
        self.offset_y = rect.centery - canvas_h // 2
        self._has_been_centered = True
        self._clamp_offset(rect)

    def _clamp_offset(self, viewport: pygame.Rect) -> None:
        """Prevent the canvas from being dragged completely outside the working area.
        Allows the image to be panned until its edges reach the opposite side of the viewport.
        """
        if not viewport or viewport.width <= 0 or viewport.height <= 0:
            return

        canvas_w = self.logical_width * self.zoom
        canvas_h = self.logical_height * self.zoom

        # Horizontal clamping
        if canvas_w <= viewport.width:
            # Small canvas: keep it centered
            self.offset_x = viewport.centerx - canvas_w // 2
        else:
            # Large canvas: allow panning until the far edge touches the viewport edge
            self.offset_x = max(viewport.right - canvas_w, min(self.offset_x, viewport.left))

        # Vertical clamping
        if canvas_h <= viewport.height:
            self.offset_y = viewport.centery - canvas_h // 2
        else:
            self.offset_y = max(viewport.bottom - canvas_h, min(self.offset_y, viewport.top))

    # ------------------------------------------------------------------
    # Zoom & Pan
    # ------------------------------------------------------------------

    def zoom_in(self, around: Optional[Tuple[int, int]] = None) -> None:
        """Zoom in using smooth ZOOM_LEVELS, optionally centered on a screen point."""
        new_zoom = self._get_next_zoom_level(self.zoom, direction=1)
        self._zoom_to_level(new_zoom, around)

    def zoom_out(self, around: Optional[Tuple[int, int]] = None) -> None:
        """Zoom out using smooth ZOOM_LEVELS, optionally centered on a screen point."""
        new_zoom = self._get_next_zoom_level(self.zoom, direction=-1)
        self._zoom_to_level(new_zoom, around)

    def _get_next_zoom_level(self, current: int, direction: int) -> int:
        """Return next zoom from ZOOM_LEVELS list (direction 1 = in, -1 = out)."""
        levels = self.ZOOM_LEVELS
        if direction > 0:
            for level in levels:
                if level > current:
                    return level
            return levels[-1]
        else:
            for level in reversed(levels):
                if level < current:
                    return level
            return levels[0]

    def _zoom_to_level(self, new_zoom: int, around: Optional[Tuple[int, int]]) -> None:
        """Internal helper that performs smooth cursor-centered zooming."""
        new_zoom = max(self.MIN_ZOOM, min(new_zoom, self.MAX_ZOOM))
        if new_zoom == self.zoom:
            return

        if around is None:
            # Zoom toward center of the canvas if no point given
            anchor_x = self.offset_x + (self.logical_width * self.zoom) // 2
            anchor_y = self.offset_y + (self.logical_height * self.zoom) // 2
        else:
            anchor_x, anchor_y = around

        # Convert screen point to logical pixel space before zoom
        logical_x = (anchor_x - self.offset_x) / self.zoom
        logical_y = (anchor_y - self.offset_y) / self.zoom

        self.zoom = new_zoom

        # Reposition so the logical point stays under the anchor
        self.offset_x = int(anchor_x - logical_x * self.zoom)
        self.offset_y = int(anchor_y - logical_y * self.zoom)

        if self.viewport_rect:
            self._clamp_offset(self.viewport_rect)

    def start_pan(self, mouse_pos: Tuple[int, int]) -> None:
        """Begin a pan/drag operation."""
        self._dragging = True
        self._last_mouse = mouse_pos

    def update_pan(self, mouse_pos: Tuple[int, int]) -> None:
        """Continue panning based on mouse movement."""
        if not self._dragging:
            return

        dx = mouse_pos[0] - self._last_mouse[0]
        dy = mouse_pos[1] - self._last_mouse[1]

        self.offset_x += dx
        self.offset_y += dy

        self._last_mouse = mouse_pos

        if self.viewport_rect:
            self._clamp_offset(self.viewport_rect)

    def end_pan(self) -> None:
        """End the current pan operation."""
        self._dragging = False

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, dest_rect: pygame.Rect) -> None:
        """
        Draw the canvas content into the given destination rectangle on `surface`.

        The dest_rect is treated as the "working area" / viewport for:
        - Initial centering on spawn
        - Clamping so the canvas cannot be dragged completely outside
        - Clipping so zoomed content doesn't draw outside the working area
        """
        self.viewport_rect = dest_rect

        # Center on first valid draw (when we finally know the working area size)
        if not self._has_been_centered and dest_rect.width > 0 and dest_rect.height > 0:
            self.center_in_rect(dest_rect)

        # Background for the working area
        pygame.draw.rect(surface, (25, 25, 28), dest_rect, border_radius=2)

        if self.layer is None:
            font = pygame.font.SysFont("Arial", 14)
            text = font.render("No layer attached", True, (180, 180, 185))
            surface.blit(text, (dest_rect.centerx - 60, dest_rect.centery - 8))
            return

        # === CLIP all further drawing to the working area ===
        previous_clip = surface.get_clip()
        surface.set_clip(dest_rect)

        # Draw the actual pixel data (will be clipped)
        self._draw_pixels(surface)

        # Draw grid when zoomed in enough (clipped)
        if self.zoom >= 4:
            self._draw_grid(surface)

        # Restore clip
        surface.set_clip(previous_clip)

        # Draw border around the logical canvas (we still want to see the border even if slightly outside)
        # But to be strict, we can also clip the border or draw it after.
        canvas_rect = pygame.Rect(
            self.offset_x,
            self.offset_y,
            self.logical_width * self.zoom,
            self.logical_height * self.zoom,
        )
        pygame.draw.rect(surface, (110, 110, 115), canvas_rect, 2)

    def _draw_pixels(self, surface: pygame.Surface) -> None:
        """Render the layer's pixels, scaled by current zoom."""
        if self.layer is None:
            return

        # Create a small pygame surface from the layer data
        # Layer pixels are (H, W, 4) uint8 RGBA
        arr = self.layer.pixels  # numpy array

        # Pygame expects (W, H, 3) or (W, H, 4) for surfarray, but we'll use frombuffer for simplicity
        # Convert RGBA to a format pygame likes
        if arr.shape[2] == 4:
            # Already RGBA
            pixel_data = arr.tobytes()
            small_surf = pygame.image.frombuffer(
                pixel_data, (self.logical_width, self.logical_height), "RGBA"
            )
        else:
            # RGB -> add alpha
            rgba = np.zeros((self.logical_height, self.logical_width, 4), dtype=np.uint8)
            rgba[:, :, :3] = arr
            rgba[:, :, 3] = 255
            pixel_data = rgba.tobytes()
            small_surf = pygame.image.frombuffer(
                pixel_data, (self.logical_width, self.logical_height), "RGBA"
            )

        # Scale to current zoom level using nearest neighbor (important for pixel art)
        scaled_size = (
            self.logical_width * self.zoom,
            self.logical_height * self.zoom,
        )
        scaled_surf = pygame.transform.scale(small_surf, scaled_size)

        # Blit at the current offset
        surface.blit(scaled_surf, (self.offset_x, self.offset_y))

    def _draw_grid(self, surface: pygame.Surface) -> None:
        """Draw a 1-pixel grid at the current zoom level."""
        color = (70, 70, 75)
        w = self.logical_width * self.zoom
        h = self.logical_height * self.zoom

        # Vertical lines
        for x in range(self.logical_width + 1):
            sx = self.offset_x + x * self.zoom
            pygame.draw.line(surface, color, (sx, self.offset_y), (sx, self.offset_y + h))

        # Horizontal lines
        for y in range(self.logical_height + 1):
            sy = self.offset_y + y * self.zoom
            pygame.draw.line(surface, color, (self.offset_x, sy), (self.offset_x + w, sy))

    # ------------------------------------------------------------------
    # Event Handling (basic panning for now)
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle input events that affect the canvas (pan, zoom, etc.).

        Returns True if the event was consumed.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 3:  # Right mouse button only for panning
                self.start_pan(event.pos)
                return True

            elif event.button in (4, 5):  # Mouse wheel
                # Only zoom on completely pure wheel scrolls (no mouse buttons and no keyboard keys held).
                # This frees up combinations like Ctrl+Wheel, Shift+Wheel, Alt+Wheel, etc. for tools
                # (e.g. brush size scaling, tool options, etc.).
                mouse_pressed = pygame.mouse.get_pressed()
                key_pressed = pygame.key.get_pressed()

                if any(mouse_pressed[:3]) or any(key_pressed):
                    return False  # do not consume the event for zoom

                if event.button == 4:
                    self.zoom_in(around=event.pos)
                else:
                    self.zoom_out(around=event.pos)
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 3:  # Right mouse button
                self.end_pan()
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self._dragging:
                self.update_pan(event.pos)
                return True

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                self.zoom_in(around=pygame.mouse.get_pos())
                return True
            elif event.key == pygame.K_MINUS:
                self.zoom_out(around=pygame.mouse.get_pos())
                return True

        return False

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_zoom(self) -> int:
        return self.zoom

    def __repr__(self) -> str:
        return (
            f"Canvas(zoom={self.zoom}x, "
            f"offset=({self.offset_x}, {self.offset_y}), "
            f"size={self.logical_width}x{self.logical_height})"
        )
