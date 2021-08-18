#!/usr/bin/env python3
import signal
import sys
from picamera import PiCamera
from datetime import datetime as dt

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
# this function is called when the program receives a SIGINT
def signal_handler(signum, frame):
    print("SIGINT detected")
    camera.stop_recording(video_name)
    print("Camera stopped recording.")
    logfile.close()
    print("Log file stopped logging.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
file_name = sys.argv[1]

video_name = file_name + '.h264'
logfile = open(file_name + '.txt', 'a')

camera = PiCamera()
camera.start_preview()
camera.start_recording(video_name)

last_frame = -1

while True:
    camera.wait_recording(0.005)
    frame = camera.frame
    if frame.index > last_frame and frame.timestamp != None:  # a new frame was detected and the time stamp is not NONE
        #camera.annotate_text = str(frame.index) + "; " + dt.now().strftime("%H:%M:%S.%f")
        logfile.write(str(frame.index) + ';' + str(frame.timestamp) + '\n')
        last_frame = frame.index
