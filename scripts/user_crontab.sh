#!/bin/bash

# the user's crontab that runs daily at 3AM
echo "user crontab run at " `date`
cd /home/pi/RPi4_behavior_boxes  && git checkout main && git pull origin main
git checkout video && git pull origin video
git checkout video_sync && git pull origin video_sync
