from picamera import PiCamera
from time import sleep
from datetime import datetime
camera = PiCamera()
# camera.resolution = (640, 480)
# camera.framerate = 90
name = input("Enter the mouse ID: ")
timestamp = datetime.utcnow().strftime('%Y-%m-%d-%H%M%S')
file_name = name + timestamp + '.h264' 

duration = input("Enter the time in seconds: ") 


camera.start_preview()
camera.start_recording(file_name)

sleep(int(duration))

camera.stop_recording()
camera.stop_preview()




      
