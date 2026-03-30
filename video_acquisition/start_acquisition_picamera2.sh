#!/bin/bash
# $1 is the video output directory, $2 is the file basename, $3 is the camera ID

if [ ! -d "$1" ]; then
    echo "Creating directory $1"
    mkdir -p "$1"
fi

PIDFILE="$1/acquisition.pid"
rm -f "$PIDFILE"

echo "Starting video log"
date >> "$1/videolog.log"

echo "Starting video acquisition"
#echo "nohup python /home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition_picamera2_fast.py \"$2\" \"$3\" >> \"$1/videolog.log\" 2>&1 &"
#nohup python /home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition_picamera2_fast.py "$2" "$3" >> "$1/videolog.log" 2>&1 &
#echo "nohup python /home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition_v3_camera.py \"$2\" \"$3\" >> \"$1/videolog.log\" 2>&1 &"
#nohup python /home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition_v3_camera.py "$2" "$3" >> "$1/videolog.log" 2>&1 &
echo "nohup python /home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition_v3_camera_fast.py \"$2\" \"$3\" \"$PIDFILE\" >> \"$1/videolog.log\" 2>&1 &"
nohup python /home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition_v3_camera_fast.py "$2" "$3" "$PIDFILE" >> "$1/videolog.log" 2>&1 &
ACQ_PID=$!
echo "$ACQ_PID" > "$PIDFILE"
echo "Acquisition PID: $ACQ_PID"

exit 0
