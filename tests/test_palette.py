"""
tests/test_palette.py

Tests for the Palette class.

Palettes are used for consistent color selection across the entire sprite.
These tests verify basic CRUD operations and the serialization contract.
"""

import pytest

from core.palette import Palette


class TestPaletteBasics:
    def test_default_palette_has_colors(self):
        p = Palette()
        assert len(p) >= 1
        assert p[0] == (0, 0, 0, 0)  # transparent first

    def test_add_and_find_color(self):
        p = Palette()
        idx = p.add_color((255, 128, 0, 255))
        assert p.find_color((255, 128, 0, 255)) == idx

    def test_remove_color_protects_last_one(self):
        p = Palette(colors=[(255, 0, 0, 255)])
        assert p.remove_color(0) is None  # should not allow emptying palette

    def test_replace_color(self):
        p = Palette()
        p.replace_color(1, (10, 20, 30, 255))
        assert p[1] == (10, 20, 30, 255)


class TestPaletteSerialization:
    def test_roundtrip(self):
        p = Palette(name="GamePalette")
        p.add_color((100, 100, 100, 255))
        data = p.to_dict()
        restored = Palette.from_dict(data)
        assert restored.name == "GamePalette"
        assert len(restored) == len(p)
        assert restored.find_color((100, 100, 100, 255)) != -1
