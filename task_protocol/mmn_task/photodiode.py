"""Shared placement for the visual stimulus synchronization patch."""

from typing import Tuple


def bottom_left_patch_rect(
    resolution: Tuple[int, int], size_px: Tuple[int, int]
) -> Tuple[int, int, int, int]:
    """Return (x, y, width, height) pixels for a bottom-left patch.

    resolution and size_px are (width, height) positive integer pixel pairs.
    Coordinates use the display's top-left origin; the patch must fit entirely
    inside the display. Invalid sizes raise ValueError.
    """
    if len(size_px) != 2 or any(not isinstance(n, int) or n <= 0 for n in size_px):
        raise ValueError("photodiode_patch_size_px must contain positive integer width and height")
    width, height = resolution
    patch_width, patch_height = size_px
    if patch_width > width or patch_height > height:
        raise ValueError("photodiode_patch_size_px must fit within the display resolution")
    return 0, height - patch_height, patch_width, patch_height
