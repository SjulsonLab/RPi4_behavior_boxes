import RPi.GPIO as GPIO
import time
import threading
import concurrent.futures

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)

# Set up the GPIO pin as an input
pin_flipper = 4
GPIO.setup(pin_flipper, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
previous_state = GPIO.input(pin_flipper)


class FlipperInput:
    def __init__(self, pin_number):
        self.pin_number = pin_number
        self.flip_state = GPIO.input(pin_number)
        print("Start state is {}".format(previous_state))
        self._flipper_timestamps = []
        self.flip_thread = None
        self.event_thread = None
        self._stop_flag = False
        self.state_change = threading.Event()
        # GPIO.add_event_detect(pin_number, GPIO.BOTH, bouncetime=100)

    def get_flipper_timestamps(self):
        return self._flipper_timestamps

    def set_flipper_timestamps(self, timestamps):
        self._flipper_timestamps = timestamps

    def GPIO_loop(self, bouncetime=100):
        while True:
            cur_state = GPIO.input(pin_flipper)
            if cur_state != self.flip_state:
                if cur_state == GPIO.HIGH:
                    print("GPIO pin is HIGH")
                else:
                    print("GPIO pin is LOW")
                self.flip_state = cur_state
                self.state_change.set()
                time.sleep(bouncetime / 1000)  # Convert milliseconds to seconds
            else:
                self.state_change.clear()
                time.sleep(.001)  # Sleep for a short time to avoid busy waiting

            if self._stop_flag:
                print("Stopping GPIO loop")
                break

    def event_loop(self):
        while True:
            if self.state_change.is_set():
                self.flipper_callback()
                self.state_change.clear()
            else:
                time.sleep(0.001)

            if self._stop_flag:
                print("Stopping event loop")
                break

    def flipper_callback(self):
        self._flipper_timestamps.append((self.flip_state, time.time()))
        print(self.flip_state, time.time())
        # print(str(self._flipper_timestamps))

    def start_flipper_thread(self):
        if self.flip_thread is None:
            self.flip_thread = threading.Thread(target=self.GPIO_loop)
            self.event_thread = threading.Thread(target=self.event_loop)
            self.event_thread.start()
            self.flip_thread.start()
        else:
            print("Flipper thread already running")

    def close_threads(self):
        print("Closing threads")
        self._stop_flag = True
        if self.flip_thread is not None:
            self.flip_thread.join()
            self.flip_thread = None
        if self.event_thread is not None:
            self.event_thread.join()
            self.event_thread = None


flipper = FlipperInput(pin_flipper)
try:
    # Start the GPIO loop in a separate thread
    flipper.start_flipper_thread()
    tstart = time.perf_counter()
    while True:
        # do pseudo work
        time.sleep(1/60)  # 60 FPS

        if time.perf_counter() - tstart >= 1:
            print("Flipper timestamps: {}".format(flipper.get_flipper_timestamps()))
            # Wait for 20 milliseconds before checking again
            time.sleep(0.02)

except KeyboardInterrupt:
    # Clean up GPIO settings before exiting
    flipper.close_threads()
    GPIO.cleanup()

