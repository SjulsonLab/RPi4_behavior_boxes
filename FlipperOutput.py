import RPi.GPIO as GPIO
from gpiozero import DigitalOutputDevice
from threading import Thread, Event
from itertools import repeat
import io
import time
import random

class FlipperOutput(DigitalOutputDevice):
    def __init__(self, session_info, pin=None):
        super(FlipperOutput, self).__init__(pin = pin)
        try:
            self.session_info = session_info
        except:
            self.close()
            raise
        # Additional properties and methods
        self._flip_thread = None
        # self._controller = None # what is this?
        self._flipper_file = self.session_info['flipper_filename'] + self.session_info['datetime'] + '.csv'
        self._flipper_timestamp = []

    def flip(self, time_min=0.5, time_max=2, n=None, background=True):
        self._stop_flip()
        self._flip_thread = Thread(
            target=self._flip_device, args=(time_min, time_max, n)
        )
        self._flip_thread.stopping = Event()
        # self._flip_thread.daemon = True
        self._flip_thread.start()
        if not background:
            self._flip_thread.join()
            self._flip_thread = None

    def close(self):
        # self._flip_thread.stopping.set()
        print("Attempts to close!")
        # self._flip_thread.join() # joining of the thread prevented the rest of the stop code
        self._flip_thread = None
        print("Attempts to stop!")
        self._stop_flip()
        self.flipper_flush()
        # super().close()

    def _stop_flip(self):
        # if getattr(self, '_controller', None):
        #     self._controller._stop_flip(self)
        # self._controller = None
        print("Entered _stop_flip")
        if getattr(self, '_flip_thread', None):
            # self._flip_thread.join(5)
            self._flip_thread.stop()
            # self.flipper_flush()
        self._flip_thread = None

    def _flip_device(self, time_min, time_max, n):
        iterable = repeat(0) if n is None else repeat(0, n)
        for _ in iterable:
            if self._flip_thread.stopping is not None:
                # self._flip_thread.stopping.clear()
                on_time = round(random.uniform(time_min, time_max), 3)
                off_time = round(random.uniform(time_min, time_max), 3)

                self._write(True)
                pin_state = self.is_active
                timestamp = (pin_state, time.time())
                print(str(timestamp))
                self._flipper_timestamp.append(timestamp)
                if self._flip_thread.stopping.wait(on_time):
                    break

                self._write(False)
                pin_state = self.is_active
                timestamp = (pin_state, time.time())
                print(str(timestamp))
                self._flipper_timestamp.append(timestamp)
                if self._flip_thread.stopping.wait(off_time):
                    break


    def flipper_flush(self):
        print(self._flipper_file)
        with io.open(self._flipper_file, 'w') as f:
            f.write('pin_tate, time.time()\n')
            # for entry in self._flipper_timestamp:
            #     f.write('%f,%f\n' % entry)