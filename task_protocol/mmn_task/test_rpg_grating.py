"""Validate native RPG file layout and fractional-angle pixels on tiny frames."""

import math
import struct

import numpy as np
import pytest


@pytest.mark.parametrize("angle", [22.5, 45, 67.5, 90, 112.5, 135, 157.5, 180])
def test_native_file_keeps_exact_angle_and_temporal_phase(tmp_path, angle):
    from task_protocol.mmn_task.rpg_grating import write_rpg_grating

    options = {
        "duration": 0.5,
        "angle": angle,
        "spac_freq": 0.05,
        "temp_freq": 2.0,
        "resolution": (80, 40),
        "screen_width_degrees": 80.0,
        "refresh_rate_hz": 60,
    }
    path = tmp_path / "grating.dat"
    write_rpg_grating(path, options)
    data = path.read_bytes()
    # Eight native uint16 fields, followed by 30 row-major RGB565 frames.
    assert struct.unpack("<8H", data[:16]) == (30, 0, 2, 60, 30, 80, 40, 0)
    frames = np.frombuffer(data[16:], dtype="<u2").reshape(30, 40, 80)
    y, x = np.indices((40, 80))
    radians = math.radians(180 - angle)
    projection = x * math.cos(radians) + y * math.sin(radians)
    for frame_number in (0, 1, 29):
        phase = 2 * math.pi * (0.05 * projection + 2.0 * frame_number / 60)
        gray = (127 * np.sin(phase) + 127).astype(np.uint16)
        expected = ((31 * (gray + 4) // 255) << 11) | ((63 * (gray + 2) // 255) << 5) | (31 * (gray + 4) // 255)
        np.testing.assert_array_equal(frames[frame_number], expected)
    if angle % 1:
        truncated = dict(options, angle=int(angle))
        other_path = tmp_path / "truncated.dat"
        write_rpg_grating(other_path, truncated)
        assert data != other_path.read_bytes()


@pytest.mark.parametrize("angle", [22.5, 45, 67.5, 90, 112.5, 135, 157.5, 180])
def test_black_patch_is_baked_into_bottom_left_of_every_frame(tmp_path, angle):
    from task_protocol.mmn_task.rpg_grating import write_rpg_grating

    options = dict(
        duration=0.5, angle=angle, spac_freq=0.05, temp_freq=2.0,
        resolution=(80, 40), screen_width_degrees=80.0, refresh_rate_hz=60,
    )
    plain_path = tmp_path / 'plain.dat'
    patched_path = tmp_path / 'patched.dat'
    write_rpg_grating(plain_path, options)
    write_rpg_grating(patched_path, dict(options, photodiode_rect_px=(0, 34, 8, 6)))
    plain = np.frombuffer(plain_path.read_bytes()[16:], dtype='<u2').reshape(30, 40, 80)
    patched = np.frombuffer(patched_path.read_bytes()[16:], dtype='<u2').reshape(30, 40, 80)
    assert np.all(patched[:, 34:, :8] == 0)
    mask = np.ones((40, 80), dtype=bool)
    mask[34:, :8] = False
    np.testing.assert_array_equal(patched[:, mask], plain[:, mask])


def test_gray_file_contains_white_patch_only_at_bottom_left(tmp_path):
    from task_protocol.mmn_task.rpg_grating import write_rpg_gray

    path = tmp_path / 'gray.dat'
    write_rpg_gray(path, dict(
        resolution=(80, 40), refresh_rate_hz=60, gray_level=40,
        photodiode_rect_px=(0, 34, 8, 6),
    ))
    data = path.read_bytes()
    # One stored frame repeated for two refreshes, then left on screen.
    assert struct.unpack('<8H', data[:16]) == (1, 0, 0, 60, 2, 80, 40, 0)
    pixels = np.frombuffer(data[16:], dtype='<u2').reshape(40, 80)
    assert np.all(pixels[34:, :8] == 0xffff)
    assert np.all(pixels[:34, :] == 0x2945)  # RGB565 encoding of gray level 40.
    assert np.all(pixels[34:, 8:] == 0x2945)
