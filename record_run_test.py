from fake_session_info import fake_session_info
import socket
import os
import time

session_info = fake_session_info
# Get the ip address for SSH into different behavioral box
IP_address = socket.gethostbyname(socket.gethostname() + ".local")
IP_address_video_list = list(IP_address)
IP_address_video_list[-3] = "2"
IP_address_video = "".join(IP_address_video_list)

# def video_start


dir_name = session_info['dir_name']
os.system("ssh pi@" + IP_address_video + " mkdir " + dir_name)
os.system("ssh pi@" + IP_address_video + " 'date >> ~/videolog.log' ") # I/O redirection
tempstr = (
        "ssh pi@" + IP_address_video + " 'nohup /home/pi/RPi4_behavior_boxes/record_video_test.py "
        + session_info["mouse_name"]
        + " >> " + session_info['dir_name'] + "/" + session_info['basename'] + ".log 2>&1 & ' " # file descriptors
)

#start recording
os.system(tempstr)

#delay
time.sleep(10)

os.system("ssh pi@" + IP_address_video + " /home/pi/RPi4_behavior_boxes/stop_video_test")
time.sleep(2)
print("video recording ended!")
# hostname = socket.gethostname()
# print("Moving video files from " + hostname + "video to " + hostname + ":")

# base_dir = '/mnt/hd/'
# path = os.path.join(base_dir, session_info['basename'])
#
# # Move the video from the box_video SD card to the box_behavior external hard drive
# os.system(
#     "rsync -av --progress --remove-source-files pi@" + IP_address_video + ":" + session_info['dir_name'] + "/*.h264 "  # this could be a problem .avi
#     + path
# )
#
# # Move the video log from the box_video SD card to the box_behavior external hard drive
# os.system(
#     "rsync -av --progress --remove-source-files pi@" + IP_address_video + ":" + session_info["dir_name"] + "/*.log "
#     + path
# )
