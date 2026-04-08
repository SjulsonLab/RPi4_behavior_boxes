"""
GPIO rotary encoder decoder for the treadmill input.
"""

from dataclasses import dataclass, replace
from threading import Lock
from time import monotonic
from typing import Callable, Optional

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    GPIO = None


MM_PER_COUNT_SCALED = 410950
DISTANCE_MM_PER_COUNT = MM_PER_COUNT_SCALED / 1_000_000.0
SPEED_TIMEOUT_S = 0.050
FORWARD = 1
BACKWARD = -1


@dataclass
class EncoderState:
    """Shared decoder state.

    Data contract:
    - `counts`: `int`, cumulative encoder counts.
    - `distance_mm`: `float`, cumulative treadmill distance in millimeters.
    - `run_speed_mms`: `float`, instantaneous treadmill speed in millimeters/second.
    - `direction`: `int`, `1` for forward, `-1` for backward, `0` before movement.
    - `last_edge_time_s`: `float`, `time.monotonic()` seconds of the last decoded edge.
    - `edge_count_total`: `int`, total number of decoded A-channel rising edges.
    - `missed_callback_count`: `int`, callback failures counted for diagnostics.
    - `last_b_state`: `int`, most recent sampled B-channel digital state.
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
    """Decode a quadrature rotary encoder using GPIO A rising edges.

    Data contract:
    - Inputs:
      - `a_pin`: `int`, BCM GPIO number for encoder channel A.
      - `b_pin`: `int`, BCM GPIO number for encoder channel B.
      - `mm_per_count`: `float`, treadmill distance in millimeters per encoder count.
      - `speed_timeout_s`: `float`, seconds after the last edge before speed is reported as zero.
      - `event_callback`: optional callable accepting one `EncoderState` snapshot per decoded event.
    - Outputs:
      - `snapshot()`: returns an `EncoderState` copy with the fields documented above.
      - `get_speed_mms()`: returns `float` speed in millimeters/second.
    """

    def __init__(
        self,
        a_pin: int,
        b_pin: int,
        mm_per_count: float,
        *,
        speed_timeout_s: float = SPEED_TIMEOUT_S,
        event_callback: Optional[Callable[[EncoderState], None]] = None,
    ) -> None:
        self.a_pin = a_pin
        self.b_pin = b_pin
        self.mm_per_count = float(mm_per_count)
        self.speed_timeout_s = float(speed_timeout_s)
        self.event_callback = event_callback

        self._lock = Lock()
        self._state = EncoderState(last_edge_time_s=monotonic())
        self._last_edge_time_s: Optional[float] = None
        self._gpio = None
        self._gpio_ready = False
        self._running = False
        self._callback_registered = False

        self._setup_gpio()

    # Helper methods: GPIO integration.
    def _setup_gpio(self) -> None:
        if GPIO is None:
            raise RuntimeError(
                "RPi.GPIO is not available. Run treadmill decoding on the behavior Raspberry Pi."
            )

        self._gpio = GPIO
        self._gpio.setwarnings(False)

        mode = self._gpio.getmode()
        if mode is None:
            self._gpio.setmode(self._gpio.BCM)
        elif mode != self._gpio.BCM:
            raise RuntimeError(
                "TreadmillDecoder requires BCM GPIO numbering, but RPi.GPIO is already using a different mode."
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

    def _read_a(self) -> int:
        if not self._gpio_ready or self._gpio is None:
            raise RuntimeError("GPIO backend is not initialized")
        return int(self._gpio.input(self.a_pin))

    def _read_b(self) -> int:
        if not self._gpio_ready or self._gpio is None:
            raise RuntimeError("GPIO backend is not initialized")
        return int(self._gpio.input(self.b_pin))

    # User-facing lifecycle methods.
    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def close(self) -> None:
        self.stop()
        if self._gpio is not None and self._callback_registered:
            try:
                self._gpio.remove_event_detect(self.a_pin)
            except RuntimeError:
                pass

        if self._gpio is not None:
            for pin in (self.a_pin, self.b_pin):
                try:
                    self._gpio.cleanup(pin)
                except RuntimeError:
                    pass

        self._callback_registered = False
        self._gpio_ready = False

    def snapshot(self) -> EncoderState:
        with self._lock:
            return replace(self._state)

    def get_speed_mms(self, now_s: Optional[float] = None) -> float:
        if now_s is None:
            now_s = monotonic()

        with self._lock:
            if (now_s - self._state.last_edge_time_s) > self.speed_timeout_s:
                return 0.0
            return self._state.run_speed_mms

    def zero(self) -> None:
        with self._lock:
            self._state = EncoderState(last_edge_time_s=monotonic())
            self._last_edge_time_s = None

    # Helper method: callback path.
    def _on_a_rising(
        self,
        gpio: Optional[int] = None,
        level: Optional[int] = None,
        tick: Optional[int] = None,
    ) -> None:
        if not self._running:
            return

        try:
            a_state = self._read_a()
            b_state = self._read_b()
            now_s = monotonic()
        except Exception:
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
            self._state.last_b_state = int(b_state)
            self._state.edge_count_total += 1

            if a_state == b_state:
                self._state.direction = FORWARD
                self._state.counts += 1
                self._state.distance_mm += self.mm_per_count
                if dt_s is not None:
                    self._state.run_speed_mms = self.mm_per_count / dt_s
            else:
                self._state.direction = BACKWARD
                self._state.counts -= 1
                self._state.distance_mm -= self.mm_per_count
                if dt_s is not None:
                    self._state.run_speed_mms = -(self.mm_per_count / dt_s)

            event_state = replace(self._state)

        if self.event_callback is not None:
            self.event_callback(event_state)
