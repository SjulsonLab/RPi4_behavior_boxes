#!/bin/bash

# the user's crontab that runs daily at 3AM
echo "user crontab run at " `date`
cd /home/pi/RPi4_behavior_boxes  && git checkout main && git pull origin main

#rsync --ignore-existing -raz /mnt/hd pi@192.168.1.90:~/videos
