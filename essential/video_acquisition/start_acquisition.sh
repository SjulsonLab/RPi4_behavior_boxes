#!/bin/bash
# $1 is the video IP address $2 is the video output directory, $3 is the file basename

ssh "pi@$1"

if [ ! -d "$1" ]; then
    echo "Creating directory $2"
    mkdir -p "$2"
fi

echo "Starting video log"
date >> "$2/videolog.log"

echo "Starting video acquisition"
nohup /home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition.py "$3" >> "$2/videolog.log" 2>&1 &

exit 0
