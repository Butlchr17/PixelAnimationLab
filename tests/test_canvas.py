"""
tests/test_canvas.py

Comprehensive tests for the Canvas class (ui-step2).

The Canvas is the core visual component responsible for displaying Layer
pixel data with zoom, pan, and proper coordinate mapping.

These tests focus on the pure logic that can be tested without a real
display (zoom math, clamping, coordinate conversion, panning state, etc.).
Rendering and pygame surface interactions are tested lightly or via
integration in manual runs.
"""

import pygame
import pytest

from ui.canvas import Canvas
from core.layer import Layer


@pytest.fixture
def small_layer():
    """A small 8x8 layer with some visible pixels for testing."""
    layer = Layer(8, 8, name="Test Layer")
    layer.set_pixel(0, 0, (255, 0, 0, 255))
    layer.set_pixel(7, 7, (0, 255, 0, 255))
    return layer


@pytest.fixture
def canvas_with_layer(small_layer):
    """A Canvas initialized with a small layer at a known zoom."""
    c = Canvas(8, 8, layer=small_layer)
    c.zoom = 4  # 32x32 on screen
    return c


class TestCanvasInitialization:
    """Basic construction and state."""

    def test_default_state(self, small_layer):
        c = Canvas(16, 16, layer=small_layer)
        assert c.logical_width == 16
        assert c.logical_height == 16
        assert c.zoom == 8
        assert c.offset_x == 0
        assert c.offset_y == 0
        assert c.layer is small_layer
        assert c._has_been_centered is False

    def test_set_layer(self, small_layer):
        c = Canvas(8, 8)
        c.set_layer(small_layer)
        assert c.layer is small_layer


class TestZoomBehavior:
    """Zoom level selection and cursor-centered zooming."""

    def test_zoom_in_out_respects_limits(self, canvas_with_layer):
        c = canvas_with_layer
        c.zoom = 1
        c.zoom_out()  # should stay at 1
        assert c.zoom == 1

        c.zoom = 64
        c.zoom_in()  # should stay at 64
        assert c.zoom == 64

    def test_smooth_zoom_steps(self, canvas_with_layer):
        c = canvas_with_layer
        c.zoom = 8
        c.zoom_in()
        assert c.zoom == 12
        c.zoom_in()
        assert c.zoom == 16
        c.zoom_out()
        assert c.zoom == 12

    def test_cursor_centered_zoom_adjusts_offset(self, canvas_with_layer):
        """Zooming around a point should keep that screen point stable."""
        c = canvas_with_layer
        c.zoom = 4
        c.offset_x = 100
        c.offset_y = 100

        # Simulate zooming around screen point (120, 120)
        anchor = (120, 120)
        old_logical_x = (120 - c.offset_x) / c.zoom
        old_logical_y = (120 - c.offset_y) / c.zoom

        c.zoom_in(around=anchor)

        # The same logical point should now be under the same screen point
        new_screen_x = c.offset_x + old_logical_x * c.zoom
        new_screen_y = c.offset_y + old_logical_y * c.zoom

        assert abs(new_screen_x - 120) < 1
        assert abs(new_screen_y - 120) < 1


class TestPanning:
    """Right-mouse-button panning behavior."""

    def test_right_click_starts_pan(self, canvas_with_layer):
        c = canvas_with_layer
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 3, "pos": (150, 150)})
        consumed = c.handle_event(event)
        assert consumed is True
        assert c._dragging is True

    def test_mouse_motion_while_dragging_pans(self, canvas_with_layer):
        c = canvas_with_layer
        c.offset_x = 100
        c.offset_y = 100

        # Start drag
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 3, "pos": (150, 150)})
        c.handle_event(down)

        # Move
        move = pygame.event.Event(pygame.MOUSEMOTION, {"pos": (170, 160)})
        consumed = c.handle_event(move)
        assert consumed is True

        # Should have moved by (20, 10)
        assert c.offset_x == 120
        assert c.offset_y == 110

    def test_right_click_release_ends_pan(self, canvas_with_layer):
        c = canvas_with_layer
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 3, "pos": (100, 100)})
        c.handle_event(down)

        up = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 3, "pos": (100, 100)})
        consumed = c.handle_event(up)
        assert consumed is True
        assert c._dragging is False


class TestCenteringAndConstraints:
    """Initial centering and boundary clamping."""

    def test_initial_center_in_rect(self, canvas_with_layer):
        c = Canvas(8, 8, layer=Layer(8, 8))  # fresh canvas
        c.zoom = 4
        viewport = pygame.Rect(100, 50, 400, 300)

        c.center_in_rect(viewport)

        expected_x = viewport.centerx - (8 * 4) // 2
        expected_y = viewport.centery - (8 * 4) // 2

        assert c.offset_x == expected_x
        assert c.offset_y == expected_y
        assert c._has_been_centered is True

    def test_clamp_prevents_canvas_from_leaving_viewport(self, canvas_with_layer):
        c = canvas_with_layer
        c.zoom = 4  # 32x32 on screen
        viewport = pygame.Rect(0, 0, 200, 200)

        # Try to drag it way off to the left
        c.offset_x = -1000
        c._clamp_offset(viewport)

        # Should be clamped so right edge of canvas touches left edge of viewport at worst
        min_allowed = viewport.left - (8 * 4)   # allow touching the edge
        assert c.offset_x >= min_allowed

    def test_small_canvas_stays_centered_when_not_dragging(self, canvas_with_layer):
        c = Canvas(8, 8)
        c.zoom = 2  # very small (16x16)
        viewport = pygame.Rect(0, 0, 300, 300)

        c.offset_x = 50  # move it away
        c._clamp_offset(viewport)

        expected = viewport.centerx - (8 * 2) // 2
        assert c.offset_x == expected


class TestCoordinateConversion:
    """screen <-> pixel conversion (critical for future tools)."""

    def test_screen_to_pixel_basic(self, canvas_with_layer):
        c = canvas_with_layer
        c.zoom = 4
        c.offset_x = 100
        c.offset_y = 50

        # Pixel (0,0) should be at screen (100, 50)
        assert c.screen_to_pixel(100, 50) == (0, 0)
        assert c.screen_to_pixel(103, 53) == (0, 0)  # still inside first pixel

        # Pixel (1,1)
        assert c.screen_to_pixel(104, 54) == (1, 1)

    def test_pixel_to_screen(self, canvas_with_layer):
        c = canvas_with_layer
        c.zoom = 4
        c.offset_x = 100
        c.offset_y = 50

        assert c.pixel_to_screen(0, 0) == (100, 50)
        assert c.pixel_to_screen(3, 3) == (112, 62)

    def test_screen_to_pixel_outside_canvas_returns_none(self, canvas_with_layer):
        c = canvas_with_layer
        c.offset_x = 0
        c.offset_y = 0
        c.zoom = 1

        assert c.screen_to_pixel(-1, 0) is None
        assert c.screen_to_pixel(8, 0) is None  # exactly on the edge is outside


class TestIntegrationWithLayer:
    """Light integration tests with real Layer data."""

    def test_canvas_renders_without_crashing(self, small_layer):
        """Basic smoke test that draw() doesn't explode (no display needed for logic)."""
        c = Canvas(8, 8, layer=small_layer)
        c.zoom = 2
        # We can't easily assert pixels without a real surface + display,
        # but we can at least exercise the drawing path.
        dummy_surface = pygame.Surface((400, 400))
        dummy_rect = pygame.Rect(0, 0, 300, 300)
        c.draw(dummy_surface, dummy_rect)  # should not raise
