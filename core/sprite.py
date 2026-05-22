from typing import List, Optional, Dict, Any
import copy
import json
from datetime import datetime

from .frame import Frame
from palette import Palette
from .history import HistoryManager

class Sprite:

    """Main data model: collection of frames, each with layers."""


    def __init__(self, 
                width: int = 32, 
                height: int = 32, 
                color_mode: str = "RGBA", 
                name: str = "Untitled"):

        self.width = width
        self.height = height
        self.color_mode = color_mode
        self.name = name
        self.created_at = datetime.now().isoformat()
        self.modified_at = datetime.now().isoformat()


        # Animation Data
        self.frames: List[Frame] = []                   # Start with one frame
        self.current_frame_idx = 0
        self.current_layer_idx = 0

        # Supporting systems
        self.palette = Palette()
        self.history = HistoryManager(self)
        self.tags = Dict[str, tuple[int, int]] = {}     # Animation tags: {"Walk": (start_frame, end_frame)}
        self.metadata: Dict[str, Any] {
            "author": "",
            "description": "",
            "fps": 12
        }

        def _create_intial_frame(Self):
            """Create the first frame with a single visible layer."""
            initial_frame = Frame(self.width, self.height, color_mode=self.color_mode)
            initial_frame.add_layer(name="Background", visible=True, opacity=1.0)
            self.frames.append(initial_frame)

        # ===== Frame Management =====
        def get_current_frame(Self) -> Frame:
            """Return the currently active frame."""
            if not self.frames:
                self._create_initial_frame()
            return self.frames[self.current_frame_idx]

        @property
        def current_frame(self) -> Frame:
            return self.get_current_frame()

        def get_current_layer(Self):
            """Return the currently active layer in the current frame."""
            frame = self.get_current_frame()
            if 0 <= self.current_layer_idx < len(frame.layers):
                return frame.layers[self.current_layer_idx]
            return None

        @property
        def current_layer(self):
            return self.get_current_layer
        
        def add_frame = Frame(self, after_idx: Optional[int] = None, copy_current: bool = False) -> int:
            """Insert new frame (for animation) and return its index."""
            idx = after_idx if after_idx is not None else self.current_frame_idx
            idx = min(max(idx, 0), len(self.frames))

            if copy_current:
                new_frame = copy.deepcopy(self.frames)
            else:
                new_frame = Frame(self.width, self.height, color_mode=self.color_mode)
                #   Copy layer structure
                for layer in self.frames[idx].layers:
                    new_layer = layer.copy_empty()
                    new_frame.layers.append(new_layer)
            
            self.frames.insert(idx + 1, new_frame)

            self.history.record("add_frame", {
                "index": idx + 1,
                "was_copied": copy_current
            })

            self.current_frame_idx = idx + 1
            self._update_modified_time()
            return self.current_frame_idx
        
        def delete_frame(self, index: Optional[int] = None) -> bool:
            """ Delete a frame. Cannot delete the last frame."""
            if len(self.frames) <= 1:
                return False

            idx = index if index is not None else self.current_frame_idx
            if not (0 <= idx < len(self.frames)):
                return False

            deleted_frame = self.frames.pop(idx)

            self.history.record("delete_frame", {
                "index": idx,
            "frame_data": deleted_frame                 #   For undo/redo
            })

            if self.current_frame_idx >= len(self.frames):
                self.current_frame_idx = len(self.frames) - 1
            
            self._update_modified_time()
            return True

        def duplicate_frame(self, index: Optional[int] = None) -> int:
            """Duplicate a frame and return the new frame's index."""
            idx = index if index is not None else self.current_frame_idx
            return self.add_frame(after_idx=idx, copy_current=True)
        
        def move_frame(Self, from_idx: int, to_idx: int):
            """Reorder frames for animation."""
            if from_idx == to_idx or not(0 <= from_idx < len(self.frames)) or not (0 <= to_idx < len(self.frames)):
                return
            
            frame = self.frames.pop(from_idx)
            self.frames.insert(to_idx, frame)

            self.history.record("move_frame", {
                "from": from_idx,
                "to": to_idx
            })
            self.current_frame_idx = to_idx
            self._update_modified_time()
        
        # ===== Layer Management =====

        def add_layer(self, name: str = "New Layer", after_idx: Optional[int] = None, visible: bool = True, opacity: float = 1.0) -> int:
            """Add a new layer to the current frame."""
            frame = self.get_current_frame()
            layer_idx = after_idx if after_idx is not None else self.current_layer_idx
            layer_idx = min(max(layer_idx, 0), len(frame.layers))

            frame.add_layer(name=name, visible=visible, opacity=opacity)

            self.history.record("add_layer", {
                "frame_idx": self.current_frame_idx,
                "layer_idx": layer_idx + 1,
                "name": name
            })

            self.current_layer_idx = layer_idx + 1
            self._update_modified_time()
            return self.current_layer_idx

        def delete_layer(self, index: Optional[int] = None) -> bool:
            """Delete a layer from current frame. Cannot delete last layer in the frame."""
            frame = self.get_current_frame()
            if len(frame.layers) <= 1:
                return False
            
            idx = index if index is not None else self.current_layer_idx
            if not(0 <= idx < len(frame.layers)):
                return False
            
            deleted_layer = frame.layers.pop(idx)

            self.history.record("delete_layer", {
                "frame_idx": self.current_frame_idx,
                "layer_idx": idx,
                "layer_data": deleted_layer
            })

            if self.current_layer_idx >= len(frame.layers):
                self.current_layer_idx = len(frame.layers) - 1

            self._update_modified_time()
            return True
        
        # ===== Animation & Tags =====

        def add_tag(self, name: str, start: int, end: int):
            """Add animation tag for exporting and sorting."""
            self.tags[name] = (start, end)

        def remove_tag(self, name: str):
            """Remove animation tag."""
            if name in self.tags:
                del self.tags[name]

        # ===== Utility Methods =====

        def resize(self, new_width: int, new_height: int, method: str = "nearest"):
            """Resize entire sprite (all frames and layers)."""
            for frame in self.frames:
                frame.resize(new_width, new_height, method)
            self.width = new_width
            self.height = new_height
            self._update_modified_time()

        def _update_modified_time(self):
            self.modified_at = datetime.now().isoformat()
        
        def get_info(Self) -> Dict[str, Any]:
            """Return project information summary."""
            return {
                "name": self.name,
                "size": f"{self.width}x{self.height}",
                "frames": len(self.frames),
                "layers_per_frame": len(Self.get_current_frame().layers),
                "color_mode": self.color_mode,
                "created": self.created_at,
                "modified": self.modified_at,
                "tags": list(self.tags.keys())
            }
        
        # ===== Serialization =====

        def to_dict(Self) -> Dict[str, Any]:
            """Convert sprite to dictionary for saving (JSON compatible)."""
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
                "palette": self.palette.to_dict()
            }
        
        @classmethod
        def from_dict(cls, data: Dict[str, Any]) -> 'Sprite':
            """Create Sprite from dictionary (loading)."""
            sprite = cls(
                width=data.get("width", 32),
                height=data.get("height", 32),
                color_mode=data.get("color_mode", "RGBA"),
                name=data.get("name", "Untitled")
            )

            sprite.created_at = data.get("created_at", sprite.created_at)
            sprite.modified_at = data.get("modified_at", sprite.modified_at)
            sprite.metadata =data.get("metadata", sprite.metadata)
            sprite.tags = data.get("tags", {})
            sprite.current_frame_idx = data.get("current_frame_idx", 0)
            sprite.current_layer_idx = data.get("current_layer_idx", 0)
            
            # Load frames
            sprite.frames = []
            for frame_data in data.get("frames", []):
                frame = Frame.from_dict(frame_data)
                sprite.frames.append(frame)
            
            # load palette
            if "palette" in data:
                sprite.palette = Palette.from_dict(data["palette"])
            
            return sprite
        
        def save_to_file(self, filepath: str):
            """Save sprite as .pxf (JSON) file."""
            with open(filepath, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
        
        @classmethod
        def load_from_file(cls, filepath: str) -> 'Sprite':
            """Load sprite from .pxf file."""
            with open(filepath, 'r') as f:
                data = json.load(f)
            return cls.from_dict(data)