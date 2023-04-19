#!/usr/bin/env python3

import signal
import sys
from picamera import PiCamera

def signal_handler(signum, frame):
    # Call the video record function
    # Wait for an user-defined amount of time
    # Exit
    print("SIGINT detected")
    camera.stop_preview()
    camera.close()
    sys.exit(0)

camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 30

camera.annotate_text = "PREVIEW ONLY"
camera.annotate_text_size = 60

camera.start_preview()

signal.signal(signal.SIGINT, signal_handler)
signal.pause()
