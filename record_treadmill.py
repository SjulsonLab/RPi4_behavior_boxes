import signal
import sys
import datetime as dt
import io

import smbus
import time
import struct


# this function is called when the program receives a SIGINT
def signal_handler(signum, frame):
    print("SIGINT detected")
    print("Saving the log file for the treadmill activity...")
    flush(threadmill_filename, treadmill_log)
    print("Existing the system!")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
# base_path = sys.argv[1]

base_path = "/mnt/hd/"
threadmill_filename = base_path + "treadmill" + "_output" + str(dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")) + ".csv"

bus_i2c = smbus.SMBus(1) # "On all recent (since 2014) raspberries the GPIO pin's I2C device is /dev/i2c-1"
# This is the address we setup in the Arduino Program
address_i2c = 0x08


def dacval(bus, address):
    time.sleep(0.3)
    block = bus.read_i2c_block_data(address, 1)
    running_speed = struct.unpack("<f", bytes(block[:4]))[0]
    # velocity = struct.unpack("<l", bytes(block[:4]))[0]
    # distance = struct.unpack("<l", bytes(block[4:]))[0]
    # data = (velocity, distance)
    # print(str(data))
    # return data
    # print(str(block) + '/n')
    # print(str(bytes(block)) + '/n')
    print("Running speed: " + str(running_speed)) # for debug purpose
    return running_speed

# save the element list
def flush(filename, list):
    with io.open(filename, 'w') as f:
        f.write('time.time(), running_speed\n')
        for entry in list:
            f.write('%f, %f\n' % entry)

treadmill_log = []
delay = 0.3

while True:
    time.sleep(delay)
    running_speed = dacval(bus_i2c, address_i2c)
    treadmill_log.append(
        (time.time(),
        running_speed)
    )




"""
for each element in the element_list, calculate the consecutive differences
for the consecutive differences, we can yield a velocity of the displacment
And from the velocity of the displacement we can get the direction and the acceleration

The problem that need to take into consideration
"""