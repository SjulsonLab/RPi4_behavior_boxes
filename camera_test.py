from picamera import PiCamera
from time import sleep
from datetime import datetime

"""
# for usb testing
import os

file_root = '/media/pi'
file = os.listdir(file_root)[-1]
file_path = os.path.join(file_root, file) + '/'
"""

# for external hard drive
file_path = '/mnt/hd/'

name = input("Enter the mouse ID: ")
timestamp = datetime.utcnow().strftime('%Y-%m-%d-%H%M%S')
file_name = file_path + name + timestamp + '.h264'
duration = int(input("Enter the time in seconds: "))

camera = PiCamera()
camera.start_preview()
camera.start_recording(file_name)

sleep(duration)

camera.stop_recording()
camera.stop_preview()