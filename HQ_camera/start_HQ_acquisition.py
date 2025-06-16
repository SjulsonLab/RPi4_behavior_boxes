#!/usr/bin/env python3

"""
This script is used to start a video recording with the Raspberry Pi HQ camera.
It is meant to run independently of behavior code, outputting its own strobe/flipper signal and timestamps.
"""


from gpiozero import Button
import io
import time
import datetime as dt
from picamera2 import Picamera2, Preview, MappedArray
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import FileOutput
import cv2
from libcamera import controls
from threading import Thread, Event
import sys
import RPi.GPIO as GPIO
from gpiozero import LED, Button
import os
import signal
from pathlib import Path
import random

# this function is called when the program receives a SIGINT
def signal_handler(signum, frame):
    print("SIGINT detected")
    camera.stop_recording()
    camera.stop_preview()
    print('Recording Stopped')
    output.close()
    print('Closing Output File')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
base_path = sys.argv[1]

# set high thread priority - may require sudo access
try:
    os.nice(-20)
except:
    print("set nice level failed. \nsudo nano /etc/security/limits.conf \npi	-       nice    -20")

#camera parameter setting
WIDTH  = 640
HEIGHT = 480
FRAMERATE = 30
BRIGHTNESS = 0  # 0:100 in Picam1, -1:1 in Picam2
CONTRAST = 1  # 50 / 100
SHARPNESS = 1  # 50
SATURATION = 1  # 30
# AWB_MODE = 'off'
# AWB_GAINS = 1.4

# Flipper TTL Pulse BounceTme in milliseconds
BOUNCETIME = 100
camId = str(0)

# overlay text for preview window timestamps
colour = (255, 255, 255)  # white
origin = (0, 30)
font = cv2.FONT_HERSHEY_SIMPLEX
scale = 1
thickness = 2

# video, timestamps and ttl file name
video_dt = str(dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
VIDEO_FILE_NAME = base_path + "_cam" + camId + "_output_" + video_dt + ".h264"
TIMESTAMP_FILE_NAME = base_path + "_cam" + camId + "_timestamp_" + video_dt + ".csv"
FLIPPER_FILE_NAME = base_path + "_cam"+ camId + "_flipper_" + video_dt + ".csv"

# set raspberry pi board layout to BCM
pin_flipper = 4
GPIO.setmode(GPIO.BCM)

# Class to hold flipper and camera timestamps
class TimestampOutput(object):

    def __init__(self, timestamp_filename, flipper_filename):
        self._timestampFile = timestamp_filename
        self._flipper_file = flipper_filename
        self._camera_timestamps = []
        self._flipper_timestamps = []

        self._flipper = LED(pin_flipper)
        self._flip_thread = None
        self._stop_flag = Event()
        self._running = False

    def flip(self, time_min=0.5, time_max=2, n=None):
        self._stop_flip()
        self._flipper.off()
        self._running = True
        self._stop_flag.clear()
        self._flip_thread = Thread(target=self._flip_device, args=(time_min, time_max, n))
        self._flip_thread.start()

    def _flip_device(self, time_min, time_max, n):
        while self._running:
            on_time = round(random.uniform(time_min, time_max), 3)
            off_time = round(random.uniform(time_min, time_max), 3)

            self._flipper.on()  # change this to your GPIO on method
            pin_state = self._flipper.value  # change this to your GPIO state check method
            timestamp = (pin_state, time.time())
            self._flipper_timestamps.append(timestamp)
            if self._stop_flag.wait(on_time):
                self._flipper.off()
                break

            self._flipper.off()
            pin_state = self._flipper.value
            timestamp = (pin_state, time.time())
            self._flipper_timestamps.append(timestamp)
            if self._stop_flag.wait(off_time):
                break

    def append_camera_timestamps(self, request):
        cur_time = time.time()
        meta = request.get_metadata()
        # cur_time = dt.datetime.now(dt.timezone.utc)  # alternately use datetime module, which is a tad slower
        self._camera_timestamps.append((
            meta['SensorTimestamp'],
            meta['FrameDuration'],
            cur_time
        ))

        # if using time module for speed, strftime doesn't include milliseconds for some reason
        framerate = 1e6 / meta['FrameDuration']
        millisec = str(round(cur_time, ndigits=6)).split('.')[1]
        sec = time.strftime("%H:%M:%S", time.gmtime(cur_time))
        strftime = '.'.join((sec, millisec))
        # strftime = cur_time.strftime("%H:%M:%S.%f")  # for datetime module
        txt = '{:.3f}; {}; {:.2f} fps'.format((meta['SensorTimestamp'] - self._camera_timestamps[0][0]) / 1e9,
                                              strftime, framerate)
        with MappedArray(request, "main") as m:
            cv2.putText(m.array, txt, origin, font, scale, colour, thickness)

    def flush(self):
        with io.open(self._timestampFile, 'w') as f:
            f.write('Sensor Timestamp (ns), Frame Duration (ms), time.time()\n')
            for entry in self._camera_timestamps:
                f.write('%f,%f,%f\n' % entry)

        with io.open(self._flipper_file, 'w') as f:
            f.write('pin_state, time.time()\n')
            for entry in self._flipper_timestamps:
                f.write('%f,%f\n' % entry)

    def _stop_flip(self):
        print("Closing threads")
        if self._flip_thread is None:
            print("No flipper thread to stop")
            return
        else:
            self._running = False
            self._stop_flag.set()
            self._flip_thread.join(5)
            if self._flip_thread.is_alive():
                raise Exception("Flipper thread not closed")
            else:
                self._flip_thread = None
                print("Flipper thread is closed!")

    def close(self):
        self._stop_flip()
        self.flush()


# Picam2 has brightness, contrast, sharpness, saturation, exposure modes, awb_mode
# Picam2 does not have an image stabilization option
# hflip and vflip are Transforms now, both default to False
camera = Picamera2()
mode = camera.sensor_modes[1]
config = camera.create_video_configuration(
    sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']},
    main={"size": (640, 480)},
    controls={'FrameDurationLimits': (33333, 33333),
              'AeExposureMode': controls.AeExposureModeEnum.Normal,
              "Brightness": BRIGHTNESS,
              "Contrast": CONTRAST,
              "Sharpness": SHARPNESS,
              "Saturation": SATURATION
})
camera.align_configuration(config)
camera.configure(config)
print("Camera configuration aligned to {}".format(camera.video_configuration.size))

timestamps = TimestampOutput(TIMESTAMP_FILE_NAME, FLIPPER_FILE_NAME)
camera.pre_callback = timestamps.append_camera_timestamps
camera.start_preview(Preview.DRM, x=100, y=0, width=1067, height=800)

with io.open(VIDEO_FILE_NAME, 'wb') as buffer:
    encoder = H264Encoder()
    output = FileOutput(file=buffer)#, pts=TIMESTAMP_FILE_NAME)
    try:
        print('Starting Recording')
        camera.start_recording(encoder, output)
        # camera.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 10.0})  # for V3 camera; comment this out for HQ camera, which uses manual focus
        time.sleep(2)
        camera.set_controls({
            'AeEnable': False,
            'AwbEnable': False,
        })
        time.sleep(2)
        print('Started Recording')
        while True:
            # time.sleep(.001)
            continue

    except Exception as e:
        camera.stop_recording()
        camera.stop_preview()
        print('Recording Stopped')
        print(e)

    finally:
        timestamps.close()
        sys.exit(0)
