"""
tests/test_layer.py

Comprehensive tests for the Layer class.

The Layer is the fundamental raster unit in PixelAnimationLab. These tests
verify that all core operations (construction, pixel manipulation, duplication
semantics, resizing, and serialization) behave correctly.

Why these tests matter:
- Layer is used by every higher-level object (Frame, Sprite).
- `copy_empty()` is critical for the animation workflow (new frames must
  share layer structure but start with transparent pixels).
- Serialization must be lossless for the .pxf save format to be reliable.
"""

import numpy as np
import pytest

from core.layer import Layer, create_filled_layer


class TestLayerConstruction:
    """Tests for Layer initialization and basic properties."""

    def test_default_construction(self):
        """A default Layer should be 1x1 RGBA and fully transparent."""
        layer = Layer(8, 8)
        assert layer.width == 8
        assert layer.height == 8
        assert layer.color_mode == "RGBA"
        assert layer.channels == 4
        assert layer.shape == (8, 8, 4)
        assert np.all(layer.pixels == 0)
        assert layer.name == "Layer"

    def test_custom_name_and_properties(self):
        """Layer should accept custom name, visibility, and opacity."""
        layer = Layer(
            16, 16,
            name="Character",
            visible=False,
            opacity=0.75,
            locked=True,
            blend_mode="normal"
        )
        assert layer.name == "Character"
        assert layer.visible is False
        assert layer.opacity == 0.75
        assert layer.locked is True

    def test_rgb_color_mode(self):
        """RGB mode should produce 3-channel arrays."""
        layer = Layer(4, 4, color_mode="RGB")
        assert layer.color_mode == "RGB"
        assert layer.channels == 3
        assert layer.shape == (4, 4, 3)

    def test_invalid_dimensions_raises(self):
        """Negative or zero dimensions must be rejected."""
        with pytest.raises(ValueError):
            Layer(0, 10)
        with pytest.raises(ValueError):
            Layer(-5, 10)


class TestPixelAccess:
    """Tests for get_pixel and set_pixel."""

    def test_set_and_get_pixel(self):
        layer = Layer(4, 4)
        layer.set_pixel(1, 2, (255, 128, 64, 255))
        assert layer.get_pixel(1, 2) == (255, 128, 64, 255)

    def test_out_of_bounds_raises(self):
        layer = Layer(4, 4)
        with pytest.raises(IndexError):
            layer.get_pixel(10, 0)
        with pytest.raises(IndexError):
            layer.set_pixel(0, 10, (0, 0, 0, 0))

    def test_wrong_channel_count_raises(self):
        layer = Layer(4, 4, color_mode="RGBA")
        with pytest.raises(ValueError):
            layer.set_pixel(0, 0, (255, 0, 0))  # only 3 values


class TestDuplicationSemantics:
    """
    Tests for the two critical duplication methods.

    These are the most important behaviors for animation:
    - copy_empty() → same metadata, transparent pixels (used for new frames)
    - copy()       → full independent duplicate including pixels
    """

    def test_copy_empty_preserves_metadata_but_clears_pixels(self):
        layer = Layer(8, 8, name="Effects", visible=True, opacity=0.5)
        layer.set_pixel(3, 3, (255, 0, 0, 255))

        empty = layer.copy_empty()

        assert empty.name == "Effects"
        assert empty.visible is True
        assert empty.opacity == 0.5
        assert np.all(empty.pixels == 0)
        assert np.any(layer.pixels != 0)  # original unchanged

    def test_copy_is_deep_and_independent(self):
        layer = Layer(4, 4)
        layer.set_pixel(0, 0, (100, 100, 100, 255))

        clone = layer.copy()
        clone.set_pixel(0, 0, (200, 200, 200, 255))

        # Original must be unaffected
        assert layer.get_pixel(0, 0) == (100, 100, 100, 255)
        assert clone.get_pixel(0, 0) == (200, 200, 200, 255)


class TestEditingOperations:
    """Tests for bulk editing methods."""

    def test_clear_and_fill(self):
        layer = Layer(4, 4)
        layer.fill((40, 40, 40, 255))
        assert np.all(layer.pixels == (40, 40, 40, 255))

        layer.clear()
        assert np.all(layer.pixels == 0)

    def test_replace_color(self):
        layer = Layer(4, 4)
        layer.fill((255, 0, 0, 255))
        layer.set_pixel(0, 0, (0, 255, 0, 255))

        count = layer.replace_color((255, 0, 0, 255), (128, 128, 128, 255))

        assert count == 4 * 4 - 1  # all but one pixel
        assert layer.get_pixel(0, 0) == (0, 255, 0, 255)


class TestTransformations:
    """Tests for resize and flip operations."""

    def test_resize_nearest(self):
        layer = Layer(4, 4)
        layer.set_pixel(0, 0, (255, 0, 0, 255))

        layer.resize(8, 8)

        assert layer.width == 8
        assert layer.height == 8
        # Nearest neighbor should duplicate the top-left pixel
        assert layer.get_pixel(0, 0) == (255, 0, 0, 255)
        assert layer.get_pixel(1, 0) == (255, 0, 0, 255)

    def test_flip_horizontal_vertical(self):
        layer = Layer(2, 2)
        layer.set_pixel(0, 0, (255, 0, 0, 255))  # top-left
        layer.set_pixel(1, 1, (0, 255, 0, 255))  # bottom-right

        layer.flip_horizontal()
        assert layer.get_pixel(1, 0) == (255, 0, 0, 255)
        assert layer.get_pixel(0, 1) == (0, 255, 0, 255)

        layer.flip_vertical()
        assert layer.get_pixel(1, 1) == (255, 0, 0, 255)


class TestSerialization:
    """Tests for to_dict / from_dict roundtrips."""

    def test_roundtrip_preserves_everything(self):
        layer = Layer(6, 6, name="Test", opacity=0.6, locked=True)
        layer.set_pixel(2, 3, (10, 20, 30, 40))
        layer.metadata["custom"] = {"foo": "bar"}

        data = layer.to_dict()
        restored = Layer.from_dict(data)

        assert restored.name == "Test"
        assert restored.opacity == 0.6
        assert restored.locked is True
        assert restored.get_pixel(2, 3) == (10, 20, 30, 40)
        assert restored.metadata == {"custom": {"foo": "bar"}}
        assert np.array_equal(restored.pixels, layer.pixels)

    def test_rgb_roundtrip(self):
        layer = Layer(3, 3, color_mode="RGB")
        layer.fill((255, 128, 64))
        restored = Layer.from_dict(layer.to_dict())
        assert restored.color_mode == "RGB"
        assert restored.channels == 3


class TestFactoryFunctions:
    """Tests for module-level helper functions."""

    def test_create_filled_layer(self):
        layer = create_filled_layer(8, 8, (50, 50, 50, 255), name="BG")
        assert layer.name == "BG"
        assert np.all(layer.pixels == (50, 50, 50, 255))


class TestProperties:
    """Tests for convenience properties."""

    def test_is_transparent(self):
        layer = Layer(4, 4)
        assert layer.is_transparent is True

        layer.set_pixel(0, 0, (0, 0, 0, 1))
        assert layer.is_transparent is False
