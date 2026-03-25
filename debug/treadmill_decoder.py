import time
from dataclasses import dataclass, replace
from threading import Lock
from time import monotonic
from typing import Callable, Optional

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    GPIO = None

# -----------------------------------------------------------------------------
# Constants / defaults
# -----------------------------------------------------------------------------
# Fill these in for your hardware during integration.
ENC_A_PIN = 17
ENC_B_PIN = 27

# Teensy-compatible calibration pattern:
# MM_PER_COUNT is in "mm * 1e6 per count" so that dividing by dt_us yields mm/s.
MM_PER_COUNT = 410950
DIST_PER_COUNT = MM_PER_COUNT / 1_000_000.0
SPEED_TIMEOUT_S = 0.050
FW = -1
BW = 1


@dataclass
class EncoderState:
    """Shared treadmill state updated by the A-rising handler.

    This mirrors the important decoded quantities from the Teensy version while
    keeping them interpretable as internal state.
    """

    counts: int = 0
    distance_mm: float = 0.0
    run_speed_mms: float = 0.0
    direction: int = 0
    last_edge_time_s: float = 0.0
    edge_count_total: int = 0
    missed_callback_count: int = 0
    last_b_state: int = 0


class TreadmillDecoder:
    """Teensy-style treadmill decoder.

    Version 1 behavior intentionally emulates the legacy Teensy logic:
    - react only to rising edges on channel A
    - sample channel B at that instant
    - if A == B: direction = FW, counts -= 1, speed positive
    - else:     direction = BW, counts += 1, speed negative

    GPIO integration is intentionally abstracted behind helper methods so you can
    swap in lgpio, gpiozero, pigpio, or another backend later.
    """

    def __init__(
        self,
        a_pin: int,
        b_pin: int,
        mm_per_count: float,
        *,
        speed_timeout_s: float = SPEED_TIMEOUT_S,
    ) -> None:
        self.a_pin = a_pin
        self.b_pin = b_pin
        self.mm_per_count = float(mm_per_count)
        self.dist_per_count = self.mm_per_count / 1_000_000.0
        self.speed_timeout_s = float(speed_timeout_s)

        self._lock = Lock()
        self._state = EncoderState(last_edge_time_s=monotonic())
        self._last_edge_time_s: Optional[float] = None
        self._gpio = None
        self._gpio_ready = False
        self._running = False
        self._callback_registered = False

        self._setup_gpio()

    # ------------------------------------------------------------------
    # GPIO/backend integration points
    # ------------------------------------------------------------------
    def _setup_gpio(self) -> None:
        """Configure GPIO and register an A-rising callback.

        This default implementation uses RPi.GPIO, which is available on
        Raspberry Pi OS for Python 3.7 and mirrors the intended hardware wiring:
          1. configure A and B as pull-up inputs
          2. register self._on_a_rising on channel A rising edges
        """
        if GPIO is None:
            raise RuntimeError(
                "RPi.GPIO is not available. Install RPi.GPIO and run this on a Raspberry Pi."
            )

        self._gpio = GPIO
        self._gpio.setwarnings(False)

        mode = self._gpio.getmode()
        if mode is None:
            self._gpio.setmode(self._gpio.BCM)
        elif mode != self._gpio.BCM:
            raise RuntimeError(
                "TreadmillDecoder requires BCM GPIO numbering, "
                "but RPi.GPIO is already using a different mode."
            )

        self._gpio.setup(self.a_pin, self._gpio.IN, pull_up_down=self._gpio.PUD_UP)
        self._gpio.setup(self.b_pin, self._gpio.IN, pull_up_down=self._gpio.PUD_UP)
        self._gpio.add_event_detect(
            self.a_pin,
            self._gpio.RISING,
            callback=self._on_a_rising,
        )

        with self._lock:
            self._state.last_b_state = int(self._gpio.input(self.b_pin))

        self._callback_registered = True
        self._gpio_ready = True

    def start(self) -> None:
        """Arm the decoder.

        In many backends the callback becomes active immediately after GPIO setup;
        this flag gives the rest of the program an explicit lifecycle anyway.
        """
        self._running = True

    def stop(self) -> None:
        """Disarm the decoder while leaving pin configuration in place."""
        self._running = False

    def close(self) -> None:
        """Remove edge detection and release only the pins owned by this decoder."""
        self.stop()
        if self._gpio is not None:
            if self._callback_registered:
                try:
                    self._gpio.remove_event_detect(self.a_pin)
                except RuntimeError:
                    pass
            for pin in (self.a_pin, self.b_pin):
                try:
                    self._gpio.cleanup(pin)
                except RuntimeError:
                    pass
        self._callback_registered = False
        self._gpio_ready = False

    def _read_a(self) -> int:
        """Read channel A from the configured GPIO backend."""
        if not self._gpio_ready or self._gpio is None:
            raise RuntimeError("GPIO backend is not initialized")
        return int(self._gpio.input(self.a_pin))

    def _read_b(self) -> int:
        """Read channel B from the configured GPIO backend."""
        if not self._gpio_ready or self._gpio is None:
            raise RuntimeError("GPIO backend is not initialized")
        return int(self._gpio.input(self.b_pin))

    # ------------------------------------------------------------------
    # Core decoding logic
    # ------------------------------------------------------------------
    def _on_a_rising(
        self,
        gpio: Optional[int] = None,
        level: Optional[int] = None,
        tick: Optional[int] = None,
    ) -> None:
        """Minimal callback for channel A rising edges.

        Signature is permissive so it can be used with a variety of GPIO
        callback APIs. Only the edge itself matters here.
        """
        if not self._running:
            return

        try:
            a = self._read_a()
            b = self._read_b()
            now_s = monotonic()
        except Exception:
            # Keep the callback resilient. Count failures for diagnostics and
            # avoid raising from inside the GPIO callback path.
            with self._lock:
                self._state.missed_callback_count += 1
            return

        with self._lock:
            dt_s: Optional[float]
            if self._last_edge_time_s is None:
                dt_s = None
            else:
                dt_s = now_s - self._last_edge_time_s
                if dt_s <= 0:
                    dt_s = None

            self._last_edge_time_s = now_s
            self._state.last_edge_time_s = now_s
            self._state.last_b_state = int(b)
            self._state.edge_count_total += 1

            if a == b:
                self._state.direction = FW
                self._state.counts -= 1
                self._state.distance_mm -= self.dist_per_count
                if dt_s is not None:
                    self._state.run_speed_mms = self.dist_per_count / dt_s
            else:
                self._state.direction = BW
                self._state.counts += 1
                self._state.distance_mm += self.dist_per_count
                if dt_s is not None:
                    self._state.run_speed_mms = -(self.dist_per_count / dt_s)

    def snapshot(self) -> EncoderState:
        """Return a copy of the current state.

        This is the Python equivalent of the Teensy's brief interrupt-disabled
        copy section.
        """
        with self._lock:
            return replace(self._state)

    def get_speed_mms(self, now_s: Optional[float] = None) -> float:
        """Return instantaneous speed with Teensy-like timeout-to-zero behavior."""
        if now_s is None:
            now_s = monotonic()

        with self._lock:
            if (now_s - self._state.last_edge_time_s) > self.speed_timeout_s:
                return 0.0
            return self._state.run_speed_mms

    def zero(self) -> None:
        """Zero the interpretable internal state.

        This is cleaner than the Teensy's transport-driven count clipping.
        """
        with self._lock:
            self._state.counts = 0
            self._state.distance_mm = 0.0
            self._state.run_speed_mms = 0.0
            self._state.direction = 0
            self._state.edge_count_total = 0
            self._state.missed_callback_count = 0
            self._state.last_b_state = 0
            self._state.last_edge_time_s = monotonic()
            self._last_edge_time_s = None


def behavior_loop(
    decoder: TreadmillDecoder,
    run_behavior_step: Callable[[int, float, float], None],
    *,
    sleep_s: float = 0.001,
) -> None:
    """Simple main-process behavior loop.

    The decoder callback updates shared state; this loop snapshots it and passes
    the current count, distance, and speed into the task code.
    """
    decoder.start()
    try:
        while True:
            enc = decoder.snapshot()
            speed = decoder.get_speed_mms()
            run_behavior_step(enc.counts, enc.distance_mm, speed)
            if sleep_s > 0:
                time.sleep(sleep_s)
    finally:
        decoder.stop()


def run_behavior_step(counts: int, distance_mm: float, speed_mms: float) -> None:
    # Replace with your real behavior update function.
    print(
        f"counts={counts:6d} distance_mm={distance_mm:9.3f} speed_mms={speed_mms:8.3f}"
    )


if __name__ == "__main__":
    decoder = TreadmillDecoder(ENC_A_PIN, ENC_B_PIN, MM_PER_COUNT)
    print("TreadmillDecoder initialized with the RPi.GPIO backend.")
    behavior_loop(decoder, run_behavior_step)
