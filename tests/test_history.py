"""
tests/test_history.py

Tests for the HistoryManager.

At the moment HistoryManager is a recording + stack manager. These tests
verify that actions are recorded, undo/redo stacks behave correctly, and
that the manager does not crash when used by Sprite.

Full command-based undo (actual state reversal) will require more work
in the future and can be tested more thoroughly then.
"""

from core.history import HistoryManager
from core.sprite import Sprite


class TestHistoryRecording:
    def test_records_actions(self):
        s = Sprite()
        h = s.history

        s.add_frame()
        s.add_layer("Test")

        assert h.undo_count >= 2
        assert h.can_undo() is True
        assert h.can_redo() is False

    def test_undo_moves_action_to_redo_stack(self):
        s = Sprite()
        h = s.history
        initial = h.undo_count

        s.add_frame()
        assert h.undo_count == initial + 1

        entry = h.undo()
        assert entry is not None
        assert h.can_redo() is True
        assert h.undo_count == initial

    def test_redo_moves_action_back(self):
        s = Sprite()
        h = s.history
        s.add_frame()
        h.undo()

        entry = h.redo()
        assert entry is not None
        assert h.can_redo() is False

    def test_clear_history(self):
        s = Sprite()
        s.history.clear()
        assert s.history.undo_count == 0
        assert s.history.redo_count == 0
