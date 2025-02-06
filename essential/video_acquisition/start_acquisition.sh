#!/bin/bash

# $1 is the video output directory, $2 is the file basename
echo "Starting video log"
date >> "$1/videolog.log"

echo "Starting video acquisition"
nohup ./start_acquisition.py "$2" >> "$1/videolog.log" 2>&1 &
