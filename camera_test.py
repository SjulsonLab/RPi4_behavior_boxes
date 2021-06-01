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


# class Camera(object):
# datestr = datetime.now().strftime("%Y-%m-%d")
# timestr = datetime.now().strftime('%H%M%S')
# full_module_name = 'session_info_' + datestr
# session_info = {}
# session_info['date'] = datestr
# session_info['time'] = timestr
# session_info['datetime'] = session_info['date'] + '_' + session_info['time']
# path = input("Enter the path to save the video(enter nothing if save in the current directory): ")
name = input("Enter the mouse ID: ")
timestamp = datetime.utcnow().strftime('%Y-%m-%d-%H%M%S')
file_name = file_path + name + timestamp + '.h264'
duration = int(input("Enter the time in seconds: "))

# with PiCamera() as camera:
#     # camera.resolution = (640, 480)
#     # camera.framerate = 90
#     camera.start_preview
#     camera.start_recording(file_name)
#
#     sleep(int(duration))
#     # camera.wait_recording(duration)
#
#     camera.stop_recording()
#     camera.stop_preview()

camera = PiCamera()
camera.start_preview()
camera.start_recording(file_name)

sleep(duration)

camera.stop_recording()
camera.stop_preview()