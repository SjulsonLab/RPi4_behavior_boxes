#!/usr/bin/env python3

#import the necessary modules
from gpiozero import Button
import io
import time
import datetime as dt
from picamera import PiCamera
from threading import Thread, Event
from queue import Queue, Empty
import sys
import RPi.GPIO as GPIO
import os
import signal

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

#set high thread priority
try:
    os.nice(-20)
except:
    print("set nice level failed. \nsudo nano /etc/security/limits.conf \npi	-       nice    -20")

#camera parameter setting
WIDTH  = 640
HEIGHT = 480
FRAMERATE = 30
VIDEO_STABILIZATION = True
EXPOSURE_MODE = 'night'
BRIGHTNESS = 55
CONTRAST = 50
SHARPNESS = 50
SATURATION = 30
AWB_MODE = 'off'
AWB_GAINS = 1.4

#Flipper TTL Pulse BounceTme in milliseconds
BOUNCETIME=10
camId = str(0)

#video, timestamps and ttl file name
VIDEO_FILE_NAME = base_path + "_cam" + camId + "_output_" + str(dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")) + ".h264"
TIMESTAMP_FILE_NAME = base_path + "_cam" + camId + "_timestamp_" + str(dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")) + ".csv"
FLIPPER_FILE_NAME = base_path + "_cam"+ camId + "_flipper_" + str(dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")) + ".csv"

#set raspberry pi board layout to BCM
GPIO.setmode(GPIO.BCM)

#pin number to receive TTL input
pin_flipper = 4

#set the pin as input pin
GPIO.setup(pin_flipper, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)

#add event detection (both falling edge and rising edge) script to GPIO pin
GPIO.add_event_detect(pin_flipper, GPIO.BOTH, bouncetime=BOUNCETIME)

#video output thread to save video file
class VideoOutput(Thread):
    def __init__(self, filename):
        super(VideoOutput, self).__init__()
        self._output = io.open(filename, 'wb', buffering=0)
        self._event = Event()
        self._queue = Queue()
        self.start()

    def write(self, buf):
        self._queue.put(buf)
        return len(buf)

    def run(self):
        while not self._event.wait(0):
            try:
                buf = self._queue.get(timeout=0.1)
            except Empty:
                pass
            else:
                self._output.write(buf)
                self._queue.task_done()

    def flush(self):
        self._queue.join()
        self._output.flush()

    def close(self):
        self._event.set()
        self.join()
        self._output.close()

    @property
    def name(self):
        return self._output.name

#timestamp output object to save timestamps according to pi and TTL inputs received and write to file
class TimestampOutput(object):
    def __init__(self, camera, video_filename, timestamp_filename, flipper_filename):
        self.camera = camera
        self._video = VideoOutput(video_filename)
        self._timestampFile = timestamp_filename
        self._flipper_file = flipper_filename
        self._timestamps = []
        self._flipper_timestamps = []

    def flipper_timestamps_write(self, pin_flipper):
        input_state = GPIO.input(pin_flipper)
        GPIO.remove_event_detect(pin_flipper)
        self._flipper_timestamps.append((input_state, time.time()))
        #print(input_state, time.time())
        print(str(self._flipper_timestamps))
        GPIO.add_event_detect(pin_flipper, GPIO.BOTH, bouncetime=BOUNCETIME)

    def write(self, buf):
        if self.camera.frame.complete and self.camera.frame.timestamp is not None:
            if len(self._timestamps) > 0:
                if self.camera.frame.timestamp != self._timestamps[-1][0]: # Ignore the 0 interval consecutive timestamp
                    self._timestamps.append((
                        self.camera.frame.timestamp,
                        self.camera.dateTime,
                        self.camera.clockRealTime
                        ))
            else:
                    self._timestamps.append((
                        self.camera.frame.timestamp,
                        self.camera.dateTime,
                        self.camera.clockRealTime
                        ))
        return self._video.write(buf)

    def flush(self):
        with io.open(self._timestampFile, 'w') as f:
            f.write('GPU Times, time.time(), clock_realtime\n')
            for entry in self._timestamps:
                f.write('%d,%f,%f\n' % entry)
        with io.open(self._flipper_file, 'w') as f:
            f.write('Input State, Timestamp\n')
            for entry in self._flipper_timestamps:
                f.write('%f,%f\n' % entry)

    def close(self):
        self._video.close()

with PiCamera(resolution=(WIDTH, HEIGHT), framerate=FRAMERATE) as camera:

    camera.brightness = BRIGHTNESS
    camera.contrast = CONTRAST
    camera.sharpness = SHARPNESS
    camera.video_stabilization = VIDEO_STABILIZATION
    camera.hflip = False
    camera.vflip = False

    #warm-up time to camera to set its initial settings
    time.sleep(2)

    camera.exposure_mode = EXPOSURE_MODE
    camera.awb_mode = AWB_MODE
    camera.awb_gains = AWB_GAINS

    #time to let camera change parameters according to exposure and AWB
    time.sleep(2)

    #switch off the exposure since the camera has been set now
    camera.exposure_mode = 'off'

    output = TimestampOutput(camera, VIDEO_FILE_NAME, TIMESTAMP_FILE_NAME, FLIPPER_FILE_NAME)

    GPIO.add_event_callback(pin_flipper, output.flipper_timestamps_write)
    try:
        camera.start_preview()
        # Construct an instance of our custom output splitter with a filename  and a connected socket
        print('Starting Recording')
        camera.start_recording(output, format='h264')
        print('Started Recording')
        camera.annotate_text_size = 10

        last_frame = 0
        while True:
            camera.wait_recording(0.005)
            frame = output._timestamps[-1][0]
            if frame != None:
                if frame > last_frame:
                    # a new frame was detected and the time stamp is not NONE
                    camera.annotate_text = str(frame) + "; " + dt.datetime.now().strftime("%H:%M:%S.%f")
                    last_frame = frame

    except Exception as e:
        output.close()
        print(e)
    finally:
        output.close()
        print('Output File Closed')
        GPIO.cleanup()
