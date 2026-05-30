"""
ui/panels/layers_panel.py

The Layers panel for PixelAnimationLab.

Features implemented:
- Layer list with name and visibility toggle
- Click to select layers
- "New Layer" button at the bottom
- Per-layer delete button (X)
- Drag reordering using a textured grip tab on the right side of each row

Still using mock data until the real Sprite/Frame/Layer model is connected.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import pygame

from ui.panels.base_panel import Panel


class LayersPanel(Panel):
    """
    Right-hand panel showing the layer stack with basic editing capabilities.
    """

    def __init__(self):
        super().__init__(name="Layers")

        # Mock layer data
        self.layers: List[dict] = [
            {"name": "Background", "visible": True},
            {"name": "Character", "visible": True},
            {"name": "Effects", "visible": False},
            {"name": "UI", "visible": True},
        ]
        self.selected_index: int = 1

        # Layout constants
        self._header_height = 28
        self._item_height = 24
        self._padding = 6

        # Drag state
        self._dragging_index: Optional[int] = None
        self._drag_start_y: int = 0
        self._drag_current_y: int = 0

        # Rename state
        self._renaming_index: Optional[int] = None
        self._rename_text: str = ""
        self._rename_cursor: int = 0
        self._rename_select_start: int = 0
        self._rename_select_end: int = 0
        self._rename_blink_timer: int = 0

        # Double-click detection
        self._last_click_time: int = 0
        self._last_click_row: int = -1

        # New layer counter for unique names
        self._next_layer_number = 5

    def update(self, dt: float) -> None:
        """Per-frame logic (cursor blink, etc.)."""
        if self._renaming_index is not None:
            self._rename_blink_timer = (self._rename_blink_timer + dt * 1000) % 1000

    # ------------------------------------------------------------------
    # Event Handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible or not self.enabled:
            return False

        mouse_pos = pygame.mouse.get_pos()
        inside_panel = self.rect.collidepoint(mouse_pos)

        # --- Rename mode handling (takes priority) ---
        if self._renaming_index is not None:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self._commit_rename()
                    return True
                elif event.key == pygame.K_ESCAPE:
                    self._cancel_rename()
                    return True
                elif event.key == pygame.K_BACKSPACE:
                    if self._rename_select_start != self._rename_select_end:
                        # delete selection
                        start = min(self._rename_select_start, self._rename_select_end)
                        end = max(self._rename_select_start, self._rename_select_end)
                        self._rename_text = self._rename_text[:start] + self._rename_text[end:]
                        self._rename_cursor = start
                    elif self._rename_cursor > 0:
                        self._rename_text = (
                            self._rename_text[: self._rename_cursor - 1]
                            + self._rename_text[self._rename_cursor :]
                        )
                        self._rename_cursor -= 1
                    self._rename_select_start = self._rename_select_end = self._rename_cursor
                    return True

            elif event.type == pygame.TEXTINPUT:
                # Replace selection or insert at cursor
                start = min(self._rename_select_start, self._rename_select_end)
                end = max(self._rename_select_start, self._rename_select_end)
                self._rename_text = self._rename_text[:start] + event.text + self._rename_text[end:]
                self._rename_cursor = start + len(event.text)
                self._rename_select_start = self._rename_select_end = self._rename_cursor
                return True

            # If click happened, commit rename (even outside)
            if event.type == pygame.MOUSEBUTTONDOWN:
                self._commit_rename()
                return True

            return False  # swallow other events while renaming

        # --- Normal mode ---
        if not inside_panel:
            if self._dragging_index is not None:
                self._finish_drag(mouse_pos[1])
            return False

        rel_y = mouse_pos[1] - self.rect.y - self._header_height
        row_index = rel_y // self._item_height if rel_y >= 0 else -1

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            current_time = pygame.time.get_ticks()

            if self._hit_new_layer_button(mouse_pos):
                self._add_new_layer()
                return True

            if 0 <= row_index < len(self.layers):
                local_x = mouse_pos[0] - self.rect.x

                # Visibility toggle
                if local_x < 24:
                    self.layers[row_index]["visible"] = not self.layers[row_index]["visible"]
                    return True

                # Delete button
                if self.rect.width - 44 < local_x < self.rect.width - 24:
                    self._delete_layer(row_index)
                    return True

                # Grip tab → start drag reorder
                if self.rect.width - 22 < local_x:
                    self._start_drag(row_index, mouse_pos[1])
                    return True

                # Name area → selection + possible double-click rename
                is_double_click = (
                    row_index == self._last_click_row
                    and current_time - self._last_click_time < 450
                )
                self._last_click_time = current_time
                self._last_click_row = row_index

                self._select_layer(row_index)

                if is_double_click:
                    self._start_renaming(row_index)

                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging_index is not None:
                self._finish_drag(mouse_pos[1])
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self._dragging_index is not None:
                self._drag_current_y = mouse_pos[1]
                return True

        return False

    # ------------------------------------------------------------------
    # Drag & Drop Reordering
    # ------------------------------------------------------------------

    def _start_drag(self, index: int, mouse_y: int):
        self._dragging_index = index
        self._drag_start_y = mouse_y
        self._drag_current_y = mouse_y

    def _finish_drag(self, mouse_y: int):
        if self._dragging_index is None:
            return

        # Calculate drop index
        header_bottom = self.rect.y + self._header_height
        rel_y = mouse_y - header_bottom
        drop_index = max(0, min(len(self.layers) - 1, rel_y // self._item_height))

        # Move the layer
        if drop_index != self._dragging_index:
            layer = self.layers.pop(self._dragging_index)
            self.layers.insert(drop_index, layer)
            self.selected_index = drop_index

        self._dragging_index = None

    # ------------------------------------------------------------------
    # Renaming
    # ------------------------------------------------------------------

    def _start_renaming(self, index: int):
        if not (0 <= index < len(self.layers)):
            return
        self._renaming_index = index
        self._rename_text = self.layers[index]["name"]
        self._rename_select_start = 0
        self._rename_select_end = len(self._rename_text)
        self._rename_cursor = len(self._rename_text)
        self._rename_blink_timer = 0
        self._select_layer(index)  # also select it visually

    def _commit_rename(self):
        if self._renaming_index is None:
            return
        new_name = self._rename_text.strip()
        if new_name:  # don't allow empty names
            self.layers[self._renaming_index]["name"] = new_name
        self._cancel_rename()

    def _cancel_rename(self):
        self._renaming_index = None
        self._rename_text = ""
        self._rename_select_start = 0
        self._rename_select_end = 0
        self._rename_cursor = 0

    # ------------------------------------------------------------------
    # Layer Operations (still mock)
    # ------------------------------------------------------------------

    def _add_new_layer(self):
        new_name = f"Layer {self._next_layer_number}"
        self._next_layer_number += 1
        self.layers.append({"name": new_name, "visible": True})

        # Select the new layer
        self._select_layer(len(self.layers) - 1)

    def _delete_layer(self, index: int):
        if len(self.layers) <= 1:
            return  # Always keep at least one layer

        was_selected = (index == self.selected_index)
        del self.layers[index]

        if was_selected:
            self.selected_index = min(self.selected_index, len(self.layers) - 1)
        elif self.selected_index > index:
            self.selected_index -= 1

    def _select_layer(self, index: int):
        for i, layer in enumerate(self.layers):
            layer["selected"] = (i == index)
        self.selected_index = index

    # ------------------------------------------------------------------
    # Hit Testing Helpers
    # ------------------------------------------------------------------

    def _hit_new_layer_button(self, mouse_pos: Tuple[int, int]) -> bool:
        button_rect = self._get_new_layer_button_rect()
        return button_rect.collidepoint(mouse_pos)

    def _get_new_layer_button_rect(self) -> pygame.Rect:
        btn_height = 20
        return pygame.Rect(
            self.rect.x + 8,
            self.rect.bottom - btn_height - 6,
            self.rect.width - 16,
            btn_height
        )

    def _get_row_rect(self, index: int) -> pygame.Rect:
        y = self.rect.y + self._header_height + index * self._item_height
        return pygame.Rect(self.rect.x, y, self.rect.width, self._item_height)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        # Panel background
        pygame.draw.rect(surface, (45, 45, 50), self.rect)
        pygame.draw.rect(surface, (70, 70, 75), self.rect, 1)

        # Header
        font_header = pygame.font.SysFont("Arial", 14, bold=True)
        header = font_header.render(self.name, True, (100, 160, 220))
        surface.blit(header, (self.rect.x + 10, self.rect.y + 8))

        # Layer rows
        font_item = pygame.font.SysFont("Arial", 12)
        y = self.rect.y + self._header_height

        for i, layer in enumerate(self.layers):
            row_rect = pygame.Rect(self.rect.x + 4, y, self.rect.width - 8, self._item_height - 2)

            # Selection highlight
            if layer.get("selected", False):
                pygame.draw.rect(surface, (70, 90, 120), row_rect, border_radius=2)

            # Visibility toggle
            vis = "●" if layer["visible"] else "○"
            vis_color = (160, 220, 160) if layer["visible"] else (110, 110, 110)
            vis_surf = font_item.render(vis, True, vis_color)
            surface.blit(vis_surf, (self.rect.x + 10, y + 4))

            # Layer name (or text input when renaming)
            name_x = self.rect.x + 28
            name_y = y + 4

            if i == self._renaming_index:
                # Draw text input box with selection and cursor
                self._draw_rename_field(surface, name_x, name_y, row_rect.width - 60)
            else:
                name_color = (245, 245, 250) if layer.get("selected") else (200, 200, 205)
                name_surf = font_item.render(layer["name"], True, name_color)
                surface.blit(name_surf, (name_x, name_y))

            # Textured grip tab (right side)
            grip_x = self.rect.right - 22
            self._draw_grip(surface, grip_x, y + 6, 12, 10)

            # Delete button (X)
            del_x = self.rect.right - 40
            del_surf = font_item.render("×", True, (200, 120, 120))
            surface.blit(del_surf, (del_x, y + 3))

            y += self._item_height

        # New Layer button
        btn_rect = self._get_new_layer_button_rect()
        pygame.draw.rect(surface, (60, 80, 110), btn_rect, border_radius=3)
        pygame.draw.rect(surface, (90, 110, 140), btn_rect, 1, border_radius=3)
        btn_font = pygame.font.SysFont("Arial", 11)
        btn_text = btn_font.render("+ New Layer", True, (220, 230, 245))
        btn_text_rect = btn_text.get_rect(center=btn_rect.center)
        surface.blit(btn_text, btn_text_rect)

        # Draw dragged layer ghost + insertion line
        if self._dragging_index is not None:
            self._draw_drag_ghost_and_insertion(surface)

    def _draw_grip(self, surface, x: int, y: int, w: int, h: int):
        """Draw a simple textured grip handle."""
        color = (140, 140, 145)
        for i in range(3):
            yy = y + i * 3 + 1
            pygame.draw.line(surface, color, (x, yy), (x + w, yy), 1)

    def _draw_drag_ghost_and_insertion(self, surface: pygame.Surface):
        """Draw a ghost of the dragged layer and an insertion indicator."""
        if self._dragging_index is None:
            return

        # Simple insertion line (more advanced ghost can be added later)
        mouse_y = self._drag_current_y
        header_bottom = self.rect.y + self._header_height
        rel_y = mouse_y - header_bottom
        insert_index = max(0, min(len(self.layers), rel_y // self._item_height))

        insert_y = self.rect.y + self._header_height + insert_index * self._item_height

        # Draw insertion line
        pygame.draw.line(
            surface,
            (100, 160, 220),
            (self.rect.x + 8, insert_y),
            (self.rect.right - 8, insert_y),
            2
        )

    def _draw_rename_field(self, surface: pygame.Surface, x: int, y: int, max_width: int):
        """Draw the in-place rename text input with selection highlight and blinking cursor."""
        text = self._rename_text
        font = pygame.font.SysFont("Arial", 12)

        # Input background
        input_rect = pygame.Rect(x - 2, y - 1, min(max_width, 140), self._item_height - 4)
        pygame.draw.rect(surface, (240, 240, 245), input_rect)
        pygame.draw.rect(surface, (80, 120, 200), input_rect, 1)

        # Selection highlight
        if self._rename_select_start != self._rename_select_end:
            start = min(self._rename_select_start, self._rename_select_end)
            end = max(self._rename_select_start, self._rename_select_end)
            prefix = text[:start]
            selected = text[start:end]

            prefix_width = font.size(prefix)[0]
            sel_width = font.size(selected)[0]

            sel_rect = pygame.Rect(
                x + prefix_width,
                y,
                min(sel_width, input_rect.width - prefix_width),
                font.get_height() - 2
            )
            pygame.draw.rect(surface, (100, 140, 220), sel_rect)

        # Text
        text_surf = font.render(text, True, (30, 30, 35))
        surface.blit(text_surf, (x, y))

        # Blinking cursor
        if self._rename_blink_timer < 500:
            cursor_x = x + font.size(text[: self._rename_cursor])[0]
            pygame.draw.line(
                surface,
                (30, 30, 35),
                (cursor_x, y + 1),
                (cursor_x, y + font.get_height() - 3),
                1
            )
