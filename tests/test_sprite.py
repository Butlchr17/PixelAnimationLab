"""
tests/test_sprite.py

High-level integration tests for the Sprite class.

Sprite is the root container. These tests verify that:
- Sprite correctly orchestrates Frame and Layer creation/manipulation
- The two animation duplication paths work as expected from the Sprite API
- Project-level operations (resize, serialization, tags) function
- History recording is triggered on mutating operations
- Loading a saved project reconstructs a usable object

These tests are the closest thing we have to "does the whole data model work?"
"""

import numpy as np

from core.sprite import Sprite


class TestSpriteCreation:
    """Basic construction and initial state."""

    def test_default_sprite(self):
        s = Sprite()
        assert s.width == 32
        assert s.height == 32
        assert len(s.frames) == 1
        assert len(s.current_frame.layers) == 1
        assert s.current_frame.layers[0].name == "Background"

    def test_custom_initialization(self):
        s = Sprite(64, 48, name="MyGameCharacter")
        assert s.name == "MyGameCharacter"
        assert s.get_info()["size"] == "64x48"


class TestFrameManagementViaSprite:
    """Tests for adding, duplicating, and deleting frames through Sprite."""

    def test_add_empty_frame(self):
        s = Sprite(16, 16)
        new_idx = s.add_frame()
        assert len(s.frames) == 2
        assert new_idx == 1
        # New frame should have same layer structure
        assert s.frames[1].get_layer_names() == ["Background"]

    def test_add_frame_with_pixel_copy(self):
        s = Sprite(8, 8)
        s.current_frame.layers[0].set_pixel(0, 0, (255, 0, 0, 255))

        new_idx = s.add_frame(copy_current=True)
        assert len(s.frames) == 2
        # Copied frame should have the pixel data
        assert s.frames[new_idx].layers[0].get_pixel(0, 0) == (255, 0, 0, 255)

    def test_delete_frame_protection(self):
        s = Sprite()
        assert s.delete_frame() is False  # cannot delete last frame
        assert len(s.frames) == 1

    def test_duplicate_frame(self):
        s = Sprite()
        s.current_frame.layers[0].set_pixel(3, 3, (128, 128, 128, 255))
        idx = s.duplicate_frame()
        assert len(s.frames) == 2
        assert s.frames[idx].layers[0].get_pixel(3, 3) == (128, 128, 128, 255)


class TestLayerManagementViaSprite:
    """Layer operations should delegate cleanly to the current frame."""

    def test_add_and_delete_layers(self):
        s = Sprite(8, 8)
        s.add_layer("Character")
        s.add_layer("Shadow")

        assert s.current_frame.get_layer_names() == ["Background", "Character", "Shadow"]

        s.delete_layer(1)  # delete Character
        assert s.current_frame.get_layer_names() == ["Background", "Shadow"]

    def test_cannot_delete_last_layer(self):
        s = Sprite()
        assert s.delete_layer() is False


class TestSpriteResize:
    """Project-wide resize must affect every frame and layer."""

    def test_resize_propagates_everywhere(self):
        s = Sprite(8, 8)
        s.add_frame()
        s.add_layer("Extra")

        s.resize(4, 4)

        assert s.width == 4 and s.height == 4
        for frame in s.frames:
            assert frame.width == 4 and frame.height == 4
            for layer in frame.layers:
                assert layer.width == 4 and layer.height == 4


class TestSerialization:
    """End-to-end save/load must be lossless for practical use."""

    def test_full_roundtrip(self):
        s = Sprite(12, 12, name="TestAnim")
        s.add_layer("Player")
        s.frames[0].layers[1].set_pixel(5, 5, (255, 200, 50, 255))

        s.add_frame(copy_current=True)
        s.add_tag("Run", 0, 1)

        data = s.to_dict()
        loaded = Sprite.from_dict(data)

        assert loaded.name == "TestAnim"
        assert len(loaded.frames) == 2
        assert loaded.tags == {"Run": (0, 1)}
        assert loaded.frames[0].layers[1].get_pixel(5, 5) == (255, 200, 50, 255)
        assert loaded.palette is not None

    def test_save_load_file_roundtrip(self, tmp_path):
        s = Sprite(8, 8, name="FileTest")
        path = tmp_path / "test.pxf"
        s.save_to_file(str(path))

        loaded = Sprite.load_from_file(str(path))
        assert loaded.name == "FileTest"


class TestHistoryRecording:
    """Sprite should record important mutations via HistoryManager."""

    def test_history_records_frame_and_layer_changes(self):
        s = Sprite(8, 8)
        s.add_frame()
        s.add_layer("FX")
        s.delete_layer(1)

        # We don't assert exact count because implementation may evolve,
        # but we expect several recorded actions.
        assert s.history.undo_count >= 3
        assert s.history.can_undo() is True


class TestTagsAndMetadata:
    """Animation tagging and project metadata."""

    def test_add_remove_tags(self):
        s = Sprite()
        s.add_tag("Idle", 0, 3)
        s.add_tag("Walk", 4, 9)
        assert "Idle" in s.tags

        s.remove_tag("Idle")
        assert "Idle" not in s.tags
