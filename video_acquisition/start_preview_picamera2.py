#!/usr/bin/env python3

import signal
import numpy as np
import sys
from picamera2 import Picamera2, Preview, MappedArray
from libcamera import controls
import cv2
import time
import datetime as dt
import RPi.GPIO as GPIO

def signal_handler(signum, frame):
    print("SIGINT detected")
    camera.stop_preview()
    camera.close()
    sys.exit(0)


def flipper_callback_GPIO(pin):
    flip_state = GPIO.input(pin)
    #print("Flip state: {}; Timestamp: {}; UTC: {}".format(flip_state, time.time(), dt.datetime.now(dt.timezone.utc).time()))


pin_flipper = 4
GPIO.setmode(GPIO.BCM)
GPIO.setup(pin_flipper, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(pin_flipper, GPIO.BOTH, callback=flipper_callback_GPIO, bouncetime=100)
signal.signal(signal.SIGINT, signal_handler)

camera = Picamera2()
camera.start_preview(Preview.DRM, x=100, y=0, width=1067, height=800)

# configs for camera sensors at 30 fps
# for camera V3 standard module, using bit_depth 10, size (2304, 1296), max fps 56.03
# for HQ camera, sensor modes 1 and 2 are okay; mode 0 has 120 fps but we only want 30 so we can get a bit more resolution
# mode1 = {'size': (2028, 1080), 'bit_depth': 12, 'fps': 50.03}
# mode2 = {'size': (4056, 3040), 'bit_depth': 12, 'fps': 40.01}

sensor_mode = 2
if sensor_mode == 0:
    resolution = (1320, 990)
elif sensor_mode == 1:
    resolution = (1440, 1080)
elif sensor_mode == 2:
    resolution = (2000, 1500)
else:
    print("Invalid sensor mode selected, setting default resolution")
    sensor_mode = 0
    resolution = (640, 480)

# config = camera.create_preview_configuration(sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']})
# camera.configure(config)

mode = camera.sensor_modes[sensor_mode]
camera.preview_configuration.sensor.output_size = mode['size']
camera.preview_configuration.sensor.bit_depth = mode['bit_depth']
#camera.preview_configuration.main.size = resolution
# camera.preview_configuration.size = (640, 480) # default setting, fine for preview screen
# camera.preview_configuration.size = (1320, 990)  # max HQ resolution for sensor 0
# camera.preview_configuration.size = (1440, 1080)  # max HQ resolution for sensor 1
# camera.preview_configuration.size = (2000, 1500)  # max HQ resolution for sensor 2
camera.preview_configuration.align()
camera.preview_configuration.controls.FrameRate = 30.0
camera.configure("preview")
print("Camera configuration aligned to {}".format(camera.preview_configuration.size))
time.sleep(2)  # let the camera warm up/autofocus

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

# camera.pre_callback = apply_timestamp
camera.start_preview(Preview.DRM, x=100, y=0, width=1067, height=800)
camera.start()

# comment this out for the HQ camera, which has no autofocus/uses manual focus
#camera.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 10.0})  # default is 1, max focal range is zero, min focal range is 32. Using 10 is fine

signal.pause()
