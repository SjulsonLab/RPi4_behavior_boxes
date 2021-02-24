import smbus
import time
import struct

bus = smbus.SMBus(0)
# This is the address we setup in the Arduino Program
address = 0x08


def dacval():
    time.sleep(1)
    block = bus.read_i2c_block_data(address,1)
    n = struct.unpack('<l',bytes(block[:4]))[0]
    dvl = n / 100
    while n!= -1:
        return dvl
