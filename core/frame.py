"""
core/frame.py - A single moment in time within a Sprite's animation.

In PixelAnimationLab (and in Aseprite-like editors), a "Frame" represents one
discrete point in the animation timeline. It owns a complete, ordered stack of
Layer objects that together form the image visible at that moment.

Terminology note:
- In Aseprite, these are often called "frames" in the timeline and "cels" when
  referring to the content on a specific layer within that frame.
- For simplicity and clarity in this codebase, we use "Frame" for the timeline
  unit and "Layer" (cel) for the per-layer content inside it.

Relationship to other core classes:
- Sprite owns a list of Frames (the animation timeline)
- Frame owns a list of Layers (the layer stack for that moment)
- Layer owns the actual pixel data

This separation is deliberate and enables powerful workflows:
- Different frames can have completely independent pixel content per layer
- Layer structure (names, visibility, opacity, blend modes) can be kept
  consistent across frames while pixel data changes (the common case)
- Future features like "linked cels" (same layer data reused across frames)
  or layer groups can be added without changing the fundamental model

Design Goals (matching the original project vision):
- Modularity: Frame knows nothing about the global timeline, UI, or history.
- Extensibility: Easy to add per-frame metadata, tags, or special layer types.
- Animation-first: First-class support for the two most common duplication
  patterns needed when working with animation.
- Clean API: Callers should rarely need to manipulate the .layers list directly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .layer import Layer


class Frame:
    """
    Represents one frame (point in time) in an animation.

    A Frame is primarily a container and manager for an ordered list of Layer
    objects. It also carries timing information (duration) that the animation
    system uses when playing the sprite.

    Attributes:
        width (int): Width of the frame in pixels. All layers should match.
        height (int): Height of the frame in pixels. All layers should match.
        color_mode (str): "RGBA" or "RGB". Propagated to new layers.
        duration (int): How long this frame should be displayed during playback,
                        in milliseconds. Default is 100 (10 fps baseline).
        layers (List[Layer]): The ordered layer stack. Index 0 is the bottom layer.
        metadata (Dict[str, Any]): Extensibility bag for future features
                                   (e.g. frame labels, camera positions, notes).
    """

    def __init__(
        self,
        width: int,
        height: int,
        color_mode: str = "RGBA",
        duration: int = 100,
        layers: Optional[List[Layer]] = None,
    ) -> None:
        """
        Create a new Frame.

        Args:
            width: Pixel width for the frame and all layers.
            height: Pixel height for the frame and all layers.
            color_mode: Color mode to use when creating new layers.
            duration: Playback duration in milliseconds.
            layers: Optional list of Layer objects to initialize with.
                    If None, the frame starts with a single default "Background" layer.

        The constructor intentionally creates a sensible default layer when none
        are provided. This matches the common expectation when creating a brand
        new frame in a pixel art tool.
        """
        if width <= 0 or height <= 0:
            raise ValueError(f"Frame dimensions must be positive, got {width}x{height}")
        if duration <= 0:
            raise ValueError(f"Frame duration must be positive, got {duration}")

        self.width = int(width)
        self.height = int(height)
        self.color_mode = color_mode
        self.duration = int(duration)
        self.metadata: Dict[str, Any] = {}

        if layers is not None:
            self.layers: List[Layer] = list(layers)
            # Sanity: ensure layers match frame size (we don't auto-resize here)
            for layer in self.layers:
                if layer.width != self.width or layer.height != self.height:
                    raise ValueError(
                        f"Layer '{layer.name}' size ({layer.width}x{layer.height}) "
                        f"does not match Frame size ({self.width}x{self.height})"
                    )
        else:
            # Default starting state: one background layer, fully transparent
            bg = Layer(
                width=self.width,
                height=self.height,
                name="Background",
                visible=True,
                opacity=1.0,
                color_mode=self.color_mode,
            )
            self.layers = [bg]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def layer_count(self) -> int:
        """Number of layers currently in this frame."""
        return len(self.layers)

    @property
    def is_empty(self) -> bool:
        """True if the frame has no layers."""
        return len(self.layers) == 0

    # ------------------------------------------------------------------
    # Layer Stack Management (The Primary Responsibility of Frame)
    # ------------------------------------------------------------------

    def add_layer(
        self,
        name: str = "New Layer",
        after_idx: Optional[int] = None,
        visible: bool = True,
        opacity: float = 1.0,
        **layer_kwargs: Any,
    ) -> int:
        """
        Create and insert a new Layer into the stack.

        Args:
            name: Display name for the new layer.
            after_idx: Insert the new layer after this index.
                       If None, the layer is appended to the top of the stack.
            visible: Initial visibility.
            opacity: Initial opacity (0.0–1.0).
            **layer_kwargs: Additional arguments passed to the Layer constructor
                            (e.g. locked=True, blend_mode="multiply").

        Returns:
            The index at which the new layer was inserted.
        """
        layer = Layer(
            width=self.width,
            height=self.height,
            name=name,
            visible=visible,
            opacity=opacity,
            color_mode=self.color_mode,
            **layer_kwargs,
        )

        if after_idx is None:
            self.layers.append(layer)
            return len(self.layers) - 1

        idx = max(0, min(after_idx + 1, len(self.layers)))
        self.layers.insert(idx, layer)
        return idx

    def delete_layer(self, index: Optional[int] = None) -> bool:
        """
        Remove a layer from the frame.

        Args:
            index: Index of the layer to delete. If None, deletes the top layer.

        Returns:
            True if a layer was deleted, False if the frame would be left with zero layers.

        Note:
            We deliberately refuse to delete the last layer. This matches common
            pixel art tool behavior and prevents invalid frame states. Higher-level
            code (Sprite) can decide whether to delete the entire frame instead.
        """
        if len(self.layers) <= 1:
            return False

        if index is None:
            index = len(self.layers) - 1

        if not (0 <= index < len(self.layers)):
            return False

        self.layers.pop(index)
        return True

    def duplicate_layer(self, index: Optional[int] = None) -> int:
        """
        Duplicate an existing layer (full pixel data copy) and insert the copy above it.

        Returns:
            Index of the newly created duplicate layer.
        """
        if index is None:
            index = len(self.layers) - 1

        if not (0 <= index < len(self.layers)):
            raise IndexError("Layer index out of range")

        original = self.layers[index]
        duplicate = original.copy()  # deep copy including pixels
        duplicate.name = f"{original.name} copy"

        insert_pos = index + 1
        self.layers.insert(insert_pos, duplicate)
        return insert_pos

    def move_layer(self, from_idx: int, to_idx: int) -> None:
        """
        Reorder layers within the stack.

        This is a common operation when the user drags layers in the layer panel.
        """
        if from_idx == to_idx:
            return
        if not (0 <= from_idx < len(self.layers)):
            raise IndexError("from_idx out of range")
        if not (0 <= to_idx < len(self.layers)):
            raise IndexError("to_idx out of range")

        layer = self.layers.pop(from_idx)
        self.layers.insert(to_idx, layer)

    def get_layer(self, index: int) -> Layer:
        """Return the Layer at the given index."""
        if not (0 <= index < len(self.layers)):
            raise IndexError(f"Layer index {index} out of range (0–{len(self.layers)-1})")
        return self.layers[index]

    def get_layer_index(self, layer: Layer) -> int:
        """Return the index of a specific Layer object, or -1 if not found."""
        try:
            return self.layers.index(layer)
        except ValueError:
            return -1

    # ------------------------------------------------------------------
    # Animation-Friendly Duplication (Critical for Sprite / Timeline)
    # ------------------------------------------------------------------

    def copy(self) -> "Frame":
        """
        Create a complete, independent deep copy of this frame.

        Every Layer and all of its pixel data is duplicated. Use this when the
        user explicitly chooses "Duplicate Frame" and wants an exact pixel copy
        to start editing from.

        This is relatively expensive for large animations. Prefer
        `create_empty_clone()` when inserting new frames in a typical animation
        workflow.
        """
        new_layers = [layer.copy() for layer in self.layers]
        new_frame = Frame(
            width=self.width,
            height=self.height,
            color_mode=self.color_mode,
            duration=self.duration,
            layers=new_layers,
        )
        new_frame.metadata = self.metadata.copy()
        return new_frame

    def create_empty_clone(self) -> "Frame":
        """
        Create a new Frame with the exact same layer *structure* but empty pixels.

        For each layer we call `Layer.copy_empty()`, preserving:
        - name, visible, opacity, locked, blend_mode
        - any metadata attached to the layer

        This is the operation you almost always want when the user presses
        "New Frame" while animating. The new frame has the same layer stack
        layout the artist is used to, but starts fully transparent so they can
        draw the next pose / frame of animation.

        This method exists specifically to support the animation workflow
        cleanly without forcing callers to do manual layer-by-layer copying.
        """
        new_layers = [layer.copy_empty() for layer in self.layers]
        new_frame = Frame(
            width=self.width,
            height=self.height,
            color_mode=self.color_mode,
            duration=self.duration,
            layers=new_layers,
        )
        new_frame.metadata = self.metadata.copy()
        return new_frame

    # ------------------------------------------------------------------
    # Bulk Operations
    # ------------------------------------------------------------------

    def resize(self, new_width: int, new_height: int, method: str = "nearest") -> None:
        """
        Resize the entire frame (all layers) to the new dimensions.

        This is a destructive operation on pixel data.
        """
        if new_width <= 0 or new_height <= 0:
            raise ValueError("New dimensions must be positive")

        for layer in self.layers:
            layer.resize(new_width, new_height, method=method)

        self.width = new_width
        self.height = new_height

    def clear_all_layers(self, color: Optional[tuple] = None) -> None:
        """Convenience method to clear every layer in the frame."""
        for layer in self.layers:
            layer.clear(color)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the frame (and all its layers) to a JSON-compatible dict.

        This is used by Sprite when saving .pxf files and by the history system.
        """
        return {
            "version": "1.0",
            "width": self.width,
            "height": self.height,
            "color_mode": self.color_mode,
            "duration": self.duration,
            "layers": [layer.to_dict() for layer in self.layers],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Frame":
        """
        Reconstruct a Frame from a serialized dictionary.

        Used when loading .pxf project files.
        """
        layers = [Layer.from_dict(ld) for ld in data.get("layers", [])]

        frame = cls(
            width=data["width"],
            height=data["height"],
            color_mode=data.get("color_mode", "RGBA"),
            duration=data.get("duration", 100),
            layers=layers if layers else None,  # let constructor create default if empty
        )

        frame.metadata = data.get("metadata", {}).copy()
        return frame

    # ------------------------------------------------------------------
    # Convenience & Debugging
    # ------------------------------------------------------------------

    def get_layer_names(self) -> List[str]:
        """Return a list of all layer names in stack order (bottom to top)."""
        return [layer.name for layer in self.layers]

    def __repr__(self) -> str:
        return (
            f"Frame({self.width}x{self.height}, "
            f"layers={self.layer_count}, duration={self.duration}ms)"
        )

    def __len__(self) -> int:
        """Allow `len(frame)` to return the number of layers."""
        return len(self.layers)

    def __getitem__(self, index: int) -> Layer:
        """Allow direct indexing: `layer = frame[0]`."""
        return self.layers[index]
