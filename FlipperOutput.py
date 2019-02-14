from gpiozero import OutputDevice
import time

class FlipperOutput(OutputDevice):
    def __init__(self, session_info, pin=None):
        super(FlipperOutput, self).__init__(pin = pin)
        try:
            self.session_info = session_info
        except:
            self.close()
            raise
        # Additional properties and methods
        self._flip_thread = None
        self._controller = None # what is this?
        self._flipper_file = self.session_info['flipper_filename']
        self._flipper_timestamp = []

    def flip(self, time_min=0.5, time_max=2, n=None, background=True):
        self._stop_flip()
        self._flip_thread = GPIOThread(
            self._flip_device, (time_min, time_max, n)
        )
        self._flip_thread.start()
        if not background:
            self._flip_thread.join()
            self._flip_thread = None

    def _stop_flip(self):
        if getattr(self, '_controller', None):
            self._controller._stop_flip(self)
        self._controller = None
        self.flipper_flush()

        if getattr(self, '_flip_thread', None):
            self._flip_thread.stop()
        self._flip_thread = None

    def _flip_device(self, time_min, time_max, n):
        iterable = repeat(0) if n is None else repeat(0, n)
        for _ in iterable:
            self._write(True)
            on_time = round(random.uniform(time_min, time_max), 3)
            off_time = round(random.uniform(time_min, time_max), 3)
            if self._flip_thread.stopping.wait(on_time):
                pin_state = True
                self._flipper_timestamp.append((pin_state, time.time(), time.clock_gettime(time.CLOCK_REALTIME)))
                break
            if self._flip_thread.stopping.wait(off_time):
                pin_state = False
                self._flipper_timestamp.append((pin_state, time.time(), time.clock_gettime(time.CLOCK_REALTIME)))
                break

    def flipper_flush(self):
        with io.open(self._flipper_file, 'w') as f:
            f.write('pin_tate, time.time(), clock_realtime\n')
            for entry in self._flipper_timestamp:
                f.write('%f,%f,%f\n' % entry)
