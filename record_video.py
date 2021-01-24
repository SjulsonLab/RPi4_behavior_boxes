#!/usr/bin/env python3

# TODO: this needs to be a script that runs from the command line on either RPi 
# connected to a behavior box, e.g.
#
# record_video.py mousename dirname
#
# and it would create files called:
# mousename_2021-01-24_150723.avi   (the video)
# mousename_2021-01-24_150723.log   (frame timestamps)
#
# and when it receives a SIGINT (either a Ctrl-C or a kill -1) it would gracefully
# stop recording and exit.



