from gpiozero import DigitalOutputDevice
from threading import Thread, Event
import io
import time
import random


class FlipperOutput(DigitalOutputDevice):
    def __init__(self, session_info, pin=None):
        super(FlipperOutput, self).__init__(pin=pin)
        self._flip_thread = None
        self._running = False
        self._stop_flag = Event()
        self._flipper_filename = session_info['flipper_filename'] + '.csv'
        self._flipper_timestamp = []
        self.on()

        # barcode
        self.barcode_bit_time = .03
        self.barcode_init_time = .01
        self.barcode_bits = 32
        self.barcode = random.randint(0, 2**self.barcode_bits-1)
        self._barcode_fname = session_info['flipper_filename'] + '_barcode.txt'

    def flip(self, time_min=0.5, time_max=2, n=None, background=True):
        self._stop_flip()
        self._running = True
        self._stop_flag.clear()
        self._flip_thread = Thread(
            target=self._flip_device, args=(time_min, time_max, n)
        )

        print("Generating start barcode")
        self.generate_barcode()

        self._flip_thread.start()
        if not background:
            self._flip_thread.join()
            self._flip_thread = None

    def close(self):
        try:
            if self._flip_thread is not None:
                print("Attempting to close the flipper thread!")
                self._stop_flip()
                self.flipper_flush()
                # super().close()
            else:
                print("No flipper thread to close")

        except Exception as e:
            print("Failed to close the flipper thread!")
            print(e)

    def _stop_flip(self):
        print("Entered _stop_flip")
        if self._flip_thread is None:
            print("No flipper thread to stop")
            return

        self._running = False
        self._stop_flag.set()
        self._flip_thread.join(5)  # shouldn't have to wait more than 5 seconds
        if self._flip_thread.is_alive():
            raise Exception("Flipper thread not closed")
        else:
            print("Flipper thread is closed!")
            self._flip_thread = None

        print("Generating end barcode")
        self.generate_barcode()

    def _flip_device(self, time_min, time_max, n):
        while self._running:
            on_time = round(random.uniform(time_min, time_max), 3)
            off_time = round(random.uniform(time_min, time_max), 3)

            # self._write(True)
            self.on()
            # self.off()
            pin_state = self.is_active
            timestamp = (pin_state, time.time())
            self._flipper_timestamp.append(timestamp)
            if self._stop_flag.wait(on_time):
                # self._write(False)
                self.off()
                # self.on()
                break

            # self._write(False)
            self.off()
            # self.on()
            pin_state = self.is_active
            timestamp = (pin_state, time.time())
            self._flipper_timestamp.append(timestamp)
            if self._stop_flag.wait(off_time):
                break

    def flipper_flush(self):
        with io.open(self._flipper_filename, 'w') as f:
            f.write('pin_state, time.time()\n')
            for entry in self._flipper_timestamp:
                f.write('%f,%f\n' % entry)

        with io.open(self._barcode_fname, 'w') as f:
            f.write('Barcode: ' + str(self.barcode) + '\n')
            f.write('Bits: ' + str(self.barcode_bits) + '\n')
            f.write('Barcode bit time: ' + str(self.barcode_time) + '\n')
            f.write('Barcode init time: ' + str(self.barcode_init_time) + '\n')

        print("Flushed flipper timestamps to " + self._flipper_filename)

    def generate_barcode(self):
        self.barcode_wrapper_pulse()
        barcode_str = format(self.barcode, '0' + str(self.barcode_bits) + 'b')
        for bit in barcode_str:
            if int(bit) == 1:
                self.on()
            else:
                self.off()
            time.sleep(self.barcode_bit_time)
        self.barcode_wrapper_pulse()

    def barcode_wrapper_pulse(self):
        self.off()
        time.sleep(self.barcode_init_time)
        self.on()
        time.sleep(self.barcode_init_time)
        self.off()
        time.sleep(self.barcode_init_time)

        # self.on()
