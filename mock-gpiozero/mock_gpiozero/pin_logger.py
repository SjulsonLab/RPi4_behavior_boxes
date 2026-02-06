import logging
import time

_gpio_logger = logging.getLogger('mock_gpiozero')


class PinLogger:
    """Singleton that records all mock GPIO pin state changes with timestamps."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.history = []
        return cls._instance

    def log(self, pin, device_type, action):
        entry = {
            'time': time.time(),
            'pin': pin,
            'device_type': device_type,
            'action': action,
        }
        self.history.append(entry)
        _gpio_logger.info("[GPIO] pin=%s (%s): %s", pin, device_type, action)

    def get_history(self, pin=None):
        if pin is not None:
            return [e for e in self.history if e['pin'] == pin]
        return list(self.history)

    def clear(self):
        self.history.clear()


# module-level singleton
pin_logger = PinLogger()


def get_pin_logger():
    return pin_logger
