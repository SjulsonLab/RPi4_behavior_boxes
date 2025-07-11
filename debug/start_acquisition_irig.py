#!/usr/bin/env python3

from gpiozero import Button
import io
import time
import datetime as dt
from picamera2 import Picamera2, Preview, MappedArray
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import FileOutput
import irig_h_gpio as irig
import cv2
from libcamera import controls
from threading import Thread, Event
import sys
import RPi.GPIO as GPIO
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
buffer_dir = Path('/home/pi/buffer/')
# output_path = Path('/home/pi/buffer/irig_output')

datestr = dt.datetime.now().strftime("%Y-%m-%d")
timestr = dt.datetime.now().strftime('%H%M%S')
datetime = datestr + '_' + timestr
session_name = 'irig_' + datetime
output_dir = buffer_dir / session_name
base_path = str((output_dir / session_name).resolve())

if not os.path.exists(output_dir):
    os.makedirs(output_dir)


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
IRIG_FILE_NAME = base_path + "_cam" + camId + "_irig_" + video_dt + ".csv"

# set raspberry pi board layout to BCM
pin_flipper = 4
GPIO.setmode(GPIO.BCM)
GPIO.setup(pin_flipper, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#timestamp output object to save timestamps according to pi and TTL inputs received and write to file
class TimestampOutput(object):

    def __init__(self, timestamp_filename, flipper_filename):
        self._timestampFile = timestamp_filename
        self._flipper_file = flipper_filename
        self._timestamps = []
        self._flipper_timestamps = []

        self.flip_state = GPIO.input(pin_flipper)
        self.flip_thread = None
        self.event_thread = None
        self.irig_thread = None
        self.state_change = Event()
        self._stop_flag = False

    def append_timestamps(self, request):
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
        millisec = str(round(cur_time, ndigits=6)).split('.')[1]
        sec = time.strftime("%H:%M:%S", time.gmtime(cur_time))
        strftime = '.'.join((sec, millisec))
        # strftime = cur_time.strftime("%H:%M:%S.%f")  # for datetime module
        txt = '{:.3f}; {}; {:.2f} fps'.format((meta['SensorTimestamp'] - self._timestamps[0][0]) / 1e9,
                                              strftime, framerate)
        with MappedArray(request, "main") as m:
            cv2.putText(m.array, txt, origin, font, scale, colour, thickness)

    def flush(self):
        with io.open(self._timestampFile, 'w') as f:
            f.write('Sensor Timestamp (ns), time.time(), time.perf_counter_ns()\n')
            for entry in self._timestamps:
                f.write('%f,%f,%f\n' % entry)

        with io.open(self._flipper_file, 'w') as f:
            f.write('Input State, time.time(), time.perf_counter_ns()\n')
            for entry in self._flipper_timestamps:
                f.write('%f,%f,%f\n' % entry)

    def GPIO_loop(self, bouncetime=BOUNCETIME):
        while True:
            cur_state = GPIO.input(pin_flipper)
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

    def flipper_callback_GPIO(self, pin):
        self.flip_state = GPIO.input(pin)
        self._flipper_timestamps.append((self.flip_state,
                                         time.time(),
                                         time.perf_counter_ns()))

    def flipper_callback(self):
        self._flipper_timestamps.append((self.flip_state,
                                         time.time(),
                                         time.perf_counter_ns()))

    # def start_irig_sending(self):
    #     """
    #     Continuously sends irig timecodes in an unending while loop.
    #     """
    #     while True:
    #         irig.generate_and_send_irig_h()
    #         if self._stop_flag:
    #             print("Stopping IRIG sending")
    #             break

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

    def close_threads(self):
        print("Closing threads")
        self._stop_flag = True
        if self.flip_thread is not None:
            self.flip_thread.join()
            self.flip_thread = None
        if self.event_thread is not None:
            self.event_thread.join()
            self.event_thread = None
        # if self.irig_thread is not None:
        #     self.irig_thread.join()
        #     self.irig_thread = None

    def close(self):
        self.close_threads()
        self.flush()
        # irig.finish(IRIG_FILE_NAME)

    def start_flipper_thread(self):
        if self.flip_thread is None:
            self.flip_thread = Thread(target=self.GPIO_loop)
            self.event_thread = Thread(target=self.event_loop)
            self.event_thread.start()
            self.flip_thread.start()
        else:
            print("Flipper thread already running")


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
camera.pre_callback = timestamps.append_timestamps
camera.start_preview(Preview.DRM, x=100, y=0, width=1067, height=800)
# timestamps.start_flipper_thread()
GPIO.add_event_detect(pin_flipper, GPIO.BOTH, callback=timestamps.flipper_callback_GPIO, bouncetime=100)
irig_sender = irig.IrigHSender(sending_gpio_pin=6, filename=IRIG_FILE_NAME)

with io.open(VIDEO_FILE_NAME, 'wb') as buffer:
    encoder = H264Encoder()
    output = FileOutput(file=buffer)#, pts=TIMESTAMP_FILE_NAME)
    try:
        print('Starting Recording')
        camera.start_recording(encoder, output)
#        camera.set_controls({"AfMode": controls.AfModeEnum.Manual,
#                             "LensPosition": 10.0})
        irig_sender.start()

        time.sleep(2)
        camera.set_controls({
            'AeEnable': False,
            'AwbEnable': False,
        })
        time.sleep(2)

        print('Started Recording')

        # Start irig sending background thread
        # irig_sender_thread = Thread(target=irig.start_irig_sending, daemon=True)
        # irig_sender_thread.start()
        # timestamps.irig_thread = Thread(target=irig.start_irig_sending, daemon=True)
        # timestamps.irig_thread.start()

        # UNCOMMENT THIS AND COMMENT THE OTHER CODE TO REMOVE MULTITHREADING
        # irig.start_irig_sending()

        while True:
            # time.sleep(.001)
            continue

    except Exception as e:
        camera.stop_recording()
        camera.stop_preview()
        timestamps.close_threads()
        print('Recording Stopped')
        print(e)

    finally:
        irig_sender.finish()
        timestamps.close()
        sys.exit(0)
        