"""
mock_gpiozero - Mock gpiozero library for testing RPi behavior box code
on non-RPi machines (macOS, Linux desktops, etc.).

Quick start:
    import mock_gpiozero
    mock_gpiozero.patch()       # now 'from gpiozero import LED' uses mocks

    from gpiozero import LED, Button, PWMLED  # these are mock objects

Classes provided:
    LED, PWMLED, Button, DigitalOutputDevice

Simulation tools:
    EventSimulator    - programmatic event injection
    KeyboardSimulator - tkinter window for keyboard-driven simulation
    get_pin_logger()  - access the pin state change log
"""

import sys

from mock_gpiozero.devices import LED, PWMLED, Button, DigitalOutputDevice
from mock_gpiozero.event_simulator import EventSimulator
from mock_gpiozero.keyboard_simulator import KeyboardSimulator
from mock_gpiozero.pin_logger import get_pin_logger


def patch():
    """Patch sys.modules so 'from gpiozero import X' resolves to mock classes.

    Call this at the top of your entry-point script, before any other imports
    that use gpiozero:

        try:
            import mock_gpiozero
            mock_gpiozero.patch()
        except ImportError:
            pass  # on RPi, use real gpiozero
    """
    sys.modules['gpiozero'] = sys.modules[__name__]


__all__ = [
    'LED', 'PWMLED', 'Button', 'DigitalOutputDevice',
    'EventSimulator', 'KeyboardSimulator',
    'get_pin_logger', 'patch',
]
