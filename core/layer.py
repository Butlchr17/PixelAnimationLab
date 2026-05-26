"""
core/layer.py - The fundamental raster building block for PixelAnimationLab.

This module defines the Layer class, which is the atomic unit of image data
in the application. Every Frame in a Sprite contains one or more Layers.

Design Philosophy (aligned with Aseprite-like editors and the original project goals):

1. **Separation of Concerns**
   - A Layer owns its pixel data and its own presentation properties.
   - It does NOT know about Frames, Sprites, or the timeline.
   - This makes Layers reusable, testable, and easy to extend (e.g. GroupLayer,
     AdjustmentLayer, TilemapLayer in the future).

2. **Performance-First Pixel Storage**
   - Uses numpy.ndarray with shape (height, width, channels) and dtype=uint8.
   - This gives us C-speed operations, easy integration with pygame and Pillow,
   - and a natural path to shaders / compute later.

3. **Animation-Friendly Semantics**
   - `copy_empty()` is a first-class operation. When you add a new animation frame,
     you usually want the same layer *structure* (names, visibility, opacity) but
     fresh transparent pixel data. This method exists specifically for that workflow.

4. **Extensibility by Design**
   - `blend_mode` is a string so we can add "multiply", "screen", "overlay", etc.
     without changing the class signature.
   - `metadata` dict allows plugins and future features to attach arbitrary data
     (e.g. tile palette indices, reference image paths, AI generation seeds).
   - Locked / visible / opacity are explicit so the UI and history system can
     reason about them cleanly.

5. **Serialization for .pxf Format**
   - Every Layer can round-trip through a JSON-compatible dictionary.
   - Pixel data is stored as base64-encoded raw bytes for compactness while
     remaining human-inspectable in a pinch.

6. **Future-Proofing**
   - We deliberately avoid baking in compositing logic here. Compositing belongs
     in a Renderer or Frame class so we can later support layer groups, clipping
     masks, and layer effects without touching this file.
"""

from __future__ import annotations

import base64
from typing import Any, Dict, Optional, Tuple

import numpy as np


