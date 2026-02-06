import time
import threading
from mock_gpiozero.pin_logger import pin_logger

# Global registry of all Button instances, keyed by pin number.
# Used by EventSimulator and KeyboardSimulator to inject events.
_button_registry = {}


class LED:
    """Mock gpiozero.LED — digital output device."""

    def __init__(self, pin):
        self.pin = pin
        self._value = 0
        self._blink_thread = None
        self._blink_stop = threading.Event()
        pin_logger.log(pin, 'LED', 'created')

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = val
        pin_logger.log(self.pin, 'LED', 'value={}'.format(val))

    def on(self):
        self._stop_blink()
        self._value = 1
        pin_logger.log(self.pin, 'LED', 'on')

    def off(self):
        self._stop_blink()
        self._value = 0
        pin_logger.log(self.pin, 'LED', 'off')

    def blink(self, on_time=1, off_time=1, n=None):
        """Blink the LED. Runs in a daemon thread to simulate real timing."""
        self._stop_blink()
        self._blink_stop.clear()
        pin_logger.log(self.pin, 'LED',
                       'blink(on={}, off={}, n={})'.format(on_time, off_time, n))

        def do_blink():
            count = 0
            while not self._blink_stop.is_set():
                self._value = 1
                if self._blink_stop.wait(on_time):
                    break
                self._value = 0
                count += 1
                if n is not None and count >= n:
                    break
                if self._blink_stop.wait(off_time):
                    break

        self._blink_thread = threading.Thread(target=do_blink, daemon=True)
        self._blink_thread.start()

    def _stop_blink(self):
        self._blink_stop.set()
        if self._blink_thread is not None:
            self._blink_thread.join(timeout=2)
            self._blink_thread = None

    def close(self):
        self._stop_blink()
        self.off()


class PWMLED:
    """Mock gpiozero.PWMLED — PWM output device with duty cycle 0-1."""

    def __init__(self, pin, frequency=100):
        self.pin = pin
        self.frequency = frequency
        self._value = 0
        pin_logger.log(pin, 'PWMLED', 'created(freq={})'.format(frequency))

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = max(0.0, min(1.0, float(val)))
        pin_logger.log(self.pin, 'PWMLED', 'value={}'.format(self._value))

    def on(self):
        self._value = 1.0
        pin_logger.log(self.pin, 'PWMLED', 'on')

    def off(self):
        self._value = 0.0
        pin_logger.log(self.pin, 'PWMLED', 'off')

    def close(self):
        self.off()


class Button:
    """Mock gpiozero.Button — input device with press/release callbacks.

    Accepts positional args to match the codebase usage:
        Button(pin, pull_up, active_state)
    e.g. Button(5, None, True)
    """

    def __init__(self, pin=None, pull_up=True, active_state=None,
                 bounce_time=None, hold_time=1, hold_repeat=False,
                 pin_factory=None):
        self.pin = pin
        self.pull_up = pull_up
        self.active_state = active_state
        self._is_pressed = False
        self._when_pressed = None
        self._when_released = None
        self._press_event = threading.Event()
        self._release_event = threading.Event()
        # Register so EventSimulator / KeyboardSimulator can find us
        _button_registry[pin] = self
        pin_logger.log(pin, 'Button',
                       'created(pull_up={}, active_state={})'.format(
                           pull_up, active_state))

    # --- callback properties ---

    @property
    def when_pressed(self):
        return self._when_pressed

    @when_pressed.setter
    def when_pressed(self, callback):
        self._when_pressed = callback

    @property
    def when_released(self):
        return self._when_released

    @when_released.setter
    def when_released(self, callback):
        self._when_released = callback

    # --- state ---

    @property
    def is_pressed(self):
        return self._is_pressed

    # --- blocking waits ---

    def wait_for_press(self, timeout=None):
        self._press_event.clear()
        self._press_event.wait(timeout)

    def wait_for_release(self, timeout=None):
        self._release_event.clear()
        self._release_event.wait(timeout)

    # --- simulation API (called by EventSimulator / KeyboardSimulator) ---

    def simulate_press(self):
        """Simulate the button being pressed. Fires when_pressed callback."""
        self._is_pressed = True
        self._press_event.set()
        pin_logger.log(self.pin, 'Button', 'pressed')
        if self._when_pressed is not None:
            self._when_pressed()

    def simulate_release(self):
        """Simulate the button being released. Fires when_released callback."""
        self._is_pressed = False
        self._release_event.set()
        pin_logger.log(self.pin, 'Button', 'released')
        if self._when_released is not None:
            self._when_released()

    def close(self):
        _button_registry.pop(self.pin, None)


class DigitalOutputDevice:
    """Mock gpiozero.DigitalOutputDevice — base class for FlipperOutput."""

    def __init__(self, pin=None):
        self.pin = pin
        self._active = False
        pin_logger.log(pin, 'DigitalOutputDevice', 'created')

    @property
    def is_active(self):
        return self._active

    def on(self):
        self._active = True
        pin_logger.log(self.pin, 'DigitalOutputDevice', 'on')

    def off(self):
        self._active = False
        pin_logger.log(self.pin, 'DigitalOutputDevice', 'off')

    def _write(self, value):
        """Internal method used by FlipperOutput."""
        self._active = bool(value)
        pin_logger.log(self.pin, 'DigitalOutputDevice',
                       'write({})'.format(value))

    def close(self):
        self.off()
