#!/bin/bash
# $1 is the video output directory, $2 is the file basename

if [ ! -d "$1" ]; then
    echo "Creating directory $1"
    mkdir -p "$1"
fi

echo "Starting video log"
date >> "$1/videolog.log"

echo "Starting video acquisition"
nohup ./start_acquisition.py "$2" >> "$1/videolog.log" 2>&1 &

exit 0