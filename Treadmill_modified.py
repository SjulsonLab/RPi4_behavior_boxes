import smbus
import time
import struct

# bus = smbus.SMBus(0)
bus_i2c = smbus.SMBus(1) # "On all recent (since 2014) raspberries the GPIO pin's I2C device is /dev/i2c-1"
# This is the address we setup in the Arduino Program
address_i2c = 0x08


def dacval(bus, address):
    time.sleep(0.3)
    block = bus.read_i2c_block_data(address, 1)
    # n = struct.unpack("<l", bytes(block[:4]))[0]
    n = struct.unpack("<f", bytes(block[:4]))[0]
    # print(str(n))
    return n

while True:
    dacval(bus_i2c, address_i2c)