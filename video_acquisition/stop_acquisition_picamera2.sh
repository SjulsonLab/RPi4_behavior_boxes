#!/bin/bash

# Get the process number(s) of currently-running sessions of start_acquisition_picamera2.py
PROCNUM=$(ps uax | grep -v grep | grep start_acquisition_picamera2.py | awk '{print $2}')

# Check if PROCNUM is not empty
if [ -n "$PROCNUM" ]; then
    # Send a SIGINT (equivalent to Ctrl-C) to start_acquisition_picamera2.py
    echo "stop_acquisition: sending SIGINT to process $PROCNUM"
    kill -2 $PROCNUM
else
    echo "No running process found for start_acquisition_picamera2.py"
fi
