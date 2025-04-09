#!/usr/bin/env python3

import signal
import numpy as np
import sys
from picamera2 import Picamera2, Preview
import cv2
import time

def signal_handler(signum, frame):
    print("SIGINT detected")
    camera.stop_preview()
    camera.close()
    sys.exit(0)

camera = Picamera2()
camera.start_preview(Preview.DRM, x=100, y=0, width=1067, height=800)

# configs for camera sensors at 30 fps
# for camera V3 standard module, using bit_depth 1, size (2304, 1296), max fps 56.03
mode = camera.sensor_modes[1]
# config = camera.create_preview_configuration(sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']})
# camera.configure(config)
camera.preview_configuration.sensor.output_size = mode['size']
camera.preview_configuration.sensor.bit_depth = mode['bit_depth']
camera.preview_configuration.size = (640, 480) # defaults
# camera.preview_configuration.size = (1600, 1280)
camera.preview_configuration.align()
camera.preview_configuration.controls.FrameRate = 30.0
camera.configure("preview")
print("Camera configuration aligned to {}".format(camera.preview_configuration.size))
time.sleep(2)  # let the camera warm up/autofocus

# colour = (0, 255, 0, 255)
# origin = (0, 30)
# font = cv2.FONT_HERSHEY_SIMPLEX
# scale = 1
# thickness = 2
# overlay = np.zeros((640, 480, 4), dtype=np.uint8)
# cv2.putText(overlay, "PREVIEW ONLY", origin, font, scale, colour, thickness)
# camera.set_overlay(overlay)
# camera.annotate_text_size = 60
camera.start()

signal.signal(signal.SIGINT, signal_handler)
signal.pause()
