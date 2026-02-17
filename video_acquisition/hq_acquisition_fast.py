#!/usr/bin/env python3

import sys
import time
import signal
import datetime as dt
from pathlib import Path
import numpy as np
import cv2

from picamera2 import Picamera2, Preview, MappedArray
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
from libcamera import controls

# --------------------------------------------------
# USER SETTINGS
# --------------------------------------------------

FRAMERATE = 30
FRAME_DURATION_US = int(1e6 / FRAMERATE)
BITRATE = 30000000  # 30 Mbps safe starting point

sensor_mode = 0  # change manually when testing

# --------------------------------------------------
# FILE PATHS
# --------------------------------------------------

video_dt = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
base_path = Path.home() / "buffer" / video_dt
camId = "0"

VIDEO_FILE_NAME = str(base_path.resolve()) + "_cam" + camId + "_output.h264"
TIMESTAMP_FILE_NAME = str(base_path.resolve()) + "_cam" + camId + "_timestamp.csv"

# --------------------------------------------------
# PRE-RENDER DIGITS + SYMBOLS
# --------------------------------------------------

FONT = cv2.FONT_HERSHEY_SIMPLEX
SCALE = 0.8
THICKNESS = 2

char_cache = {}
chars = "0123456789.-"

for c in chars:
    img = np.zeros((40, 30), dtype=np.uint8)
    cv2.putText(img, c, (2, 30), FONT, SCALE, 255, THICKNESS)
    char_cache[c] = img


def draw_text_fast(frame_y, text, x=10, y=50):
    offset = 0
    for char in text:
        if char in char_cache:
            glyph = char_cache[char]
            h, w = glyph.shape
            frame_y[y - h:y, x + offset:x + offset + w] = np.maximum(
                frame_y[y - h:y, x + offset:x + offset + w],
                glyph
            )
            offset += w + 2
        else:
            offset += 15  # spacing for unsupported chars


# --------------------------------------------------
# TIMESTAMP STORAGE
# --------------------------------------------------

timestamps = []


def append_timestamp(request):
    meta = request.get_metadata()
    sensor_ts = meta["SensorTimestamp"]
    unix_ts = time.time_ns() * 1e-9

    timestamps.append((sensor_ts, unix_ts))

    # Format Unix time with microsecond precision
    unix_str = f"{unix_ts:.6f}"

    with MappedArray(request, "main") as m:
        frame_y = m.array[:, :, 0]

        # Top line: UNIX timestamp
        draw_text_fast(frame_y, unix_str, x=10, y=50)

        # Second line: SensorTimestamp (ns)
        draw_text_fast(frame_y, str(sensor_ts), x=10, y=100)


# --------------------------------------------------
# CAMERA SETUP
# --------------------------------------------------

camera = Picamera2()

if sensor_mode >= len(camera.sensor_modes):
    raise ValueError("Invalid sensor_mode index")

mode = camera.sensor_modes[sensor_mode]
print(f"Using sensor mode {sensor_mode}: {mode['size']}")

video_config = camera.create_video_configuration(
    sensor={
        "output_size": mode["size"],
        "bit_depth": mode["bit_depth"]
    },
    controls={
        "FrameDurationLimits": (FRAME_DURATION_US, FRAME_DURATION_US),
        "AeExposureMode": controls.AeExposureModeEnum.Normal,
    }
)

camera.configure(video_config)
camera.pre_callback = append_timestamp
camera.start_preview(Preview.DRM, x=100, y=0, width=1067, height=800)

encoder = H264Encoder(bitrate=BITRATE)
output = FileOutput(VIDEO_FILE_NAME)

# --------------------------------------------------
# CLEAN SHUTDOWN
# --------------------------------------------------


def shutdown(sig, frame):
    print("Stopping...")
    camera.stop_recording()
    camera.stop_preview()

    with open(TIMESTAMP_FILE_NAME, "w") as f:
        f.write("SensorTimestamp_ns,UnixTimestamp_s\n")
        for sensor_ts, unix_ts in timestamps:
            f.write(f"{sensor_ts},{unix_ts}\n")

    sys.exit(0)


signal.signal(signal.SIGINT, shutdown)

# --------------------------------------------------
# START RECORDING
# --------------------------------------------------

print("Starting recording...")
camera.start_recording(encoder, output)

time.sleep(2)
camera.set_controls({
    "AeEnable": False,
    "AwbEnable": False,
})

print("Recording... Press Ctrl+C to stop.")

while True:
    time.sleep(1)
