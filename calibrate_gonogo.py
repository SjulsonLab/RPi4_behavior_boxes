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
pump_number = str(input("Pump Number: "))  # user inputs the pump number they intend to calibrate at the moment
on_time = float(input("on_time: "))
off_time = float(input("off_time: "))
iteration = int(input("iteration: "))
weight_tube = float(input("weight_tube: "))

for i in range(iteration):
    print("reward delivery " + str(i))
    if pump_number == "1":
        LED(19).blink(on_time, 0.1, 1)
        time.sleep(off_time)
    elif pump_number == "2":
        time.sleep(off_time)
    elif pump_number == "3":
        time.sleep(off_time)
    elif pump_number == "4":
        time.sleep(off_time)

print("DONE!")
print("Please go weight the container with the liquid!\n")
weight_total = float(input("weight_total: "))
weight_fluid = weight_total - weight_tube
print("Fluid weight = " + str(weight_fluid))
