#!/usr/bin/env python3

# contrl_acquisition.py
# script run and control over video acquisition

# necessary import
#import argparse
import os
from time import sleep

# parse the argument with argparse
#parser = argparse.ArgumentParser()
#parser.add_argument("-hr", "--hours", type=int, help="number of hours to record")
#parser.add_argument("-m", "--minutes", type=int, help="number of minutes to record")
#parser.add_argument("-s", "--seconds", type=int, help="number of seconds to record")
#
#args = parser.parse_args()

# integrate hours + minutes + seconds into the same unit seconds
#runningTimeHours = float(args.hours)
#runningTimeMinutes = float(args.minutes)
#runningTimeSeconds = float(args.seconds)
#
#totalRunningTime = runningTimeHours*60*60 + runningTimeMinutes*60 + runningTimeSeconds
duration = int(input("Enter the time in seconds: "))

#command_line_start = "nohup start_acquisition.py"
#command_line_end = "stop_acquisition"
os.system("python3 /home/pi/PicameraPaper/PicameraVideoAcquisitionScripts/StartAcquisition_skip_3.py /home/pi/video/test &")
sleep(duration + 4)
os.system("/home/pi/PicameraPaper/PicameraVideoAcquisitionScripts/stop_acquisition.sh")
