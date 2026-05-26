"""
tests/test_frame.py

Tests for the Frame class and its interactions with Layer.

Frames represent a single moment in time in an animation. They are primarily
containers for an ordered list of Layers, but also carry timing information
(duration) and provide high-level layer stack operations.

Key behaviors tested here:
- Layer stack management (add, delete, duplicate, move)
- The two duplication strategies: copy() vs create_empty_clone()
- Propagation of operations (resize) to all child layers
- Serialization
- Protection against deleting the last layer
"""

import numpy as np
import pytest

from core.frame import Frame
from core.layer import Layer


class TestFrameConstruction:
    """Tests for Frame initialization."""

    def test_default_frame_has_one_background_layer(self):
        frame = Frame(16, 16)
        assert frame.width == 16
        assert frame.height == 16
        assert len(frame.layers) == 1
        assert frame.layers[0].name == "Background"
        assert frame.duration == 100  # default

    def test_custom_duration_and_color_mode(self):
        frame = Frame(8, 8, color_mode="RGB", duration=50)
        assert frame.color_mode == "RGB"
        assert frame.duration == 50
        assert frame.layers[0].color_mode == "RGB"

    def test_constructor_with_existing_layers(self):
        l1 = Layer(4, 4, name="A")
        l2 = Layer(4, 4, name="B")
        frame = Frame(4, 4, layers=[l1, l2])
        assert frame.layer_count == 2
        assert frame.get_layer_names() == ["A", "B"]


class TestLayerStackOperations:
    """Tests for adding, removing, and reordering layers."""

    def test_add_layer_appends_by_default(self):
        frame = Frame(8, 8)
        idx = frame.add_layer("Foreground")
        assert idx == 1
        assert frame.get_layer_names() == ["Background", "Foreground"]

    def test_add_layer_at_specific_position(self):
        frame = Frame(8, 8)
        frame.add_layer("Top")
        frame.add_layer("Middle", after_idx=0)
        assert frame.get_layer_names() == ["Background", "Middle", "Top"]

    def test_delete_layer_protects_last_layer(self):
        frame = Frame(8, 8)
        assert frame.delete_layer() is False  # only one layer
        assert frame.layer_count == 1

    def test_delete_specific_layer(self):
        frame = Frame(8, 8)
        frame.add_layer("FX")
        frame.add_layer("UI")
        assert frame.delete_layer(1) is True
        # After adding FX then UI, index 1 is FX. Deleting it leaves UI.
        assert frame.get_layer_names() == ["Background", "UI"]

    def test_duplicate_layer(self):
        frame = Frame(8, 8)
        frame.layers[0].set_pixel(0, 0, (255, 0, 0, 255))
        new_idx = frame.duplicate_layer(0)
        assert frame.layer_count == 2
        assert frame.layers[new_idx].name == "Background copy"
        assert frame.layers[new_idx].get_pixel(0, 0) == (255, 0, 0, 255)

    def test_move_layer(self):
        frame = Frame(8, 8)
        frame.add_layer("A")
        frame.add_layer("B")
        frame.move_layer(2, 0)  # move B to bottom
        assert frame.get_layer_names() == ["B", "Background", "A"]


class TestFrameDuplication:
    """
    Critical tests for animation workflows.

    - create_empty_clone() is used when inserting a normal new frame.
    - copy() is used for explicit "Duplicate Frame" commands.
    """

    def test_create_empty_clone_preserves_structure_but_clears_pixels(self):
        frame = Frame(8, 8)
        frame.add_layer("Character")
        frame.layers[1].set_pixel(4, 4, (255, 255, 0, 255))

        clone = frame.create_empty_clone()

        assert clone.width == frame.width
        assert clone.height == frame.height
        assert clone.duration == frame.duration
        assert clone.get_layer_names() == frame.get_layer_names()
        assert np.all(clone.layers[1].pixels == 0)
        assert np.any(frame.layers[1].pixels != 0)  # original untouched

    def test_copy_is_deep(self):
        frame = Frame(8, 8)
        frame.layers[0].set_pixel(1, 1, (10, 20, 30, 255))

        duplicate = frame.copy()
        duplicate.layers[0].set_pixel(1, 1, (99, 99, 99, 255))

        assert frame.layers[0].get_pixel(1, 1) == (10, 20, 30, 255)
        assert duplicate.layers[0].get_pixel(1, 1) == (99, 99, 99, 255)


class TestFrameTransformations:
    """Tests that operations correctly affect all layers."""

    def test_resize_affects_all_layers(self):
        frame = Frame(8, 8)
        frame.add_layer("Overlay")
        frame.resize(4, 4)

        assert frame.width == 4
        assert frame.height == 4
        for layer in frame.layers:
            assert layer.width == 4
            assert layer.height == 4


class TestFrameSerialization:
    """Serialization roundtrip tests."""

    def test_frame_roundtrip(self):
        frame = Frame(6, 6, duration=120)
        frame.add_layer("Effects")
        frame.layers[1].set_pixel(2, 2, (255, 128, 0, 255))

        data = frame.to_dict()
        restored = Frame.from_dict(data)

        assert restored.duration == 120
        assert restored.layer_count == 2
        assert restored.get_layer_names() == ["Background", "Effects"]
        assert restored.layers[1].get_pixel(2, 2) == (255, 128, 0, 255)


class TestConvenienceFeatures:
    """Tests for dunder methods and helpers."""

    def test_len_and_indexing(self):
        frame = Frame(4, 4)
        frame.add_layer("A")
        assert len(frame) == 2
        assert frame[1].name == "A"

    def test_get_layer_raises_on_bad_index(self):
        frame = Frame(4, 4)
        with pytest.raises(IndexError):
            frame.get_layer(5)
