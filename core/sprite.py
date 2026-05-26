"""
core/sprite.py - The top-level container for a complete PixelAnimationLab project.

A Sprite is the root object that represents an entire animation or pixel art
document. It contains:

- Multiple Frames (the animation timeline)
- A shared Palette
- A HistoryManager for undo/redo
- Animation metadata (tags, fps, author info, etc.)

This class orchestrates Frames and Layers but tries to stay relatively thin.
Most low-level pixel and layer operations live in Frame and Layer.

Design notes:
- Sprite manages the "current frame" and "current layer" selection (UI state).
- Frame and Layer are responsible for their own data and operations.
- We use Frame.create_empty_clone() and Frame.copy() for the two main
  duplication patterns needed in animation work.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from .frame import Frame
from .history import HistoryManager
from .layer import Layer
from .palette import Palette


class Sprite:
    """
    The main data model: a complete pixel art animation or illustration.

    A Sprite owns a sequence of Frames. Each Frame owns its own stack of Layers.
    This three-level hierarchy (Sprite → Frames → Layers) matches the structure
    used by professional tools like Aseprite.
    """

    def __init__(
        self,
        width: int = 32,
        height: int = 32,
        color_mode: str = "RGBA",
        name: str = "Untitled",
    ) -> None:
        self.width = width
        self.height = height
        self.color_mode = color_mode
        self.name = name

        self.created_at = datetime.now().isoformat()
        self.modified_at = datetime.now().isoformat()

        # === Animation Data ===
        self.frames: List[Frame] = []
        self.current_frame_idx: int = 0
        self.current_layer_idx: int = 0

        # === Supporting Systems ===
        self.palette = Palette()
        self.history = HistoryManager(self)

        # Animation tags: {"Walk": (start_frame, end_frame), ...}
        self.tags: Dict[str, tuple[int, int]] = {}

        # Project metadata
        self.metadata: Dict[str, Any] = {
            "author": "",
            "description": "",
            "fps": 12,
        }

        # Create the initial frame with one layer
        self._create_initial_frame()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _create_initial_frame(self) -> None:
        """Create the first frame with a single visible background layer."""
        if self.frames:
            return  # Already initialized

        frame = Frame(
            width=self.width,
            height=self.height,
            color_mode=self.color_mode,
        )
        # Ensure the default layer has a nice name
        if frame.layers:
            frame.layers[0].name = "Background"

        self.frames.append(frame)
        self.current_frame_idx = 0
        self.current_layer_idx = 0

    def _update_modified_time(self) -> None:
        self.modified_at = datetime.now().isoformat()

    def _get_current_frame(self) -> Frame:
        """Return the active frame, creating one if necessary."""
        if not self.frames:
            self._create_initial_frame()
        return self.frames[self.current_frame_idx]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_frame(self) -> Frame:
        return self._get_current_frame()

    @property
    def current_layer(self) -> Optional[Layer]:
        """Return the currently selected layer in the current frame."""
        frame = self._get_current_frame()
        if 0 <= self.current_layer_idx < len(frame.layers):
            return frame.layers[self.current_layer_idx]
        return None

    # ------------------------------------------------------------------
    # Frame Management
    # ------------------------------------------------------------------

    def add_frame(
        self,
        after_idx: Optional[int] = None,
        copy_current: bool = False,
    ) -> int:
        """
        Insert a new frame into the animation.

        Args:
            after_idx: Insert after this frame index. Defaults to current frame.
            copy_current: If True, duplicate the pixel content of the current
                          frame. If False, create a new frame with the same
                          layer structure but empty pixels (the common case).

        Returns:
            Index of the newly created frame.
        """
        if after_idx is None:
            after_idx = self.current_frame_idx

        after_idx = max(0, min(after_idx, len(self.frames) - 1))

        if copy_current:
            new_frame = self.frames[after_idx].copy()
        else:
            # Preferred animation workflow: same layer names/props, empty pixels
            new_frame = self.frames[after_idx].create_empty_clone()

        insert_pos = after_idx + 1
        self.frames.insert(insert_pos, new_frame)

        self.history.record("add_frame", {
            "index": insert_pos,
            "was_copied": copy_current,
        })

        self.current_frame_idx = insert_pos
        self._update_modified_time()
        return insert_pos

    def delete_frame(self, index: Optional[int] = None) -> bool:
        """Delete a frame. Cannot delete the last remaining frame."""
        if len(self.frames) <= 1:
            return False

        if index is None:
            index = self.current_frame_idx

        if not (0 <= index < len(self.frames)):
            return False

        deleted = self.frames.pop(index)

        self.history.record("delete_frame", {
            "index": index,
            "frame_data": deleted,  # kept for potential future undo
        })

        # Adjust current frame index
        if self.current_frame_idx >= len(self.frames):
            self.current_frame_idx = len(self.frames) - 1

        self._update_modified_time()
        return True

    def duplicate_frame(self, index: Optional[int] = None) -> int:
        """Duplicate a frame (with full pixel data) and return its new index."""
        if index is None:
            index = self.current_frame_idx
        return self.add_frame(after_idx=index, copy_current=True)

    def move_frame(self, from_idx: int, to_idx: int) -> None:
        """Reorder frames in the timeline."""
        if from_idx == to_idx:
            return
        if not (0 <= from_idx < len(self.frames)):
            return
        if not (0 <= to_idx < len(self.frames)):
            return

        frame = self.frames.pop(from_idx)
        self.frames.insert(to_idx, frame)

        self.history.record("move_frame", {
            "from": from_idx,
            "to": to_idx,
        })

        self.current_frame_idx = to_idx
        self._update_modified_time()

    # ------------------------------------------------------------------
    # Layer Management (delegates to current Frame)
    # ------------------------------------------------------------------

    def add_layer(
        self,
        name: str = "New Layer",
        after_idx: Optional[int] = None,
        visible: bool = True,
        opacity: float = 1.0,
    ) -> int:
        """Add a new layer to the current frame."""
        frame = self._get_current_frame()

        if after_idx is None:
            after_idx = self.current_layer_idx

        new_layer_idx = frame.add_layer(
            name=name,
            after_idx=after_idx,
            visible=visible,
            opacity=opacity,
        )

        self.history.record("add_layer", {
            "frame_idx": self.current_frame_idx,
            "layer_idx": new_layer_idx,
            "name": name,
        })

        self.current_layer_idx = new_layer_idx
        self._update_modified_time()
        return new_layer_idx

    def delete_layer(self, index: Optional[int] = None) -> bool:
        """Delete a layer from the current frame. Cannot delete the last layer."""
        frame = self._get_current_frame()

        if len(frame.layers) <= 1:
            return False

        if index is None:
            index = self.current_layer_idx

        if not (0 <= index < len(frame.layers)):
            return False

        deleted = frame.layers.pop(index)

        self.history.record("delete_layer", {
            "frame_idx": self.current_frame_idx,
            "layer_idx": index,
            "layer_data": deleted,
        })

        if self.current_layer_idx >= len(frame.layers):
            self.current_layer_idx = len(frame.layers) - 1

        self._update_modified_time()
        return True

    # ------------------------------------------------------------------
    # Animation Tags
    # ------------------------------------------------------------------

    def add_tag(self, name: str, start: int, end: int) -> None:
        """Define a named animation range (e.g. 'Walk', 'Attack')."""
        self.tags[name] = (start, end)

    def remove_tag(self, name: str) -> None:
        if name in self.tags:
            del self.tags[name]

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def resize(self, new_width: int, new_height: int, method: str = "nearest") -> None:
        """Resize the entire sprite (all frames and all layers)."""
        for frame in self.frames:
            frame.resize(new_width, new_height, method=method)

        self.width = new_width
        self.height = new_height
        self._update_modified_time()

    def get_info(self) -> Dict[str, Any]:
        """Return a summary of the project."""
        return {
            "name": self.name,
            "size": f"{self.width}x{self.height}",
            "frames": len(self.frames),
            "layers_per_frame": len(self.current_frame.layers) if self.frames else 0,
            "color_mode": self.color_mode,
            "created": self.created_at,
            "modified": self.modified_at,
            "tags": list(self.tags.keys()),
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Convert the entire sprite to a JSON-serializable dictionary."""
        return {
            "version": "1.0",
            "width": self.width,
            "height": self.height,
            "color_mode": self.color_mode,
            "name": self.name,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "metadata": self.metadata,
            "tags": self.tags,
            "current_frame_idx": self.current_frame_idx,
            "current_layer_idx": self.current_layer_idx,
            "frames": [frame.to_dict() for frame in self.frames],
            "palette": self.palette.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Sprite":
        """Reconstruct a Sprite from a dictionary (loading)."""
        sprite = cls(
            width=data.get("width", 32),
            height=data.get("height", 32),
            color_mode=data.get("color_mode", "RGBA"),
            name=data.get("name", "Untitled"),
        )

        sprite.created_at = data.get("created_at", sprite.created_at)
        sprite.modified_at = data.get("modified_at", sprite.modified_at)
        sprite.metadata = data.get("metadata", sprite.metadata)
        sprite.tags = data.get("tags", {})
        sprite.current_frame_idx = data.get("current_frame_idx", 0)
        sprite.current_layer_idx = data.get("current_layer_idx", 0)

        # Load frames
        frame_data_list = data.get("frames", [])
        if frame_data_list:
            sprite.frames = [Frame.from_dict(fd) for fd in frame_data_list]

        # Load palette
        if "palette" in data:
            sprite.palette = Palette.from_dict(data["palette"])

        # Ensure we have at least one frame
        if not sprite.frames:
            sprite._create_initial_frame()

        return sprite

    def save_to_file(self, filepath: str) -> None:
        """Save the sprite as a .pxf (JSON) file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> "Sprite":
        """Load a sprite from a .pxf file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
