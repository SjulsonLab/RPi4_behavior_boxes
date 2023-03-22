# calibrate.py
"""
author: tian qiu
date: 2023-03-22
name: calibrate.py
goal: calibrating the the pump and log the data entry
description:

"""
from datetime import datetime
import io
from subprocess import check_output
from gpiozero import LED

datestr = str(datetime.now().strftime("%Y-%m-%d"))
timestr = str(datetime.now().strftime('%H%M%S'))
calibrator = str(input("Who is calibrating the pump? (Enter your name)"))
box_number = check_output(['hostname', '-I']).decode('ascii')
base_path = "/home/pi/experiment_info/calibration_info/"
calibration_filename = base_path + "calibration_box" + str(box_number) + "_" + str(
    calibrator) + "_" + datestr + timestr + '.csv'
# initiate the calibration list for logging at the end
calibration_log = []  # initiate calibration list for appending


def calibration_flush(calibration_filename, calibration_log):
    print("Flushing: " + calibration_filename)
    with io.open(calibration_filename, 'w') as f:
        f.write('pump_number, on_time, off_time, iteration, weight_tube, weight_total, weight_fluid\n')
        for entry in calibration_log:
            f.write('%f, %f, %f, %f, %f, %f, %f\n' % entry)


class Pump(object):  # specifically for calibration, different from the behavbox pump object
    def __init__(self):
        self.pump1 = LED(19)
        self.pump2 = LED(20)
        self.pump3 = LED(21)
        self.pump4 = LED(7)
        self.pump_air = LED(8)
        self.pump_vacuum = LED(25)

    def reward(self, which_pump, on_time, off_time, iteration):
        if which_pump == "1":
            self.pump1.blink(on_time, off_time, iteration)
            print("pump1, " + str(on_time) + str(off_time) + str(iteration))
        elif which_pump == "2":
            self.pump2.blink(on_time, off_time, iteration)
            print("pump2, " + str(on_time) + str(off_time) + str(iteration))
        elif which_pump == "3":
            self.pump3.blink(on_time, off_time, iteration)
            print("pump3, " + str(on_time) + str(off_time) + str(iteration))
        elif which_pump == "4":
            self.pump4.blink(on_time, off_time, iteration)
            print("pump4, " + str(on_time) + str(off_time) + str(iteration))


# initiate pump
pump = Pump()

while True:
    pump_number = int(input("Pump Number: "))  # user inputs the pump number they intend to calibrate at the moment
    on_duration = float(input("on_time: "))
    off_duration = float(input("off_time: "))
    pulse_time = float(input("iteration: "))
    weight_tube = float(input("weight_tube: "))
    # deliver the water using the pump object
    pump.reward(pump_number, on_duration, off_duration, pulse_time)
    print("Please go weight the container with the liquid!\n")
    weight_total = float(input("weight_total: "))
    weight_fluid = weight_total - weight_tube
    calibration_log.append(
        (pump_number, on_duration, off_duration,
         pulse_time, weight_tube, weight_total, weight_fluid)
    )
    abort_or_not = str(input("Abort the program?(Y/N) \n")).upper()
    if abort_or_not == 'Y':
        break

print("Flushing the calibration data ...\n")
calibration_flush(calibration_filename, calibration_log)

print("DONE")
