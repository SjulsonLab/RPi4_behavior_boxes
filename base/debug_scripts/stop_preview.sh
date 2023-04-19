#!/bin/bash

# the process number (or numbers) of currently-running sessions of start_preview.py
PROCNUM=`ps uax | grep -v grep | grep start_preview.py | tr -s " " | cut -d " " -f 2`

# this sends a SIGINT (equal to Ctrl-C) to record_video.py
echo stopvideo: sending SIGINT to process $PROCNUM
kill -2 $PROCNUM