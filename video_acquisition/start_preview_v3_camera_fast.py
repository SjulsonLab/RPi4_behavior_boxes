#!/usr/bin/env python3

"""Standalone fast preview for the V3 camera.

This script uses the same fast Picamera2 video-configuration path as the
recording script but runs preview only. It can be launched as:

    python start_preview_v3_camera_fast.py

Use ``--display-text`` to enable the cached numeric overlay renderer.
"""

import argparse
import signal
import time

import cv2
import numpy as np
from libcamera import controls
from picamera2 import MappedArray, Picamera2, Preview


DEFAULT_SENSOR_MODE = 0
PREVIEW_SIZE = (1024, 768)
PREVIEW_WINDOW = (100, 0, 1024, 768)
LENS_POSITION = 32.0
WARMUP_SECONDS = 2

FONT = cv2.FONT_HERSHEY_SIMPLEX
SCALE = 0.8
THICKNESS = 2
CHARACTERS = "0123456789.-"


def parse_args(argv=None):
    """Parse command-line flags for the preview script.

    Args:
        argv (list[str] | None): Command-line tokens excluding the executable
            name. Each element is a single CLI token with no physical units.

    Returns:
        argparse.Namespace: Parsed arguments with field ``display_text``
        (bool), where ``True`` enables numeric on-screen overlay text.
    """

    parser = argparse.ArgumentParser(description="Start a fast V3 camera preview.")
    parser.add_argument(
        "--display-text",
        action="store_true",
        help="Overlay cached numeric timing text on the preview frames.",
    )
    return parser.parse_args(argv)


def get_sensor_mode_settings(sensor_mode):
    """Return framerate settings for a supported sensor mode.

    Args:
        sensor_mode (int): Picamera2 sensor mode index. This is a scalar with no
            physical units.

    Returns:
        tuple[int, int]: ``(framerate_hz, frame_duration_us)`` where framerate is
        in frames/second and frame duration is in microseconds.

    Raises:
        ValueError: If the provided sensor mode is not supported by this script.
    """

    if sensor_mode in (0, 1):
        framerate_hz = 50
    elif sensor_mode == 2:
        framerate_hz = 40
    else:
        raise ValueError(f"Unsupported SENSOR_MODE: {sensor_mode}")

    frame_duration_us = int(1e6 / framerate_hz)
    return framerate_hz, frame_duration_us


def build_char_cache():
    """Pre-render glyph bitmaps for fast numeric overlays.

    Args:
        None.

    Returns:
        dict[str, np.ndarray]: Mapping from character to a 2-D uint8 image with
        shape ``(glyph_rows, glyph_cols)`` in luma intensity units ``[0, 255]``.
    """

    char_cache = {}
    for char in CHARACTERS:
        glyph = np.zeros((40, 30), dtype=np.uint8)
        cv2.putText(glyph, char, (2, 30), FONT, SCALE, 255, THICKNESS)
        char_cache[char] = glyph
    return char_cache


CHAR_CACHE = build_char_cache()


def draw_text_fast(frame_y, text, x=10, y=50, char_cache=None):
    """Draw cached glyphs into a single-channel frame buffer.

    Args:
        frame_y (np.ndarray): Preview luma plane with shape ``(rows, cols)`` and
            dtype ``uint8`` in intensity units ``[0, 255]``.
        text (str): ASCII text to render. Only digits, decimal point, and minus
            sign are supported efficiently by the cache.
        x (int): Left pixel coordinate in image-column units.
        y (int): Baseline pixel coordinate in image-row units.
        char_cache (dict[str, np.ndarray] | None): Optional glyph cache where each
            value has shape ``(glyph_rows, glyph_cols)`` and dtype ``uint8``.

    Returns:
        None: ``frame_y`` is modified in place.
    """

    glyph_cache = CHAR_CACHE if char_cache is None else char_cache
    offset = 0
    for char in text:
        if char not in glyph_cache:
            offset += 15
            continue

        glyph = glyph_cache[char]
        height, width = glyph.shape
        y0 = max(y - height, 0)
        y1 = min(y, frame_y.shape[0])
        x0 = x + offset
        x1 = min(x0 + width, frame_y.shape[1])

        if y1 > y0 and x1 > x0:
            glyph_y0 = height - (y1 - y0)
            glyph_x1 = x1 - x0
            frame_y[y0:y1, x0:x1] = np.maximum(
                frame_y[y0:y1, x0:x1],
                glyph[glyph_y0:height, :glyph_x1],
            )
        offset += width + 2


