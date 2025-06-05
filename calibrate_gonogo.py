# calibrate.py
"""
author: tian qiu
date: 2023-03-22
name: calibrate.py
goal: calibrating the the pump and log the data entry
description:

"""
from datetime import datetime
from gpiozero import LED
import time

datestr = str(datetime.now().strftime("%Y-%m-%d"))
timestr = str(datetime.now().strftime('%H%M%S'))
on_time = float(input("on_time: "))
iteration = int(input("iteration: "))
weight_tube = float(input("weight_tube: "))

led1 = LED(19)

led1.blink(on_time,0.1,iteration)
led1.close()

print("DONE!")
print("Please go weight the container with the liquid!\n")
weight_total = float(input("weight_total: "))
weight_fluid = weight_total - weight_tube
print("Fluid weight = " + str(weight_fluid))
