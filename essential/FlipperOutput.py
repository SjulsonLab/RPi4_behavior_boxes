from gpiozero import DigitalOutputDevice
from threading import Thread, Event
import io
import time
import random


class FlipperOutput(DigitalOutputDevice):
    def __init__(self, session_info, pin=None):
        super(FlipperOutput, self).__init__(pin=pin)
        try:
            self.session_info = session_info
        except:
            self.close()
            raise
        # Additional properties and methods
        self._flip_thread = None
        self._running = False

        self._flipper_file = self.session_info['flipper_filename'] + '.csv'
        self._flipper_timestamp = []

    def flip(self, time_min=0.5, time_max=2, n=None, background=True):
        self._stop_flip()
        self._running = True
        self._flip_thread = Thread(
            target=self._flip_device, args=(time_min, time_max, n)
        )
        self._flip_thread.stop_flag = Event()
        self._flip_thread.start()
        if not background:
            self._flip_thread.join()
            self._flip_thread = None

    def close(self):
        try:
            print("Attempting to close the flipper thread!")
            self._stop_flip()
            self.off()
            self.flipper_flush()
            # super().close()

        except Exception as e:
            print("Failed to close the flipper thread!")
            print(e)

    def _stop_flip(self):
        print("Entered _stop_flip")
        self._running = False
        self._flip_thread.stop_flag.set()
        self._flip_thread.join(5)  # shouldn't have to wait more than 5 seconds
        if self._flip_thread.is_alive():
            raise Exception("Flipper thread not closed")
        else:
            print("Flipper thread closed!")
            self._flip_thread = None

    def _flip_device(self, time_min, time_max, n):
        while self._running:
            on_time = round(random.uniform(time_min, time_max), 3)
            off_time = round(random.uniform(time_min, time_max), 3)

            self._write(True)
            pin_state = self.is_active
            timestamp = (pin_state, time.time())
            self._flipper_timestamp.append(timestamp)
            if self._flip_thread.stop_flag.wait(on_time):
                break

            self._write(False)
            pin_state = self.is_active
            timestamp = (pin_state, time.time())
            self._flipper_timestamp.append(timestamp)
            if self._flip_thread.stop_flag.wait(off_time):
                break

    def flipper_flush(self):
        print("Flushing: " + self._flipper_file)
        with io.open(self._flipper_file, 'w') as f:
            f.write('pin_state, time.time()\n')
            for entry in self._flipper_timestamp:
                f.write('%f,%f\n' % entry)

        print("Flushed flipper timestamps to " + self._flipper_file)
