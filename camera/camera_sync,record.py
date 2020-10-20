import RPi.GPIO as GPIO
from picamera import PiCamera
from time import sleep
import os
import csv
from datetime import datetime
camera = PiCamera()
# camera.resolution = (640, 480)
# camera.framerate = 90
camera.start_preview()
print("Check if the 0x36 address is exist")
os.system("i2cdetect -y 0")
camera.start_recording('/home/pi/Desktop/video.h264')
sleep(5)
print("Write i2c")
camera.exposure_mode="off"
os.system("i2cset -y 0 0x36 0x30 0x9802 w")
os.system("i2cset -y 0 0x36 0x3B 0x8100 w")
os.system("i2cset -y 0 0x36 0x3B 0x0207 w")
camera.exposure_mode="auto"
print("OK")
pin= 12
GPIO.setmode(GPIO.BOARD)
GPIO.setup(pin,GPIO.IN)


for i in range(10000):
# While True:
    output = []
    if (GPIO.input(pin) == True):
        value = 0
    else:
        value = 20
    output.append(value)
    with open('logs.csv', 'a') as csvfile:
        logcsv = csv.writer(csvfile, delimiter=',')
        logcsv.writerow([datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]] + output)   
#     sleep(1);
print("stop recording and preview")
camera.stop_recording()
camera.stop_preview()




      
