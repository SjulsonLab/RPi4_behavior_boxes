"""
Tkinter-based keyboard simulator for mock GPIO.

Opens a small window that captures key presses and translates them into
mock GPIO Button events. The tkinter window runs in a separate Python
process (via subprocess.Popen) so it works on macOS (which requires
tkinter on the main thread) and is fully compatible with pygame.

Usage:
    from mock_gpiozero import KeyboardSimulator
    sim = KeyboardSimulator()
    sim.start()   # opens the tkinter window
    # ... experiment runs ...
    sim.stop()
"""

import os
import sys
import json
import subprocess
import threading
import logging

from mock_gpiozero.devices import _button_registry

logger = logging.getLogger('mock_gpiozero')

# Default key mapping for the behavior box.
#
# The lick and IR sensors are wired with inverted logic (Button(..., inverted=True)),
# which means the gpiozero callback naming is swapped relative to the physical action:
#
#   Lick sensors:  when_released -> *_entry (animal starts licking)
#                  when_pressed  -> *_exit  (animal stops licking)
#
#   IR sensors:    when_pressed  -> IR_*_entry (animal pokes)
#                  when_released -> IR_*_exit  (animal withdraws)
#
# This mapping ensures key-down = "animal does the action" and
# key-up = "animal stops", matching intuitive keyboard behavior.
#
# Format: key_name -> {pin, on_keydown, on_keyup, label}
#   on_keydown/on_keyup: 'press' calls simulate_press(), 'release' calls simulate_release()

DEFAULT_KEY_MAP = {
    # Lick sensors (inverted: keydown->simulate_release to fire when_released->*_entry)
    '1': {'pin': 26, 'on_keydown': 'release', 'on_keyup': 'press',
           'label': 'Left lick (pin 26)'},
    '2': {'pin': 27, 'on_keydown': 'release', 'on_keyup': 'press',
           'label': 'Right lick (pin 27)'},
    '3': {'pin': 15, 'on_keydown': 'release', 'on_keyup': 'press',
           'label': 'Center lick (pin 15)'},

    # IR nosepoke sensors (normal: keydown->simulate_press to fire when_pressed->IR_*_entry)
    '4': {'pin': 5,  'on_keydown': 'press', 'on_keyup': 'release',
           'label': 'IR nosepoke 1 (pin 5)'},
    '5': {'pin': 6,  'on_keydown': 'press', 'on_keyup': 'release',
           'label': 'IR nosepoke 2 (pin 6)'},
    '6': {'pin': 12, 'on_keydown': 'press', 'on_keyup': 'release',
           'label': 'IR nosepoke 3 (pin 12)'},
}


class KeyboardSimulator:
    """Opens a tkinter window to capture keyboard input as mock GPIO events.

    Launches a separate Python process running a tkinter window. Key events
    are sent back to this process via a stdout pipe. A reader thread
    dispatches them to the appropriate mock Button's simulate_press/release.
    """

    def __init__(self, key_map=None):
        self.key_map = key_map or DEFAULT_KEY_MAP
        self._proc = None
        self._reader_thread = None
        self._running = False

    def start(self):
        """Open the keyboard simulator window."""
        if self._running:
            return
        self._running = True

        tk_script = os.path.join(os.path.dirname(__file__), '_tk_window.py')
        key_map_json = json.dumps(self.key_map)

        self._proc = subprocess.Popen(
            [sys.executable, tk_script, key_map_json],
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,  # line-buffered
        )

        self._reader_thread = threading.Thread(
            target=self._read_events, daemon=True)
        self._reader_thread.start()
        logger.info("KeyboardSimulator started (pid=%s)", self._proc.pid)

    def _read_events(self):
        """Read key events from the subprocess stdout and dispatch them."""
        for line in self._proc.stdout:
            if not self._running:
                break
            line = line.strip()
            if not line:
                continue
            try:
                pin_str, action = line.split(',', 1)
                pin = int(pin_str)
            except ValueError:
                continue
            btn = _button_registry.get(pin)
            if btn is None:
                logger.warning(
                    "KeyboardSimulator: no Button on pin %s (not yet created?)",
                    pin)
                continue
            if action == 'press':
                btn.simulate_press()
            elif action == 'release':
                btn.simulate_release()
        self._running = False

    def stop(self):
        """Close the keyboard simulator window."""
        self._running = False
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
        self._reader_thread = None
        logger.info("KeyboardSimulator stopped")
