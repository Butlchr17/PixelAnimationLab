"""
core/history.py - Undo/Redo system for PixelAnimationLab.

The HistoryManager records changes made to a Sprite and its contents
(frames, layers, pixels, etc.) so the user can undo and redo actions.

Current implementation is a minimal but functional foundation:
- Action recording with metadata
- Basic undo / redo stacks
- Ability to group actions in the future

Future improvements (when needed):
- Command pattern with proper apply/unapply methods
- Selective invalidation (e.g. after a resize, some history may be invalid)
- Disk-backed history for very large projects
- Per-layer or per-frame history branches
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .sprite import Sprite


class HistoryManager:
    """
    Records and manages undo/redo history for a Sprite.

    Each recorded action is a simple dictionary containing:
    - "action": string identifier (e.g. "add_frame", "delete_layer", "draw")
    - "data": arbitrary payload needed to undo/redo the action
    """

    def __init__(self, sprite: "Sprite", max_history: int = 100):
        self.sprite = sprite
        self.max_history = max_history

        self._undo_stack: List[Dict[str, Any]] = []
        self._redo_stack: List[Dict[str, Any]] = []
        self._enabled = True

    def record(self, action: str, data: Dict[str, Any]) -> None:
        """
        Record a new action in the history.

        This should be called by Sprite (and eventually Frame/Layer) after
        a mutating operation succeeds.
        """
        if not self._enabled:
            return

        entry = {
            "action": action,
            "data": data,
        }

        self._undo_stack.append(entry)
        # Clear redo stack on new action (standard behavior)
        self._redo_stack.clear()

        # Enforce size limit
        if len(self._undo_stack) > self.max_history:
            self._undo_stack.pop(0)

    def undo(self) -> Optional[Dict[str, Any]]:
        """Undo the last action. Returns the action entry if something was undone."""
        if not self._undo_stack:
            return None

        entry = self._undo_stack.pop()
        self._redo_stack.append(entry)

        # Note: Actual undo logic is not yet implemented here.
        # For now we just track what happened. Full undo will be added
        # once we have a proper command pattern or when Sprite/Frame expose
        # more reversible operations.
        return entry

    def redo(self) -> Optional[Dict[str, Any]]:
        """Redo the last undone action."""
        if not self._redo_stack:
            return None

        entry = self._redo_stack.pop()
        self._undo_stack.append(entry)
        return entry

    def clear(self) -> None:
        """Clear all history (e.g. after loading a new file)."""
        self._undo_stack.clear()
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    @property
    def undo_count(self) -> int:
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        return len(self._redo_stack)

    def __repr__(self) -> str:
        return f"HistoryManager(undo={self.undo_count}, redo={self.redo_count})"
