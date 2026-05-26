"""
core/palette.py - Color palette management for PixelAnimationLab.

A Palette holds a list of colors used by the sprite. This enables:
- Consistent color usage across frames and layers
- Easy color remapping
- Exporting with limited palettes (useful for retro formats)

This is a minimal but functional implementation focused on the needs of Sprite.
It can be extended later with features like:
- Named colors / swatches
- Multiple palettes per sprite
- Palette cycling / animation
- Import from .gpl, .act, image files, etc.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


Color = Tuple[int, int, int, int]  # RGBA


class Palette:
    """
    A collection of colors used throughout a sprite.

    Colors are stored as (r, g, b, a) tuples with values 0-255.
    The first color (index 0) is conventionally treated as the transparent
    or background color in many pixel art workflows.
    """

    def __init__(self, colors: Optional[List[Color]] = None, name: str = "Default"):
        self.name = name
        self.colors: List[Color] = list(colors) if colors else [
            (0, 0, 0, 0),      # Transparent / background
            (255, 255, 255, 255),  # White
            (0, 0, 0, 255),        # Black
            (255, 0, 0, 255),      # Red
            (0, 255, 0, 255),      # Green
            (0, 0, 255, 255),      # Blue
        ]

    def add_color(self, color: Color, index: Optional[int] = None) -> int:
        """Add a color to the palette. Returns the index it was inserted at."""
        if index is None:
            self.colors.append(color)
            return len(self.colors) - 1
        index = max(0, min(index, len(self.colors)))
        self.colors.insert(index, color)
        return index

    def remove_color(self, index: int) -> Optional[Color]:
        """Remove and return the color at the given index."""
        if 0 <= index < len(self.colors) and len(self.colors) > 1:
            return self.colors.pop(index)
        return None

    def get_color(self, index: int) -> Optional[Color]:
        """Return the color at index, or None if out of range."""
        if 0 <= index < len(self.colors):
            return self.colors[index]
        return None

    def find_color(self, color: Color) -> int:
        """Return the index of the color, or -1 if not present."""
        try:
            return self.colors.index(color)
        except ValueError:
            return -1

    def replace_color(self, index: int, new_color: Color) -> bool:
        """Replace the color at the given index."""
        if 0 <= index < len(self.colors):
            self.colors[index] = new_color
            return True
        return False

    def __len__(self) -> int:
        return len(self.colors)

    def __getitem__(self, index: int) -> Color:
        return self.colors[index]

    def __iter__(self):
        return iter(self.colors)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the palette for saving."""
        return {
            "version": "1.0",
            "name": self.name,
            "colors": [list(c) for c in self.colors],  # lists are JSON-safe
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Palette":
        """Reconstruct a Palette from serialized data."""
        colors = [tuple(c) for c in data.get("colors", [])]
        palette = cls(colors=colors if colors else None,
                      name=data.get("name", "Default"))
        return palette

    def __repr__(self) -> str:
        return f"Palette(name={self.name!r}, colors={len(self.colors)})"
