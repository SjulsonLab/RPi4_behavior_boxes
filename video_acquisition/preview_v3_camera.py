#!/usr/bin/env python3

import signal
import sys
import time
import datetime as dt
from picamera2 import Picamera2, Preview, MappedArray
from libcamera import controls
import cv2
from pprint import pprint

def signal_handler(signum, frame):
    print("SIGINT detected")
    camera.stop_preview()
    camera.close()
    sys.exit(0)


colour = (255, 255, 255)  # white
font = cv2.FONT_HERSHEY_SIMPLEX

def apply_timestamp(request):
    timestamp = dt.datetime.now().strftime("%H:%M:%S.%f")
    meta = request.get_metadata()
    framerate = 1e6 / meta['FrameDuration']
    txt = 'PREVIEW ONLY; {}; {} fps'.format(timestamp, framerate)
    with MappedArray(request, "main") as m:
        cv2.putText(m.array, txt, origin, font, scale, colour, thickness)

signal.signal(signal.SIGINT, signal_handler)

camera = Picamera2()

### V3 camera sensor modes:
# Use mode 0, 1, or 2 for 30 fps recording
# Sensor modes 0 and 1 have fast visuals
# Sensor mode 2 will look lagged on the preview screen, but should still record at 30 fps

# mode0 = {'size': (1332, 990), 'bit_depth': 10, 'fps': 120.05}
# mode1 = {'size': (2028, 1080), 'bit_depth': 12, 'fps': 50.03}
# mode2 = {'size': (4056, 3040), 'bit_depth': 12, 'fps': 40.01}
# mode3 = {'size': (4056, 3040), 'bit_depth': 12, 'fps': 10.0}
## see for yourself:
print_sensor_modes = False
if print_sensor_modes:
    pprint(camera.sensor_modes)

mode_ix = 0
mode = camera.sensor_modes[mode_ix]
print("Using sensor mode:", mode)

# Preview text settings
if mode_ix == 0:
    origin = (0, 30)
    scale = 1
    thickness = 2
elif mode_ix == 1:
    origin = (0, 50)
    scale = 2
    thickness = 4
elif mode_ix == 2:
    origin = (0, 100)
    scale = 4
    thickness = 6


config = camera.create_preview_configuration(
    main={"size": (1024, 768)},
    sensor={"output_size": mode["size"], "bit_depth": mode["bit_depth"]},
    controls={"FrameRate": 30.0,
              "AfMode": controls.AfModeEnum.Manual,
              "LensPosition": 10.0}  # ranges from 0 (max focal distance) to 32 (min focal distance)
)
# default LensPosition is 1, max focal range is zero (infinite distance), min focal range is 32 (min distance)
# Using 10 is fine for general use, but for up-close eye recording you may want higher values


camera.configure(config)

x, y, w, h = 100, 0, 1024, 768
print(f"Trying preview window x={x} y={y} w={w} h={h}")

camera.pre_callback = apply_timestamp
camera.start_preview(Preview.DRM, x=x, y=y, width=w, height=h)
camera.start()
time.sleep(2)  # let the camera warm up/autofocus
print("Camera is running")

signal.pause()
