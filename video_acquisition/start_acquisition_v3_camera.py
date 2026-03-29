#!/usr/bin/env python3

import io
import time
import datetime as dt
from picamera2 import Picamera2, Preview, MappedArray
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import FileOutput
import cv2
from libcamera import controls
from pprint import pprint
import sys
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
camId = str(sys.argv[2]) if len(sys.argv) > 2 else "0"

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

# overlay text for preview window timestamps
colour = (255, 255, 255)  # white
font = cv2.FONT_HERSHEY_SIMPLEX

# video, timestamps and ttl file name
video_dt = str(dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
# VIDEO_FILE_NAME = base_path + "_cam" + camId + "_output_" + video_dt + ".h264"
# TIMESTAMP_FILE_NAME = base_path + "_cam" + camId + "_timestamp_" + video_dt + ".csv"

# don't need to add new timestamps to file names, the base_path already includes a timestamp
VIDEO_FILE_NAME = base_path + "_cam" + camId + "_output.h264"
TIMESTAMP_FILE_NAME = base_path + "_cam" + camId + "_timestamp.csv"


# timestamp output object to save timestamps according to pi and TTL inputs received and write to file
class TimestampOutput(object):

    def __init__(self, timestamp_filename):
        self._timestampFile = timestamp_filename
        self._timestamps = []
        self._stop_flag = False

    def append_timestamps(self, request):
        cur_time = time.time()
        meta = request.get_metadata()
        # cur_time = dt.datetime.now(dt.timezone.utc)  # alternately use datetime module, which is a tad slower
        self._timestamps.append((
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
        txt = '{:.3f}; {}; {:.2f} fps'.format((meta['SensorTimestamp'] - self._timestamps[0][0]) / 1e9,
                                              strftime, framerate)
        with MappedArray(request, "main") as m:
            cv2.putText(m.array, txt, origin, font, scale, colour, thickness)

    def flush(self):
        with io.open(self._timestampFile, 'w') as f:
            f.write('Sensor Timestamp (ns),Frame Duration (ms),time.time()\n')
            for entry in self._timestamps:
                f.write('%f,%f,%f\n' % entry)

    def close_threads(self):
        print("Closing threads")
        self._stop_flag = True
        if self.flip_thread is not None:
            self.flip_thread.join()
            self.flip_thread = None
        if self.event_thread is not None:
            self.event_thread.join()
            self.event_thread = None

    def close(self):
        self.close_threads()
        self.flush()


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

# Picam2 has brightness, contrast, sharpness, saturation, exposure modes, awb_mode
# Picam2 does not have an image stabilization option
# hflip and vflip are Transforms now, both default to False
sensor_mode = 1
# Preview text settings
if sensor_mode == 0:
    origin = (0, 30)
    scale = 1
    thickness = 2
elif sensor_mode == 1:
    origin = (0, 50)
    scale = 2
    thickness = 4
elif sensor_mode == 2:
    origin = (0, 100)
    scale = 4
    thickness = 6

mode = camera.sensor_modes[sensor_mode]
config = camera.create_video_configuration(
    main={"size": (1024, 768)},  # preview size; can be set to same as sensor output size or smaller for faster preview performance
    sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']},
    controls={'FrameDurationLimits': (20000, 20000),  # 50 fps; set to (33333, 33333) for 30 fps
              'AeExposureMode': controls.AeExposureModeEnum.Normal,
              "AfMode": controls.AfModeEnum.Manual,  # for V3 camera; comment this out for HQ camera, which uses manual focus
              "LensPosition": 32}
)
# Lens position ranges from 0 (max focal distance) to 32 (min focal distance). 10 is good for general use, but for
# up-close eye recording you may want higher values
camera.align_configuration(config)
camera.configure(config)
print("Camera configuration aligned to {}".format(camera.video_configuration.size))

timestamps = TimestampOutput(TIMESTAMP_FILE_NAME)
camera.pre_callback = timestamps.append_timestamps
x, y, w, h = 100, 0, 1024, 768
camera.start_preview(Preview.DRM, x=x, y=y, width=w, height=h)
print(f"Using preview window x={x} y={y} w={w} h={h}")

with io.open(VIDEO_FILE_NAME, 'wb') as buffer:
    encoder = H264Encoder()
    output = FileOutput(file=buffer)
    try:
        print('Starting Recording')
        camera.start_recording(encoder, output, quality=Quality.VERY_HIGH)
        time.sleep(2)
        camera.set_controls({
            'AeEnable': False,
            'AwbEnable': False,
        })
        time.sleep(2)
        print('Started Recording')
        while True:
            # time.sleep(.0001)
            continue

    except Exception as e:
        camera.stop_recording()
        camera.stop_preview()
        timestamps.close_threads()
        print('Recording Stopped')
        print(e)

    finally:
        timestamps.close()
        sys.exit(0)
