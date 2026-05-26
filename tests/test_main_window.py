"""
tests/test_main_window.py

Tests for the UI logic in MainWindow.

Because MainWindow is a pygame-based class, we focus on testing the
**pure, testable logic** rather than the rendering loop itself:

- Zoom level selection (`_get_next_zoom_level`)
- Working area rectangle calculation (`_get_working_rect`)
- Basic state initialization
- Zoom application behavior (at a high level)

Full integration tests involving an actual pygame display are difficult
in a headless environment and are left for manual testing for now.
"""

import pygame
import pytest

from ui.main_window import MainWindow
from utils.config import Config


@pytest.fixture
def window():
    """Create a MainWindow without calling init() so we can test logic safely."""
    cfg = Config(width=1280, height=800)
    win = MainWindow(cfg)
    return win


class TestMainWindowInitialization:
    """Basic state checks on construction."""

    def test_initial_state(self, window):
        assert window.zoom == 8
        assert window.logical_width == 32
        assert window.logical_height == 32
        assert window.canvas_x == 0
        assert window.canvas_y == 0
        assert isinstance(window.mouse_pos, tuple)
        assert window._canvas_initialized is False

    def test_zoom_levels_list_is_reasonable(self, window):
        levels = window.ZOOM_LEVELS
        assert 1 in levels
        assert 64 in levels
        assert levels == sorted(levels)  # must be ascending


class TestZoomLevelSelection:
    """Tests for the smooth zoom stepping logic."""

    def test_zoom_in_from_common_values(self, window):
        # 8 → 12
        assert window._get_next_zoom_level(8, direction=1) == 12
        # 12 → 16
        assert window._get_next_zoom_level(12, direction=1) == 16
        # 32 → 48
        assert window._get_next_zoom_level(32, direction=1) == 48

    def test_zoom_out_from_common_values(self, window):
        assert window._get_next_zoom_level(8, direction=-1) == 6
        assert window._get_next_zoom_level(16, direction=-1) == 12
        assert window._get_next_zoom_level(4, direction=-1) == 3

    def test_zoom_in_at_max_stays_at_max(self, window):
        assert window._get_next_zoom_level(64, direction=1) == 64

    def test_zoom_out_at_min_stays_at_min(self, window):
        assert window._get_next_zoom_level(1, direction=-1) == 1

    def test_zoom_in_from_value_between_levels(self, window):
        # Should jump to the next defined step
        assert window._get_next_zoom_level(5, direction=1) == 6
        assert window._get_next_zoom_level(9, direction=1) == 12


class TestWorkingRect:
    """Tests for the working area rectangle used by layout and zoom anchoring."""

    def test_working_rect_is_smaller_than_window(self, window):
        rect = window._get_working_rect()
        assert rect.width > 0
        assert rect.height > 0
        assert rect.width < window.config.width
        assert rect.height < window.config.height

    def test_working_rect_position_accounts_for_panels(self, window):
        rect = window._get_working_rect()
        # Should start after left tools panel + margin
        assert rect.left >= 48 + 8
        # Should end before right layers panel + margin
        assert rect.right <= window.config.width - 180 - 8


class TestZoomApplication:
    """High-level tests for the zoom machinery (without requiring display)."""

    def test_zoom_changes_zoom_level(self, window):
        old_zoom = window.zoom
        window.zoom_in()
        assert window.zoom > old_zoom

        window.zoom_out()
        window.zoom_out()
        assert window.zoom < old_zoom

    def test_zoom_does_not_exceed_defined_levels(self, window):
        for _ in range(20):
            window.zoom_in()
        assert window.zoom <= 64

        for _ in range(30):
            window.zoom_out()
        assert window.zoom >= 1
