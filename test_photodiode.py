import os
import struct

import photodiode
from photodiode import (
    PHOTODIODE_OFF_RAW_FRAMES,
    PHOTODIODE_SIZE_PX,
    load_photodiode_off_raw,
    patched_grating_path,
    read_grating_info,
    write_photodiode_off_rgb_frame,
)


def _write_fake_rgb565_grating(path, width=16, height=12, frames=2):
    """Write a minimal fake RPG RGB565 grating file for tests.

    Inputs
    ------
    path : str
        Output file path.
    width : int, pixels
        Frame width.
    height : int, pixels
        Frame height.
    frames : int, frames
        Number of frames per cycle and total displayed frames.

    Returns
    -------
    None
        Writes row-major frame data with shape ``(frames, height, width)`` and
        16-bit RGB565 pixel values.
    """
    header = struct.pack("<8H", frames, 1, 1, 60, frames, width, height, 0)
    frame = struct.pack("<H", 0) * (width * height)
    with open(path, "wb") as handle:
        handle.write(header)
        for _ in range(frames):
            handle.write(frame)


class FakeScreen:
    """Small RPG Screen stand-in for testing raw loading.

    Inputs
    ------
    colormode : int
        RPG screen color mode. ``0`` means RGB565 and ``2`` means RGB888.

    Attributes
    ----------
    loaded_raw_path : str or None
        Most recent path passed to ``load_raw``.
    """

    def __init__(self, colormode=0):
        self.colormode = colormode
        self.loaded_raw_path = None

    def load_raw(self, path):
        """Record and return the requested raw path.

        Inputs
        ------
        path : str
            Raw file path.

        Returns
        -------
        str
            Same raw file path. No physical units or array shapes apply.
        """
        self.loaded_raw_path = path
        return path


class FakeRpgModule:
    """Small RPG module stand-in for testing raw conversion arguments."""

    def __init__(self):
        self.convert_raw_calls = []

    def convert_raw(self, input_path, output_path, n_frames, width, height, refreshes_per_frame, colormode):
        """Record conversion arguments and create the expected output file.

        Inputs
        ------
        input_path : str
            Path to row-major RGB888 bytes with shape
            ``(n_frames, height, width, 3)``.
        output_path : str
            Path where a converted RPG raw file should be written.
        n_frames : int, frames
            Number of frames in the RGB input.
        width : int, pixels
            Frame width.
        height : int, pixels
            Frame height.
        refreshes_per_frame : int, monitor refreshes/frame
            Number of display refreshes per frame.
        colormode : int, bits/pixel
            RPG conversion color mode, 16 or 24.

        Returns
        -------
        None
            Writes a tiny placeholder output file and stores all arguments.
        """
        self.convert_raw_calls.append(
            (input_path, output_path, n_frames, width, height, refreshes_per_frame, colormode)
        )
        with open(output_path, "wb") as handle:
            handle.write(b"fake raw")


def _read_bytes(path):
    """Return all bytes from a file path.

    Inputs
    ------
    path : str
        File path.

    Returns
    -------
    bytes
        File contents. No physical units or array shapes apply.
    """
    with open(path, "rb") as handle:
        return handle.read()


def test_read_grating_info_detects_rgb565_file(tmp_path):
    grating_path = tmp_path / "test_grating.dat"
    _write_fake_rgb565_grating(str(grating_path))

    info = read_grating_info(str(grating_path))

    assert info["frames_per_cycle"] == 2
    assert info["width"] == 16
    assert info["height"] == 12
    assert info["pixel_size"] == 2


def test_patched_grating_path_adds_top_right_white_square(tmp_path):
    width = 16
    height = 12
    grating_path = tmp_path / "test_grating.dat"
    _write_fake_rgb565_grating(str(grating_path), width=width, height=height)

    patched_path = patched_grating_path(str(grating_path))
    data = _read_bytes(patched_path)

    header_size = struct.calcsize("<8H")
    pixel_size = 2
    patch_size = min(PHOTODIODE_SIZE_PX, width, height)
    left = width - patch_size
    top = 0
    white = struct.pack("<H", 0xFFFF)
    black = struct.pack("<H", 0)

    patched_pixel_offset = header_size + ((top * width + left) * pixel_size)
    unpatched_pixel_offset = header_size + ((height - 1) * width * pixel_size)

    assert os.path.exists(patched_path)
    assert data[patched_pixel_offset : patched_pixel_offset + pixel_size] == white
    assert data[unpatched_pixel_offset : unpatched_pixel_offset + pixel_size] == black


def test_write_photodiode_off_rgb_frame_adds_black_square_on_gray_background(tmp_path):
    width = 16
    height = 12
    gray_level = 127
    frame_path = tmp_path / "off.rgb"

    write_photodiode_off_rgb_frame(str(frame_path), width, height, gray_level)
    data = _read_bytes(str(frame_path))

    patch_size = min(PHOTODIODE_SIZE_PX, width, height)
    left = width - patch_size
    top = 0
    patched_pixel_offset = ((top * width + left) * 3)
    unpatched_pixel_offset = ((height - 1) * width * 3)

    assert data[patched_pixel_offset : patched_pixel_offset + 3] == b"\x00\x00\x00"
    assert data[unpatched_pixel_offset : unpatched_pixel_offset + 3] == bytes([gray_level] * 3)


def test_load_photodiode_off_raw_converts_two_frame_raw(tmp_path, monkeypatch):
    monkeypatch.setattr(photodiode, "_CACHE_DIR", str(tmp_path / "photodiode_cache"))
    screen = FakeScreen(colormode=0)
    rpg_module = FakeRpgModule()

    raw_object = load_photodiode_off_raw(screen, rpg_module, width=16, height=12, gray_level=127)

    assert raw_object == screen.loaded_raw_path
    assert len(rpg_module.convert_raw_calls) == 1

    input_path, output_path, n_frames, width, height, refreshes_per_frame, colormode = rpg_module.convert_raw_calls[0]
    assert input_path.endswith(".rgb")
    assert output_path == screen.loaded_raw_path
    assert n_frames == PHOTODIODE_OFF_RAW_FRAMES
    assert width == 16
    assert height == 12
    assert refreshes_per_frame == 1
    assert colormode == 16

    rgb_bytes = _read_bytes(input_path)
    assert len(rgb_bytes) == PHOTODIODE_OFF_RAW_FRAMES * 16 * 12 * 3
