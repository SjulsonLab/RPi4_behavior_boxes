import smbus
import time
import struct

# bus = smbus.SMBus(0)
bus = smbus.SMBus(1) # "On all recent (since 2014) raspberries the GPIO pin's I2C device is /dev/i2c-1"
# This is the address we setup in the Arduino Program
address = 0x08


def dacval(sm_bus, sender_address):
    time.sleep(1)
    block = sm_bus.read_i2c_block_data(sender_address, 1)
    n = struct.unpack("<l", bytes(block[:4]))[0]
    dvl = n / 100
    while n != -1:
        return dvl

while True:
    dvl_output = dacval(bus, address)
    print(str(dvl_output))