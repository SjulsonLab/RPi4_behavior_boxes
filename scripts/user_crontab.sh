#!/bin/bash

# the user's crontab that runs daily at 3AM
# echo "user crontab run at " `date`
REPO_DIR='/home/pi/RPi4_behavior_boxes'
cd REPO_DIR && git checkout season-crontab && git pull origin season-crontab
