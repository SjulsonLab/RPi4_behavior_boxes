#!/usr/bin/env python3

import signal
import sys
from picamera import PiCamera

# TODO: this needs to be a script that runs from the command line on either RPi
# connected to a behavior box, e.g.
#
# record_video.py mousename
#
# It should save the videos in /home/pi/Videos
# Note(shouldn't it saved in the external drive?)
# and it would create files called:
# mousename_2021-01-24_150723.avi   (the video)
# mousename_2021-01-24_150723.log   (frame timestamps)
#
# and when it receives a SIGINT (either a Ctrl-C or a kill -2) it would gracefully
# stop recording, close the files, and exit.
# function takes in the session information, and it uses the information
# to create directory and video file...

# for testing only
def signal_handler(signum, frame):
    # Call the video record function
    # Wait for an user-defined amount of time
    # Exit
    print("SIGINT detected")
    sys.exit(0)

file_name = sys.argv[1]

# for external hard drive
# base_dir = '/home/pi/video/'
# file_name = mouse_name + time_stamp
# path = os.path.join(base_dir, basename)
# os.mkdir(path)
# ic("Video directory '% s' created" % path)

video_name = file_name + '.h264'

camera = PiCamera()
camera.start_preview()
camera.start_recording(video_name)

signal.signal(signal.SIGINT, signal_handler)
signal.pause()
