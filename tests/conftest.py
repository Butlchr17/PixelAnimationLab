"""
tests/conftest.py

Shared pytest fixtures for PixelAnimationLab tests.

Fixtures defined here are automatically available to all test modules
without explicit imports.
"""

import pytest

from core.sprite import Sprite
from core.frame import Frame
from core.layer import Layer


@pytest.fixture
def small_sprite():
    """A small, empty Sprite useful for most unit tests."""
    return Sprite(8, 8, name="TestSprite")


@pytest.fixture
def sprite_with_content():
    """A Sprite with multiple frames and layers containing some pixel data."""
    s = Sprite(8, 8, name="ContentSprite")
    s.add_layer("Character")
    s.add_frame()
    s.current_frame_idx = 1
    s.current_frame.layers[1].set_pixel(4, 4, (255, 255, 0, 255))
    return s


@pytest.fixture
def empty_frame():
    """A minimal empty Frame."""
    return Frame(8, 8)


@pytest.fixture
def sample_layer():
    """A small Layer with one pixel painted."""
    layer = Layer(4, 4, name="Sample")
    layer.set_pixel(1, 1, (255, 128, 64, 255))
    return layer
