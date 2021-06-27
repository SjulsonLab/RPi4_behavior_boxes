from test_session_info import test_session_info
import socket
import os
import time

session_info = test_session_info
# Get the ip address for SSH into different behavioral box
IP_address = socket.gethostbyname(socket.gethostname() + ".local")
IP_address_video_list = list(IP_address)
IP_address_video_list[-3] = "2"
IP_address_video = "".join(IP_address_video_list)

# def video_start

dir_name = session_info['dir_name']
basename = session_info['basename']
file_name = dir_name + "/" + basename

os.system("ssh pi@" + IP_address_video + " mkdir " + dir_name)
os.system("ssh pi@" + IP_address_video + " 'date >> ~/videolog.log' ") # I/O redirection
tempstr = (
        "ssh pi@" + IP_address_video + " 'nohup /home/pi/RPi4_behavior_boxes/record_video_test_001.py "
        + file_name
        + " >> " + file_name + ".log 2>&1 & ' " # file descriptors
)

#start recording
os.system(tempstr)

#delay
time.sleep(6)

os.system("ssh pi@" + IP_address_video + " /home/pi/RPi4_behavior_boxes/stop_video_test_001")
time.sleep(2)
hostname = socket.gethostname()
print("Moving video files from " + hostname + "video to " + hostname + ":")

base_dir = '/mnt/hd/'
hd_dir = base_dir + basename
os.mkdir(hd_dir)

# Move the video + log from the box_video SD card to the box_behavior external hard drive
os.system(
    "rsync -av --progress --remove-source-files pi@" + IP_address_video + ":" + dir_name + " "  # this could be a problem .avi
    + hd_dir
)