#!/bin/bash

# the process number (or numbers) of currently-running sessions of start_acquisition.py
PROCNUM=`ps uax | grep -v grep | grep StartAcquisition_skip_3.py | tr -s " " | cut -d " " -f 2`

# this sends a SIGINT (equal to Ctrl-C) to start_acquisition.py
echo stop_acquisition: sending SIGINT to process $PROCNUM
kill -2 $PROCNUM
