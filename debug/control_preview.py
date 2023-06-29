# control_preview.py
# This script ssh into box_video to start preview or stop preview
import sys
import os
from time import sleep

IP_address_video = sys.argv[1]
duration = int(input("How long do you want to preview? (in sec, int. only)"))

os.system("ssh pi@" + IP_address_video + " 'nohup /home/pi/RPi4_behavior_boxes/start_preview.py'")
sleep(duration)
print("Stopping the preview")
os.system("ssh pi@" + IP_address_video + " /home/pi/RPi4_behavior_boxes/stop_preview.sh")