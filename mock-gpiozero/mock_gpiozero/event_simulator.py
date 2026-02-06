import time
import threading
from mock_gpiozero.devices import _button_registry


class EventSimulator:
    """Programmatic API for injecting fake GPIO input events.

    Usage:
        sim = EventSimulator()
        sim.press(26)       # triggers when_pressed on pin 26
        sim.release(26)     # triggers when_released on pin 26

        # Timed sequence
        sim.schedule([
            (1.0, "press", 26),
            (1.1, "release", 26),
            (3.0, "press", 5),
            (3.1, "release", 5),
        ])
    """

    def press(self, pin):
        """Simulate a button press on the given pin."""
        btn = _button_registry.get(pin)
        if btn is None:
            raise ValueError(
                "No mock Button registered on pin {}. "
                "Available pins: {}".format(pin, list(_button_registry.keys())))
        btn.simulate_press()

    def release(self, pin):
        """Simulate a button release on the given pin."""
        btn = _button_registry.get(pin)
        if btn is None:
            raise ValueError(
                "No mock Button registered on pin {}. "
                "Available pins: {}".format(pin, list(_button_registry.keys())))
        btn.simulate_release()

    def schedule(self, events, start_delay=0):
        """Run a timed sequence of press/release events in a background thread.

        Args:
            events: list of (time_offset_sec, action, pin) tuples.
                    action is "press" or "release".
                    time_offset_sec is relative to when schedule() is called.
            start_delay: seconds to wait before starting the sequence.

        Returns:
            The background Thread (can be joined if needed).
        """
        def run_schedule():
            time.sleep(start_delay)
            start = time.time()
            for offset, action, pin in events:
                elapsed = time.time() - start
                if offset > elapsed:
                    time.sleep(offset - elapsed)
                if action == 'press':
                    self.press(pin)
                elif action == 'release':
                    self.release(pin)

        thread = threading.Thread(target=run_schedule, daemon=True)
        thread.start()
        return thread
