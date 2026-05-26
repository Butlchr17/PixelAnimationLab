"""
utils/config.py

Central configuration for PixelAnimationLab.

This module holds window settings, UI constants, colors, and other
application-wide configuration. Keeping configuration in one place makes
it easier to support themes, user preferences, and command-line overrides
in the future.
"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class Config:
    """Application configuration and constants."""

    # Window settings
    width: int = 1280
    height: int = 800
    title: str = "PixelAnimationLab"
    fps: int = 60

    # UI scaling / pixel art friendliness
    ui_scale: float = 1.0
    default_zoom: int = 8          # Initial zoom level on the canvas

    # Colors (RGB tuples) - basic dark theme starting point
    bg_color: Tuple[int, int, int] = (30, 30, 35)
    panel_bg: Tuple[int, int, int] = (45, 45, 50)
    accent_color: Tuple[int, int, int] = (70, 130, 180)
    text_color: Tuple[int, int, int] = (230, 230, 235)
    grid_color: Tuple[int, int, int] = (60, 60, 65)

    # Canvas settings
    canvas_bg: Tuple[int, int, int] = (20, 20, 22)

    # Feature flags (easy to toggle during development)
    show_grid: bool = True
    show_layer_bounds: bool = False

    # Paths (can be expanded later)
    assets_dir: str = "assets"
    projects_dir: str = "projects"

    # Internal
    _version: str = "0.1.0"


# Default global config instance (can be replaced at startup if needed)
DEFAULT_CONFIG = Config()
