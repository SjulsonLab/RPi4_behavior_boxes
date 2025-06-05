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

while True:
    pump_number = str(input("Pump Number: "))  # user inputs the pump number they intend to calibrate at the moment
    on_time = float(input("on_time: "))
    off_time = float(input("off_time: "))
    pulse_time = int(input("iteration: "))
    weight_tube = float(input("weight_tube: "))

    if pump_number == "1":
        LED(19).blink(on_time, off_time, pulse_time)
        print("pump1, " + str(on_time) + str(off_time) + str(pulse_time))
    elif pump_number == "2":
        LED(20).blink(on_time, off_time, pulse_time)
        print("pump2, " + str(on_time) + str(off_time) + str(pulse_time))
    elif pump_number == "3":
        LED(21).blink(on_time, off_time, pulse_time)
        print("pump3, " + str(on_time) + str(off_time) + str(pulse_time))
    elif pump_number == "4":
        LED(7).blink(on_time, off_time, pulse_time)
        print("pump4, " + str(on_time) + str(off_time) + str(pulse_time))
    time.sleep((on_time+off_time)*pulse_time + 0.1)
    print("Please go weight the container with the liquid!\n")
    weight_total = float(input("weight_total: "))
    weight_fluid = weight_total - weight_tube
    print("Fluid weight = " + str(weight_fluid))
    abort_or_not = str(input("Abort the program?(Y/N) \n")).upper()
    if abort_or_not == 'Y':
        break

print("DONE")
