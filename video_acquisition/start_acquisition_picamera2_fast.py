#!/usr/bin/env python3

import sys
import time
import signal
import numpy as np
import cv2
import RPi.GPIO as GPIO

from picamera2 import Picamera2, Preview, MappedArray
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
from libcamera import controls

# --------------------------------------------------
# USER SETTINGS
# --------------------------------------------------

FRAMERATE = 30
FRAME_DURATION_US = int(1e6 / FRAMERATE)
BITRATE = 25000000  # adjust up/down after testing

# ---- Sensor mode selection (same as before) ----
sensor_mode = 0  # change manually when testing

# --------------------------------------------------
# FILE PATHS
# --------------------------------------------------

base_path = sys.argv[1]
camId = "0"

VIDEO_FILE_NAME = base_path + "_cam" + camId + "_output.h264"
TIMESTAMP_FILE_NAME = base_path + "_cam" + camId + "_timestamp.csv"

# --------------------------------------------------
# PRE-RENDER DIGITS (FAST BURN-IN)
# --------------------------------------------------

FONT = cv2.FONT_HERSHEY_SIMPLEX
SCALE = 0.8
THICKNESS = 2

digit_cache = {}

for i in range(10):
    img = np.zeros((40, 30), dtype=np.uint8)
    cv2.putText(img, str(i), (2, 30), FONT, SCALE, 255, THICKNESS)
    digit_cache[str(i)] = img

def draw_number_fast(frame_y_plane, number, x=10, y=50):
    s = str(number)
    offset = 0
    for char in s:
        if char in digit_cache:
            digit = digit_cache[char]
            h, w = digit.shape
            frame_y_plane[y-h:y, x+offset:x+offset+w] = np.maximum(
                frame_y_plane[y-h:y, x+offset:x+offset+w],
                digit
            )
            offset += w + 2

# --------------------------------------------------
# TIMESTAMP STORAGE
# --------------------------------------------------

timestamps = []

def append_timestamp(request):
    meta = request.get_metadata()
    sensor_ts = meta["SensorTimestamp"]
    timestamps.append(sensor_ts)

    # Burn into Y plane only (fastest)
    with MappedArray(request, "main") as m:
        frame_y = m.array[:, :, 0]
        draw_number_fast(frame_y, sensor_ts)

# --------------------------------------------------
# CAMERA SETUP
# --------------------------------------------------

camera = Picamera2()

# Validate sensor mode
if sensor_mode >= len(camera.sensor_modes):
    raise ValueError("Invalid sensor_mode index")

# configs for camera sensors at 30 fps
# for camera V3 standard module, using bit_depth 10, size (2304, 1296), max fps 56.03
# for HQ camera, sensor modes 0, 1, and 2 are okay
# mode0 = {'size': (1332, 990), 'fps': 120}, dunno bit depth
# mode1 = {'size': (2028, 1080), 'bit_depth': 12, 'fps': 50.03}
# mode2 = {'size': (4056, 3040), 'bit_depth': 12, 'fps': 40.01}

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

camera.start_preview(Preview.DRM)

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
        for ts in timestamps:
            f.write(f"{ts}\n")

    GPIO.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)

# --------------------------------------------------
# START RECORDING
# --------------------------------------------------

print("Starting high-quality recording...")
camera.start_recording(encoder, output)

# Allow AE/AWB to settle
time.sleep(2)

camera.set_controls({
    "AeEnable": False,
    "AwbEnable": False,
})

print("Recording with burned-in timestamps. Press Ctrl+C to stop.")

while True:
    time.sleep(1)
