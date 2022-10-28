#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 28 12:30:51 2022

@author: eliezyer

based on the BehavBox class
"""
import os
from colorama import Fore,Style
import time
import scipy
import socket
import pickle

class VideoCapture():
    """this class is to make video captures independently of the behavior box,
    this way we can record video in freely moving or sleep boxes using a simple
    Raspberry pi
    
    You have to provide several variables:
        IP_address_video: the host name of the RPi with camera, ip or hostname,
            for example 'sleepboxpi'
        video_name: name of the video file, example: B6_sleeprecording_20221028
        base_pi_dir: where in the pi to save your videos, I recommend you to
            create your own folder
        local_storage_dir: final destination where you want to save the videos
            to, ideally in a HDD in the computer where ephys is also stored.
            Usually is a windows computer. This has to be something like- 
            E:/MyProject/Session/
    
    """
    def __init__(self,IP_address_video,video_name,base_pi_dir,local_storage_dir):
            self.IP_address_video = IP_address_video
            self.basename = video_name
            self.base_dir = base_pi_dir
            self.local_storage_dir = local_storage_dir
        
    def video_preview_only(self):
            IP_address_video = self.IP_address_video
            
            try:
                os.system("ssh pi@" + IP_address_video + " pkill python")
                print(Fore.CYAN + "\nStart Previewing ..." + Style.RESET_ALL)
                print(Fore.RED + "\n CRTL + C to quit previewing" + Style.RESET_ALL)
                
                os.system("ssh pi@" + IP_address_video + " '/home/pi/RPi4_behavior_boxes/start_preview.py'")
                
                print(Fore.GREEN + "\nKilling the preview process." + Style.RESET_ALL)
                os.system("ssh pi@" + IP_address_video + " '/home/pi/RPi4_behavior_boxes/stop_preview.sh'")
                time.sleep(2)
                
            except Exception as error_message:
                print("It couldn't start the preview\n")
                print(str(error_message))
                
    def video_start(self):
            IP_address_video = self.IP_address_video
            dir_name = self.base_dir
            basename = self.basename
            hd_dir = self.local_storage_dir
            file_name = dir_name + "/" + basename
            # print(Fore.RED + '\nTEST - RED' + Style.RESET_ALL)
            # create directory on the external storage
            #os.mkdir(hd_dir)
    
            # Preview check per Kelly request
            print(Fore.YELLOW + "Killing any python process prior to this session!\n" + Style.RESET_ALL)
            try:
                os.system("ssh pi@" + IP_address_video + " pkill python")
                print(Fore.CYAN + "\nStart Previewing ..." + Style.RESET_ALL)
                print(Fore.RED + "\n CRTL + C to quit previewing and start recording" + Style.RESET_ALL)
    
                os.system("ssh pi@" + IP_address_video + " '/home/pi/RPi4_behavior_boxes/start_preview.py'")
                # Kill any python process before start recording
                print(Fore.GREEN + "\nKilling any python process before start recording!" + Style.RESET_ALL)
    
                os.system("ssh pi@" + IP_address_video + " pkill python")
                time.sleep(2)
    
                # Prepare the path for recording
                os.system("ssh pi@" + IP_address_video + " mkdir " + dir_name)
                os.system("ssh pi@" + IP_address_video + " 'date >> ~/video/videolog.log' ")  # I/O redirection
                tempstr = (
                        "ssh pi@" + IP_address_video + " 'nohup /home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition.py "
                        + file_name
                        + " >> ~/video/videolog.log 2>&1 & ' "  # file descriptors
                )
                # start the flipper before the recording start
                # initiate the flipper
                try:
                    self.flipper.flip()
                except Exception as error_message:
                    print("flipper can't run\n")
                    print(str(error_message))
    
                # start recording
                print(Fore.GREEN + "\nStart Recording!" + Style.RESET_ALL)
                os.system(tempstr)
    
                print(
                    Fore.RED + Style.BRIGHT + "Please check if the preview screen is on! Cancel the session if it's not!" + Style.RESET_ALL)
    
            except Exception as e:
                print(e)
    
    def video_stop(self):
            # Get the basename from the session information
            basename = self.basename
            dir_name = self.base_dir
            # Get the ip address for the box video:
            IP_address_video = self.IP_address_video
            try:
                # Run the stop_video script in the box video
                os.system(
                    "ssh pi@" + IP_address_video + " /home/pi/RPi4_behavior_boxes/video_acquisition/stop_acquisition.sh")
                time.sleep(2)
                
                hostname = socket.gethostname()
                print("Moving video files from " + hostname + "video to " + hostname + ":")
    
                # Create a directory for storage on the hard drive mounted on the box behavior
                hd_dir = self.local_storage_dir
    
                #scipy.io.savemat(hd_dir + "/" + basename + '_session_info.mat', {'session_info': self.session_info})
    
                #THIS PART SHOULD BE TRIGGERED BY THE USER, YOU DON'T WANT SEVERAL 
                #STUFF BEING COPIED INTO THE HARD DRIVE AT THE SAME TIME!
                
                # Move the video + log from the box_video SD card to the box_behavior external hard drive
                os.system(
                    "rsync -av --progress --remove-source-files pi@" + IP_address_video + ":" + dir_name + "/ "
                    + hd_dir
                )
                os.system(
                    "rsync -av --progress --remove-source-files pi@" + IP_address_video + ":~/video/*.log "
                    + hd_dir
                )
    
                os.system(
                    "rsync -arvz --progress --remove-source-files " + dir_name + "/ "
                    + hd_dir
                )
                print("rsync finished!")
                # print("Control-C to quit (ignore the error for now)")
            except Exception as e:
                print(e)