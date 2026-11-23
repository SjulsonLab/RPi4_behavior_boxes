"""Write sine gratings in the native RGB565 format consumed by rpg.Screen.

The upstream C generator casts angles to integers. This adapter keeps fractional
angles and writes the same eight-uint16 header and row-major pixel frames:
https://github.com/SjulsonLab/rpg/blob/master/rpg/_rpigratings.c
"""

import math
import struct
from pathlib import Path
from typing import Any, Dict


def write_rpg_grating(path: Path, options: Dict[str, Any]) -> None:
    """Write one precomputed movie to path and return None.

    Required options: duration (seconds), angle (degrees, RPG propagation
    convention), spac_freq (cycles/visual degree), temp_freq (Hz), resolution
    ((width, height) integer pixels), screen_width_degrees (visual degrees),
    and refresh_rate_hz (integer Hz, matching the monitor). Frames have shape
    (height, width), packed as little-endian RGB565, at full sine contrast.
    Optional photodiode_rect_px is (x, y, width, height) pixels from the top-left
    origin; that region is black in every frame, including the first frame.
    Only one frame is generated at a time to limit temporary memory usage.
    """
    import numpy as np

    width, height = options['resolution']
    fps = options['refresh_rate_hz']
    duration = options['duration']
    angle = options['angle']
    spatial_frequency = options['spac_freq']
    temporal_frequency = options['temp_freq']
    screen_width_degrees = options['screen_width_degrees']
    for value in (duration, spatial_frequency, temporal_frequency, screen_width_degrees):
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Grating duration, frequencies, and screen visual angle must be positive and finite")
    if not math.isfinite(angle):
        raise ValueError("Grating angle must be finite")
    if any(not isinstance(value, int) or not 1 <= value <= 65535 for value in (width, height, fps)):
        raise ValueError("Grating width, height, and refresh rate must be integers from 1 to 65535")
    frame_count = round(duration * fps)
    if not 2 <= frame_count <= 65535:
        raise ValueError("Grating duration must correspond to 2–65535 display frames")

    # RPG's header stores historical integer frequency fields. Exact values
    # remain in the JSON metadata; playback uses the precomputed frames.
    header = struct.pack(
        '<8H', frame_count, int(spatial_frequency), int(temporal_frequency),
        fps, frame_count, width, height, 0,
    )
    radians = math.radians(180 - angle)
    x = np.arange(width, dtype=np.float64)[None, :]
    y = np.arange(height, dtype=np.float64)[:, None]
    projection = x * math.cos(radians) + y * math.sin(radians)
    cycles_per_pixel = spatial_frequency * screen_width_degrees / width
    spatial_cycles = cycles_per_pixel * projection
    with Path(path).open('wb') as output:
        output.write(header)
        for frame_number in range(frame_count):
            phase = 2 * math.pi * (
                spatial_cycles + temporal_frequency * frame_number / fps
            )
            gray = (127 * np.sin(phase) + 127).astype(np.uint16)
            pixels = _gray_to_rgb565(gray)
            if options.get('photodiode_rect_px') is not None:
                x0, y0, patch_width, patch_height = options['photodiode_rect_px']
                pixels[y0:y0 + patch_height, x0:x0 + patch_width] = 0
            output.write(pixels.astype('<u2', copy=False).tobytes())


def write_rpg_gray(path: Path, options: Dict[str, Any]) -> None:
    """Write a static gray frame with a white synchronization patch; return None.

    options specifies resolution ((width, height) integer pixels),
    refresh_rate_hz (integer Hz), gray_level (integer 0–255), and optional
    photodiode_rect_px ((x, y, width, height) pixels, top-left origin).
    One row-major RGB565 frame is stored and held for two display refreshes;
    RPG needs two refreshes to compute its interframe timing statistics.
    The final frame remains visible until the next display operation.
    """
    import numpy as np

    width, height = options['resolution']
    fps = options['refresh_rate_hz']
    gray_level = options['gray_level']
    if any(not isinstance(n, int) or not 1 <= n <= 65535 for n in (width, height, fps)):
        raise ValueError("Gray-frame dimensions and refresh rate must be integers from 1 to 65535")
    if not isinstance(gray_level, int) or not 0 <= gray_level <= 255:
        raise ValueError("gray_level must be an integer from 0 to 255")
    pixels = np.full((height, width), _gray_to_rgb565(gray_level), dtype='<u2')
    if options.get('photodiode_rect_px') is not None:
        x0, y0, patch_width, patch_height = options['photodiode_rect_px']
        pixels[y0:y0 + patch_height, x0:x0 + patch_width] = 0xffff
    with Path(path).open('wb') as output:
        output.write(struct.pack('<8H', 1, 0, 0, fps, 2, width, height, 0))
        output.write(pixels.tobytes())


def _gray_to_rgb565(gray):
    """Pack a 0–255 integer or uint16 grayscale array into matching RGB565 values."""
    red_blue = 31 * (gray + 4) // 255
    green = 63 * (gray + 2) // 255
    return (red_blue << 11) | (green << 5) | red_blue
