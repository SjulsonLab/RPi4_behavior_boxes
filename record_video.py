#!/usr/bin/env python3

import signal
import sys
import os
from icecream import ic


# TODO: this needs to be a script that runs from the command line on either RPi
# connected to a behavior box, e.g.
#
# record_video.py mousename
#
# It should save the videos in /home/pi/Videos
#
# and it would create files called:
# mousename_2021-01-24_150723.avi   (the video)
# mousename_2021-01-24_150723.log   (frame timestamps)
#
# and when it receives a SIGINT (either a Ctrl-C or a kill -2) it would gracefully
# stop recording, close the files, and exit.

# for testing only
def signal_handler(sig, frame):
    ic("SIGINT detected")
    os.system("touch /home/pi/Videos/fakevideo.avi")
    #    os.system('touch /home/pi/Videos/fakevideo.log')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.pause()