class Layer:
    """
    A single raster layer containing pixel data and layer-specific properties.

    This is the core data structure for all drawing, animation, and export
    operations. Think of it as the equivalent of a layer in Aseprite, Photoshop,
    or Krita, but optimized for pixel-art workflows and animation.

    Attributes:
        width (int): Width of the layer in pixels.
        height (int): Height of the layer in pixels.
        name (str): Human-readable name shown in the layer stack.
        visible (bool): Whether the layer is currently rendered.
        opacity (float): Master opacity multiplier in range [0.0, 1.0].
        locked (bool): When True, the layer should be protected from editing tools.
        blend_mode (str): How this layer composites over layers below it.
                          Currently only "normal" is implemented; the string
                          field exists for future expansion.
        color_mode (str): "RGBA" (default) or "RGB". Determines channel count.
        pixels (np.ndarray): The actual image data.
                             Shape is (height, width, channels).
                             dtype is always np.uint8.
        metadata (Dict[str, Any]): Extensibility bag for plugins and future
                                   features (e.g. tile data, reference info).
    """

    VALID_COLOR_MODES = ("RGBA", "RGB")
    VALID_BLEND_MODES = ("normal",)  # Extend this list as new modes are added

    def __init__(
        self,
        width: int,
        height: int,
        name: str = "Layer",
        visible: bool = True,
        opacity: float = 1.0,
        color_mode: str = "RGBA",
        locked: bool = False,
        blend_mode: str = "normal",
    ) -> None:
        """
        Create a new Layer with transparent (zeroed) pixel data.

        Args:
            width: Pixel width. Must be positive.
            height: Pixel height. Must be positive.
            name: Display name for the layer stack UI.
            visible: Initial visibility state.
            opacity: Initial opacity in [0.0, 1.0].
            color_mode: "RGBA" or "RGB".
            locked: Whether the layer starts locked.
            blend_mode: Compositing mode (currently only "normal").

        Raises:
            ValueError: If dimensions are invalid or color_mode/blend_mode
                        are not supported.
        """
        if width <= 0 or height <= 0:
            raise ValueError(f"Layer dimensions must be positive, got {width}x{height}")

        if color_mode not in self.VALID_COLOR_MODES:
            raise ValueError(f"Unsupported color_mode '{color_mode}'. "
                             f"Valid options: {self.VALID_COLOR_MODES}")

        if blend_mode not in self.VALID_BLEND_MODES:
            raise ValueError(f"Unsupported blend_mode '{blend_mode}'. "
                             f"Valid options: {self.VALID_BLEND_MODES}")

        self.width = int(width)
        self.height = int(height)
        self.name = str(name)
        self.visible = bool(visible)
        self.opacity = max(0.0, min(1.0, float(opacity)))
        self.color_mode = color_mode
        self.locked = bool(locked)
        self.blend_mode = blend_mode

        # Extensibility hook. Future features (tilemaps, reference layers,
        # procedural generators, etc.) can store structured data here without
        # requiring changes to the core class or the serialization format.
        self.metadata: Dict[str, Any] = {}

        # === Pixel Storage ===
        # We use (H, W, C) layout because it is the most natural for numpy
        # indexing (layer[y, x]) and matches how most image libraries think.
        channels = 4 if color_mode == "RGBA" else 3
        self.pixels: np.ndarray = np.zeros(
            (self.height, self.width, channels), dtype=np.uint8
        )

        # Internal channel count cached for fast access and serialization.
        self._channels = channels

    # ------------------------------------------------------------------
    # Properties (with light validation)
    # ------------------------------------------------------------------

    @property
    def channels(self) -> int:
        """Number of color channels (3 for RGB, 4 for RGBA)."""
        return self._channels

    @property
    def shape(self) -> Tuple[int, int, int]:
        """Convenience property returning (height, width, channels)."""
        return (self.height, self.width, self._channels)

    @property
    def is_transparent(self) -> bool:
        """True if the layer contains only fully transparent pixels."""
        if self.color_mode == "RGBA":
            return bool(np.all(self.pixels[:, :, 3] == 0))
        return False  # RGB layers have no alpha concept

    # ------------------------------------------------------------------
    # Core Creation & Duplication (Critical for Animation Workflow)
    # ------------------------------------------------------------------

    def copy_empty(self) -> "Layer":
        """
        Create a new Layer with identical metadata but empty (transparent) pixels.

        This is one of the most important methods for animation work.
        When the user inserts a new frame, Sprite typically wants to duplicate
        the *layer stack structure* (same names, visibility, opacity, locked
        state, blend modes) while giving each new layer fresh transparent
        pixel data.

        Using copy_empty() is both faster and semantically clearer than
        doing a full copy and then clearing the pixels.

        Returns:
            A new Layer instance with the same properties but zeroed pixels.
        """
        new_layer = Layer(
            width=self.width,
            height=self.height,
            name=self.name,
            visible=self.visible,
            opacity=self.opacity,
            color_mode=self.color_mode,
            locked=self.locked,
            blend_mode=self.blend_mode,
        )
        # Preserve any plugin / future metadata
        new_layer.metadata = self.metadata.copy()
        return new_layer

    def copy(self) -> "Layer":
        """
        Create a complete deep copy of this layer, including all pixel data.

        Use this when you truly want an independent duplicate (for example,
        when the user explicitly duplicates a layer, or when history needs
        to snapshot the exact previous state for undo).

        Returns:
            A new Layer with identical everything.
        """
        new_layer = self.copy_empty()
        # numpy copy is fast (C-level memcpy under the hood)
        new_layer.pixels = self.pixels.copy()
        return new_layer

    # ------------------------------------------------------------------
    # Basic Pixel Manipulation
    # ------------------------------------------------------------------

    def clear(self, color: Optional[Tuple[int, ...]] = None) -> None:
        """
        Fill the entire layer with a single color.

        Args:
            color: Tuple of channel values (length must match self.channels).
                   If None, clears to transparent black (0,0,0,0) for RGBA
                   or (0,0,0) for RGB.
        """
        if color is None:
            color = (0, 0, 0, 0) if self.color_mode == "RGBA" else (0, 0, 0)

        if len(color) != self._channels:
            raise ValueError(
                f"Color must have {self._channels} components for {self.color_mode}, "
                f"got {len(color)}"
            )

        self.pixels[:] = color

    def fill(self, color: Tuple[int, ...]) -> None:
        """Alias for clear() with an explicit color. More intuitive name in some contexts."""
        self.clear(color)

    def get_pixel(self, x: int, y: int) -> Tuple[int, ...]:
        """
        Return the color at a specific pixel as a tuple.

        Coordinates are in layer-local space (0,0 is top-left).

        Raises:
            IndexError: If coordinates are out of bounds.
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(f"Pixel coordinate ({x}, {y}) out of bounds "
                             f"for layer size {self.width}x{self.height}")
        return tuple(self.pixels[y, x])

    def set_pixel(self, x: int, y: int, color: Tuple[int, ...]) -> None:
        """
        Set the color of a single pixel.

        Args:
            x, y: Layer-local coordinates.
            color: Tuple with correct number of channels.

        Raises:
            IndexError: If coordinates are out of bounds.
            ValueError: If color tuple has wrong length.
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(f"Pixel coordinate ({x}, {y}) out of bounds")

        if len(color) != self._channels:
            raise ValueError(f"Expected {self._channels} channel values, got {len(color)}")

        self.pixels[y, x] = color

    # ------------------------------------------------------------------
    # Bulk Operations (Useful for Tools & Scripts)
    # ------------------------------------------------------------------

    def replace_color(self, old_color: Tuple[int, ...], new_color: Tuple[int, ...]) -> int:
        """
        Replace every occurrence of old_color with new_color.

        Returns:
            Number of pixels that were changed.
        """
        if len(old_color) != self._channels or len(new_color) != self._channels:
            raise ValueError("Color tuples must match layer channel count")

        # Create a boolean mask where all channels match
        mask = np.all(self.pixels == old_color, axis=2)
        count = int(np.sum(mask))
        self.pixels[mask] = new_color
        return count

    # ------------------------------------------------------------------
    # Transformation (Basic but Essential for Pixel Art Workflow)
    # ------------------------------------------------------------------

    def resize(
        self,
        new_width: int,
        new_height: int,
        method: str = "nearest",
    ) -> None:
        """
        Resize the layer's pixel data.

        NOTE: This is a destructive operation on the pixel content. The layer's
        width/height are updated. Callers (usually Sprite or Frame) are
        responsible for updating their own dimensions if they track them.

        Current implementation only supports nearest-neighbor (ideal for
        pixel art). Higher-quality methods can be added later without
        changing the public signature.

        Args:
            new_width: Target width in pixels.
            new_height: Target height in pixels.
            method: Resampling method. Only "nearest" is supported today.
        """
        if new_width <= 0 or new_height <= 0:
            raise ValueError("New dimensions must be positive")

        if method != "nearest":
            raise NotImplementedError(
                f"Resize method '{method}' is not yet implemented. "
                "Only 'nearest' (nearest-neighbor) is supported for pixel-art fidelity."
            )

        if new_width == self.width and new_height == self.height:
            return  # Nothing to do

        # Nearest-neighbor resize using integer indexing
        # We map each destination pixel back to the source
        src_y = (np.arange(new_height) * self.height / new_height).astype(np.int32)
        src_x = (np.arange(new_width) * self.width / new_width).astype(np.int32)

        # Clip just in case of floating point edge cases
        src_y = np.clip(src_y, 0, self.height - 1)
        src_x = np.clip(src_x, 0, self.width - 1)

        # Use advanced indexing to pull the new pixels
        self.pixels = self.pixels[src_y[:, None], src_x[None, :]].copy()

        self.width = new_width
        self.height = new_height

    def flip_horizontal(self) -> None:
        """Mirror the layer left-to-right in place."""
        self.pixels = np.fliplr(self.pixels)

    def flip_vertical(self) -> None:
        """Mirror the layer top-to-bottom in place."""
        self.pixels = np.flipud(self.pixels)

    # ------------------------------------------------------------------
    # Serialization (for .pxf files and undo/redo)
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the entire layer to a JSON-compatible dictionary.

        Pixel data is stored as base64-encoded raw bytes. This is compact,
        lossless, and easy to parse in other tools if needed.

        The format is intentionally versioned lightly via the presence of
        keys so we can evolve it over time without breaking old files.
        """
        # Convert numpy array to raw bytes then base64 for JSON safety
        raw_bytes = self.pixels.tobytes()
        pixels_b64 = base64.b64encode(raw_bytes).decode("ascii")

        return {
            "version": "1.0",
            "name": self.name,
            "visible": self.visible,
            "opacity": self.opacity,
            "locked": self.locked,
            "blend_mode": self.blend_mode,
            "color_mode": self.color_mode,
            "width": self.width,
            "height": self.height,
            "pixels_b64": pixels_b64,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Layer":
        """
        Reconstruct a Layer from a dictionary produced by to_dict().

        This is the primary deserialization path used when loading .pxf files
        and when restoring history snapshots.
        """
        # Create the shell with correct dimensions and properties
        layer = cls(
            width=data["width"],
            height=data["height"],
            name=data.get("name", "Layer"),
            visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0),
            color_mode=data.get("color_mode", "RGBA"),
            locked=data.get("locked", False),
            blend_mode=data.get("blend_mode", "normal"),
        )

        # Restore pixel data if present
        if "pixels_b64" in data and data["pixels_b64"]:
            raw = base64.b64decode(data["pixels_b64"])
            expected_shape = (layer.height, layer.width, layer.channels)
            layer.pixels = np.frombuffer(raw, dtype=np.uint8).reshape(expected_shape)

        # Restore extensibility data
        layer.metadata = data.get("metadata", {}).copy()

        return layer

    # ------------------------------------------------------------------
    # Convenience / Interoperability
    # ------------------------------------------------------------------

    def to_rgba_array(self) -> np.ndarray:
        """
        Return a copy of the pixel data as RGBA, regardless of the layer's
        native color mode.

        RGB layers are promoted by adding a fully-opaque alpha channel.
        This is extremely useful for the rendering pipeline so it can always
        work in a consistent 4-channel space.
        """
        if self.color_mode == "RGBA":
            return self.pixels.copy()

        # RGB → RGBA by appending 255 alpha
        rgba = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        rgba[:, :, :3] = self.pixels
        rgba[:, :, 3] = 255
        return rgba

    def __repr__(self) -> str:
        return (
            f"Layer(name={self.name!r}, size={self.width}x{self.height}, "
            f"visible={self.visible}, opacity={self.opacity:.2f}, "
            f"locked={self.locked}, blend_mode={self.blend_mode!r})"
        )

    def __eq__(self, other: object) -> bool:
        """Two layers are equal if all properties and pixel data match."""
        if not isinstance(other, Layer):
            return NotImplemented
        return (
            self.name == other.name
            and self.visible == other.visible
            and self.opacity == other.opacity
            and self.locked == other.locked
            and self.blend_mode == other.blend_mode
            and self.color_mode == other.color_mode
            and self.width == other.width
            and self.height == other.height
            and np.array_equal(self.pixels, other.pixels)
            and self.metadata == other.metadata
        )


# -----------------------------------------------------------------------------
# Module-level helper (useful for tests and tools)
# -----------------------------------------------------------------------------

def create_filled_layer(
    width: int,
    height: int,
    color: Tuple[int, ...],
    name: str = "Filled Layer",
    **kwargs: Any,
) -> Layer:
    """
    Factory helper that creates a layer already filled with a solid color.

    Example:
        bg = create_filled_layer(32, 32, (40, 40, 60, 255), name="Background")
    """
    layer = Layer(width, height, name=name, **kwargs)
    layer.fill(color)
    return layer
