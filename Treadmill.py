"""
### Older version ###
import smbus
import time
import struct

# bus = smbus.SMBus(0)
bus = smbus.SMBus(1) # "On all recent (since 2014) raspberries the GPIO pin's I2C device is /dev/i2c-1"
# This is the address we setup in the Arduino Program
address = 0x08


def dacval():
    time.sleep(1)
    block = bus.read_i2c_block_data(address, 1)
    n = struct.unpack("<l", bytes(block[:4]))[0]
    dvl = n / 100
    while n != -1:
        return dvl
"""

import datetime as dt
import io
from threading import Thread, Event

import smbus
import time
import struct


def dacval(bus, address):
    # time.sleep(0.3)
    block = bus.read_i2c_block_data(address, 1)
    running_speed = struct.unpack("<f", bytes(block[:4]))[0]
    return running_speed


class Treadmill(object):
    def __init__(self, session_info):
        try:
            self.session_info = session_info
        except:
            self.close()
            raise

        self.bus = smbus.SMBus(1)  # "On all recent (since 2014) raspberries the GPIO pin's I2C device is /dev/i2c-1"
        # This is the address we setup in the Arduino Program
        self.address = 0x08
        self.treadmill_filename = self.session_info['basedir'] + "/" + self.session_info['basename'] + "/" + \
                                  "treadmill_output_" + self.session_info['basename'] + ".csv "
        print(self.treadmill_filename)
        self._dacval_thread = None

        self.treadmill_log = []
        self.delay = 0.3

    def start(self, background=True):
        self._stop_dacval()
        self._dacval_thread = Thread(target=self.run)
        self._dacval_thread.stopping = Event()
        self._dacval_thread.start()

        if not background:
            self._dacval_thread.join()
            self._dacval_thread = None

    def close(self):
        try:
            self._dacval_thread.stopping.set()
            print("Attempts to close the treadmill thread!")
            self._dacval_thread.join(5)
            self._dacval_thread = None
            self._stop_dacval()
            # self.off()
            self.treadmill_flush()
            # super().close()
        except:
            pass

    def _stop_dacval(self):
        print("Entered _stop_dacval")
        if getattr(self, '_stop_dacval', None):
            print("enter _stop_dacval.stop()")
            self._dacval_thread.stop()
        self._dacval_thread = None

    def run(self):
        while True:
            time.sleep(self.delay)
            running_speed = dacval(self.bus, self.address)
            self.treadmill_log.append(
                (time.time(),
                 running_speed)
            )

    # save the element list
    def treadmill_flush(self):
        with io.open(self.treadmill_filename, 'w') as f:
            f.write('time.time(), running_speed\n')
            for entry in self.treadmill_log:
                f.write('%f, %f\n' % entry)


"""
for each element in the element_list, calculate the consecutive differences
for the consecutive differences, we can yield a velocity of the displacment
And from the velocity of the displacement we can get the direction and the acceleration

The problem that need to take into consideration
"""
