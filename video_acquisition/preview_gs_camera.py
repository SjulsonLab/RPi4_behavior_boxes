#!/usr/bin/env python3

import signal
import sys
import datetime as dt
from picamera2 import Picamera2, Preview, MappedArray
import cv2
from pprint import pprint

def signal_handler(signum, frame):
    print("SIGINT detected")
    camera.stop_preview()
    camera.close()
    sys.exit(0)


colour = (255, 255, 255)  # white
origin = (0, 30)
font = cv2.FONT_HERSHEY_SIMPLEX
scale = 1
thickness = 2

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
# For GS camera, there is only one sensor mode
# mode0 = {'size': (1456, 1088), 'fps': 60}
## see for yourself:
print_sensor_modes = False
if print_sensor_modes:
    pprint(camera.sensor_modes)

mode = camera.sensor_modes[0]
print("Using sensor mode:", mode)

config = camera.create_preview_configuration(
    main={"size": mode["size"]},
    sensor={"output_size": mode["size"], "bit_depth": mode["bit_depth"]},
    controls={"FrameRate": 30.0}
)


camera.configure(config)

x, y, w, h = 100, 0, 1067, 800
print(f"Trying preview window x={x} y={y} w={w} h={h}")

camera.pre_callback = apply_timestamp
camera.start_preview(Preview.DRM, x=x, y=y, width=w, height=h)
camera.start()
print("Camera is running")

signal.pause()
