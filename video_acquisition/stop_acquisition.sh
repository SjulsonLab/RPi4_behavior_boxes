#!/bin/bash

# Stop the old PiCamera acquisition process. No running process is treated as a
# successful stop because the camera is already closed from the user's point of view.

PROCESS_PATTERN='/home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition\.py'
PROCNUM=$(pgrep -f "$PROCESS_PATTERN")

if [ -z "$PROCNUM" ]; then
    echo "No running acquisition process found."
    exit 0
fi

echo "stop_acquisition: sending SIGINT to process(es) $PROCNUM"
kill -2 $PROCNUM

for _ in $(seq 1 50); do
    REMAINING=""
    for pid in $PROCNUM; do
        if kill -0 "$pid" 2>/dev/null; then
            REMAINING="$REMAINING $pid"
        fi
    done

    if [ -z "$REMAINING" ]; then
        exit 0
    fi
    sleep 0.1
done

echo "Hard-kill fallback used for acquisition process(es):$REMAINING"
kill -9 $REMAINING
exit 0
