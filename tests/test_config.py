"""
tests/test_config.py

Tests for the Config dataclass in utils/config.py.

The Config class centralizes all application settings (window size, colors,
zoom defaults, feature flags, etc.). These tests ensure that defaults are
sensible and that the class behaves as a normal dataclass.
"""

import pytest

from utils.config import Config, DEFAULT_CONFIG


class TestConfigDefaults:
    """Verify that default values are reasonable for a pixel art editor."""

    def test_default_window_settings(self):
        cfg = Config()
        assert cfg.width > 800
        assert cfg.height > 600
        assert cfg.title == "PixelAnimationLab"
        assert cfg.fps == 60

    def test_default_zoom_is_pixel_art_friendly(self):
        cfg = Config()
        assert cfg.default_zoom == 8
        assert cfg.ui_scale == 1.0

    def test_color_values_are_valid_rgb(self):
        cfg = Config()
        for color in (cfg.bg_color, cfg.panel_bg, cfg.accent_color,
                      cfg.text_color, cfg.grid_color, cfg.canvas_bg):
            assert len(color) == 3
            assert all(0 <= c <= 255 for c in color)

    def test_feature_flags_have_sensible_defaults(self):
        cfg = Config()
        assert isinstance(cfg.show_grid, bool)
        assert isinstance(cfg.show_layer_bounds, bool)


class TestConfigCustomization:
    """Ensure users can override values at construction time."""

    def test_custom_initialization(self):
        cfg = Config(width=800, height=600, default_zoom=4, title="My Editor")
        assert cfg.width == 800
        assert cfg.height == 600
        assert cfg.default_zoom == 4
        assert cfg.title == "My Editor"

    def test_default_global_instance_exists(self):
        assert isinstance(DEFAULT_CONFIG, Config)
        assert DEFAULT_CONFIG.width >= 800