def make_preview_callback(display_text):
    """Create an optional fast overlay callback for preview frames.

    Args:
        display_text (bool): Whether to render the numeric timing overlay on each
            frame. This flag has no physical units.

    Returns:
        collections.abc.Callable | None: Picamera2 request callback when overlay
        text is enabled, otherwise ``None``.
    """

    if not display_text:
        return None

    state = {"first_sensor_timestamp_ns": None}

    def append_preview_text(request):
        """Overlay timing values on the request's main preview stream.

        Args:
            request: Picamera2 request object whose metadata fields include
                ``SensorTimestamp`` in nanoseconds and ``FrameDuration`` in
                microseconds. The request's ``main`` stream is expected to have
                shape ``(rows, cols, channels)`` or ``(rows, cols)``.

        Returns:
            None: The preview frame is modified in place.
        """

        meta = request.get_metadata()
        sensor_timestamp_ns = meta["SensorTimestamp"]
        frame_duration_us = meta.get("FrameDuration", 0)
        unix_timestamp_s = time.time()

        if state["first_sensor_timestamp_ns"] is None:
            state["first_sensor_timestamp_ns"] = sensor_timestamp_ns
        elapsed_s = (
            sensor_timestamp_ns - state["first_sensor_timestamp_ns"]
        ) / 1e9
        fps = (1e6 / frame_duration_us) if frame_duration_us else 0.0

        with MappedArray(request, "main") as mapped:
            frame = mapped.array
            frame_y = frame[:, :, 0] if frame.ndim == 3 else frame
            draw_text_fast(frame_y, f"{elapsed_s:.3f}", x=10, y=45)
            draw_text_fast(frame_y, f"{unix_timestamp_s:.6f}", x=10, y=90)
            draw_text_fast(frame_y, f"{fps:.1f}", x=10, y=135)

    return append_preview_text


def configure_camera(camera, sensor_mode, preview_size, frame_duration_us, lens_position):
    """Configure the camera using the fast video path for preview.

    Args:
        camera (Picamera2): Camera object with ``sensor_modes`` metadata and the
            Picamera2 configuration methods used below.
        sensor_mode (int): Sensor mode index with no physical units.
        preview_size (tuple[int, int]): ``(width_px, height_px)`` for the main
            preview stream in pixels.
        frame_duration_us (int): Requested fixed frame duration in microseconds.
        lens_position (float): Manual lens position scalar in Picamera2 control
            units.

    Returns:
        dict: Picamera2 video configuration dictionary for the preview pipeline.

    Raises:
        ValueError: If ``sensor_mode`` is outside the available camera modes.
    """

    if sensor_mode >= len(camera.sensor_modes):
        raise ValueError(f"Invalid SENSOR_MODE index: {sensor_mode}")

    mode = camera.sensor_modes[sensor_mode]
    video_config = camera.create_video_configuration(
        main={"size": preview_size},
        sensor={"output_size": mode["size"], "bit_depth": mode["bit_depth"]},
        controls={
            "FrameDurationLimits": (frame_duration_us, frame_duration_us),
            "AeExposureMode": controls.AeExposureModeEnum.Normal,
            "AfMode": controls.AfModeEnum.Manual,
            "LensPosition": lens_position,
        },
    )
    camera.align_configuration(video_config)
    camera.configure(video_config)
    return video_config


def shutdown(camera):
    """Stop preview resources and close the camera.

    Args:
        camera (Picamera2): Camera object to stop and close. This is a handle to
            external hardware and has no array shape or physical units.

    Returns:
        None.
    """

    try:
        camera.stop_preview()
    except Exception:
        pass

    try:
        camera.stop()
    except Exception:
        pass

    try:
        camera.close()
    except Exception:
        pass


def make_signal_handler(camera):
    """Create a SIGINT handler that shuts down the preview cleanly.

    Args:
        camera (Picamera2): Camera object to close when SIGINT arrives. This is a
            hardware handle with no shape or physical units.

    Returns:
        collections.abc.Callable: Signal handler taking ``(signum, frame)`` and
        terminating the process after cleanup.
    """

    def _handle_signal(signum, frame):
        """Handle process-interrupt signals for the preview script.

        Args:
            signum (int): POSIX signal number with no physical units.
            frame: Current Python stack frame object from the signal module.

        Returns:
            None: The process exits after cleanup.
        """

        del signum, frame
        shutdown(camera)
        raise SystemExit(0)

    return _handle_signal


def main(argv=None):
    """Run the standalone fast preview script.

    Args:
        argv (list[str] | None): Command-line tokens excluding the executable
            name. Each element is a single CLI token with no physical units.

    Returns:
        int: Process exit status where ``0`` indicates clean shutdown.
    """

    args = parse_args(argv)
    sensor_mode = DEFAULT_SENSOR_MODE
    framerate_hz, frame_duration_us = get_sensor_mode_settings(sensor_mode)

    camera = Picamera2()
    signal.signal(signal.SIGINT, make_signal_handler(camera))

    configure_camera(
        camera=camera,
        sensor_mode=sensor_mode,
        preview_size=PREVIEW_SIZE,
        frame_duration_us=frame_duration_us,
        lens_position=LENS_POSITION,
    )
    camera.pre_callback = make_preview_callback(display_text=args.display_text)

    x_pos, y_pos, width_px, height_px = PREVIEW_WINDOW
    print(f"Using sensor mode {sensor_mode} at {framerate_hz} fps")
    print(
        f"Using preview window x={x_pos} y={y_pos} "
        f"w={width_px} h={height_px}"
    )

    camera.start_preview(
        Preview.DRM,
        x=x_pos,
        y=y_pos,
        width=width_px,
        height=height_px,
    )
    camera.start()
    time.sleep(WARMUP_SECONDS)
    print("Preview running. Press Ctrl+C to stop.")

    try:
        signal.pause()
    except KeyboardInterrupt:
        shutdown(camera)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
