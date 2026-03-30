#!/usr/bin/env python3

import os
import signal
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from libcamera import controls
from picamera2 import MappedArray, Picamera2, Preview
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput


FRAMERATE = 50
FRAME_DURATION_US = int(1e6 / FRAMERATE)
BITRATE = 30_000_000
SENSOR_MODE = 1
PREVIEW_SIZE = (1024, 768)
PREVIEW_WINDOW = (100, 0, 1024, 768)
LENS_POSITION = 32.0
WARMUP_SECONDS = 2

FONT = cv2.FONT_HERSHEY_SIMPLEX
SCALE = 0.8
THICKNESS = 2
CHARACTERS = "0123456789.-"


char_cache = {}
for char in CHARACTERS:
    glyph = np.zeros((40, 30), dtype=np.uint8)
    cv2.putText(glyph, char, (2, 30), FONT, SCALE, 255, THICKNESS)
    char_cache[char] = glyph


def draw_text_fast(frame_y, text, x=10, y=50):
    offset = 0
    for char in text:
        if char in char_cache:
            glyph = char_cache[char]
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
        else:
            offset += 15


def require_args():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: start_acquisition_v3_camera_fast.py <base_path> [camera_id] [pidfile]")
    base_path = Path(sys.argv[1])
    camera_id = str(sys.argv[2]) if len(sys.argv) > 2 else "0"
    pidfile = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    return base_path, camera_id, pidfile


base_path, cam_id, pidfile_path = require_args()
video_file_name = f"{base_path}_{cam_id}_output.h264"
timestamp_file_name = f"{base_path}_{cam_id}_timestamp.csv"

# set high thread priority - may require sudo access
try:
    os.nice(-20)
except Exception:
    print("set nice level failed. \nsudo nano /etc/security/limits.conf \npi\t-\tnice\t-20")


timestamps = []
camera = Picamera2()
recording_started = False
output = None


def append_timestamp(request):
    meta = request.get_metadata()
    sensor_ts = meta["SensorTimestamp"]
    frame_duration = meta.get("FrameDuration", 0)
    unix_ts = time.time()
    elapsed = 0.0 if not timestamps else (sensor_ts - timestamps[0][0]) / 1e9
    fps = (1e6 / frame_duration) if frame_duration else 0.0

    timestamps.append((sensor_ts, frame_duration, unix_ts))

    with MappedArray(request, "main") as mapped:
        frame = mapped.array
        frame_y = frame[:, :, 0] if frame.ndim == 3 else frame
        draw_text_fast(frame_y, f"{elapsed:.3f}", x=10, y=45)
        draw_text_fast(frame_y, f"{unix_ts:.6f}", x=10, y=90)
        draw_text_fast(frame_y, f"{fps:.1f}", x=10, y=135)


def flush_timestamps():
    with open(timestamp_file_name, "w") as handle:
        handle.write("SensorTimestamp_ns,FrameDuration_us,UnixTimestamp_s\n")
        for sensor_ts, frame_duration, unix_ts in timestamps:
            handle.write(f"{sensor_ts},{frame_duration},{unix_ts}\n")


def shutdown(signum=None, frame=None):
    global recording_started
    print("Stopping...")

    if recording_started:
        try:
            camera.stop_recording()
        except Exception:
            pass
        recording_started = False

    try:
        camera.stop_preview()
    except Exception:
        pass

    try:
        camera.close()
    except Exception:
        pass

    if output is not None:
        try:
            output.close()
        except Exception:
            pass

    if pidfile_path is not None:
        try:
            pidfile_path.unlink(missing_ok=True)
        except Exception:
            pass

    flush_timestamps()
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown)

if SENSOR_MODE >= len(camera.sensor_modes):
    raise ValueError(f"Invalid SENSOR_MODE index: {SENSOR_MODE}")

mode = camera.sensor_modes[SENSOR_MODE]
print(f"Using sensor mode {SENSOR_MODE}: {mode['size']}")

video_config = camera.create_video_configuration(
    main={"size": PREVIEW_SIZE},
    sensor={"output_size": mode["size"], "bit_depth": mode["bit_depth"]},
    controls={
        "FrameDurationLimits": (FRAME_DURATION_US, FRAME_DURATION_US),
        "AeExposureMode": controls.AeExposureModeEnum.Normal,
        "AfMode": controls.AfModeEnum.Manual,
        "LensPosition": LENS_POSITION,
    },
)

camera.align_configuration(video_config)
camera.configure(video_config)
camera.pre_callback = append_timestamp

x, y, width, height = PREVIEW_WINDOW
camera.start_preview(Preview.DRM, x=x, y=y, width=width, height=height)
print(f"Using preview window x={x} y={y} w={width} h={height}")

encoder = H264Encoder(bitrate=BITRATE)
output = FileOutput(video_file_name)

try:
    print("Starting recording...")
    camera.start_recording(encoder, output)
    recording_started = True

    time.sleep(WARMUP_SECONDS)
    camera.set_controls({
        "AeEnable": False,
        "AwbEnable": False,
    })

    print("Recording... Press Ctrl+C to stop.")
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    shutdown()
except Exception as exc:
    print(exc)
    shutdown()
