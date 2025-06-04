#!/usr/bin/env python3

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
import os
import signal
from pathlib import Path


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

# set high thread priority - may require sudo access
try:
    os.nice(-20)
except:
    print("set nice level failed. \nsudo nano /etc/security/limits.conf \npi	-       nice    -20")

# camera parameter setting
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
VIDEO_FILE_NAME = str((Path.home() / 'buffer' / "cam{}_output_{}.h264".format(camId, video_dt)).resolve())
TIMESTAMP_FILE_NAME = str((Path.home() / 'buffer' / "cam{}_timestamp_{}.csv".format(camId, video_dt)).resolve())
FLIPPER_FILE_NAME = str((Path.home() / 'buffer' / "cam{}_flipper_{}.csv".format(camId, video_dt)).resolve())

# timestamp output object to save timestamps according to pi and TTL inputs received and write to file
class SimFlipplerOutput(object):

    def __init__(self, flipper_filename, timestamp_filename):
        self._flipper_file = flipper_filename
        self._flipper_timestamps = []
        self._timestampFile = timestamp_filename
        self._timestamps = []

        self.flip_state = False
        self.flip_thread = None
        self.event_thread = None
        self.state_change = Event()
        self._stop_flag = False

    def flush(self):
        with io.open(self._timestampFile, 'w') as f:
            f.write('Sensor Timestamp (ns), time.time(), time.perf_counter_ns()\n')
            for entry in self._timestamps:
                f.write('%f,%f,%f\n' % entry)

        with io.open(self._flipper_file, 'w') as f:
            f.write('Input State, time.time(), time.perf_counter_ns()\n')
            for entry in self._flipper_timestamps:
                f.write('%f,%f,%f\n' % entry)

    def flip_loop(self, bouncetime=BOUNCETIME):
        cur_state = self.flip_state
        tstart = time.time()
        while True:
            if time.time() - tstart > 1:
                cur_state = not self.flip_state
                tstart = time.time()

            if cur_state != self.flip_state:
                self.flip_state = cur_state
                self.state_change.set()
                time.sleep(bouncetime / 1000)  # Convert milliseconds to seconds
            else:
                self.state_change.clear()
                time.sleep(.001)

            if self._stop_flag:
                print("Stopping GPIO loop")
                break

    def flipper_callback(self):
        self._flipper_timestamps.append((self.flip_state,
                                         time.time(),
                                         time.perf_counter_ns()))

    def event_loop(self):
        while True:
            if self.state_change.is_set():
                self.flipper_callback()
                self.state_change.clear()
            else:
                time.sleep(0.001)

            if self._stop_flag:
                print("Stopping event loop")
                break

    def close(self):
        print("Closing threads")
        self._stop_flag = True
        if self.flip_thread is not None:
            self.flip_thread.join()
            self.flip_thread = None
            self.flush()

        if self.event_thread is not None:
            self.event_thread.join()
            self.event_thread = None

    def start_flipper_thread(self):
        if self.flip_thread is None:
            self.flip_thread = Thread(target=self.flip_loop)
            self.event_thread = Thread(target=self.event_loop)
            self.event_thread.start()
            self.flip_thread.start()
        else:
            print("Flipper thread already running")

    def apply_timestamp(self, request):
        meta = request.get_metadata()
        cur_time = time.time()
        # cur_time = dt.datetime.now(dt.timezone.utc)  # alternately use datetime module, which is a tad slower
        self._timestamps.append((
            meta['SensorTimestamp'],
            cur_time,
            # cur_time.timestamp(),  # for datetime module
            time.perf_counter_ns()
        ))

        # if using time module for speed, strftime doesn't include milliseconds for some reason
        framerate = 1e6 / meta['FrameDuration']
        millisec = str(cur_time).split('.')[1]
        sec = time.strftime("%H:%M:%S", time.gmtime(cur_time))
        strftime = '.'.join((sec, millisec))
        # strftime = cur_time.strftime("%H:%M:%S.%f")  # for datetime module
        txt = '{:.3f}; {}; {:.2f} fps'.format((meta['SensorTimestamp'] - self._timestamps[0][0]) / 1e9,
                                              strftime, framerate)
        with MappedArray(request, "main") as m:
            cv2.putText(m.array, txt, origin, font, scale, colour, thickness)


camera = Picamera2()
mode = camera.sensor_modes[1]
config = camera.create_video_configuration(
    sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']},
    # main={"size": (640, 480)},  # for V3 camera
    main={"size": (1600, 1200)},  # for HQ camera
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

flipper = SimFlipplerOutput(FLIPPER_FILE_NAME, TIMESTAMP_FILE_NAME)
camera.pre_callback = flipper.apply_timestamp
camera.start_preview(Preview.DRM, x=100, y=0, width=1067, height=800)

flipper.start_flipper_thread()
with io.open(VIDEO_FILE_NAME, 'wb') as buffer:
    encoder = H264Encoder()
    output = FileOutput(file=buffer)#, pts=TIMESTAMP_FILE_NAME)
    try:
        print('Starting Recording')
        camera.start_recording(encoder, output)
        # camera.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 10.0})  # comment this out for HQ camera, which uses manual focus
        time.sleep(2)
        camera.set_controls({
            'AeEnable': False,
            'AwbEnable': False,
        })
        time.sleep(2)
        print('Started Recording')
        while True:
            time.sleep(.001)

    except Exception as e:
        camera.stop_recording()
        camera.stop_preview()
        flipper.close()
        print('Recording Stopped')
        print(e)

    finally:
        flipper.close()
        print('Recording Stopped')
        sys.exit(0)
