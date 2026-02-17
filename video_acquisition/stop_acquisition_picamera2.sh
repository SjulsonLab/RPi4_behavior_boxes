#!/bin/bash

# Find running acquisition scripts (normal or fast version)
PROCNUM=$(pgrep -f 'start_acquisition_picamera2(_fast)?\.py')

if [ -n "$PROCNUM" ]; then
    echo "stop_acquisition: sending SIGINT to process(es) $PROCNUM"
    kill -2 $PROCNUM
else
    echo "No running acquisition process found."
fi
