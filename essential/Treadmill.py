import csv
import io
import time
from pathlib import Path
from threading import Lock
from typing import Callable, Dict, List, Optional

from essential.treadmill_decoder import (
    DISTANCE_MM_PER_COUNT,
    EncoderState,
    TreadmillDecoder,
)


class Treadmill(object):
    """Record treadmill encoder events for the current session.

    Data contract:
    - Inputs:
      - `session_info`: `dict` containing:
        - `treadmill_filename`: `str`, CSV basename without the `.csv` suffix.
        - `treadmill_setup`: `dict` with integer BCM pins `encoder_a_pin` and `encoder_b_pin`.
    - Optional inputs:
      - `decoder_factory`: callable returning a decoder object with `start()` and `close()` methods.
      - `clock`: callable returning `float` wall-clock seconds in `time.time()` units.
    - Outputs:
      - `record_event()`: appends one treadmill event row in memory.
      - `close()`: flushes all recorded rows to `<treadmill_filename>.csv`.
    """

    def __init__(
        self,
        session_info: Dict[str, object],
        decoder_factory: Optional[Callable[..., object]] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.session_info = session_info
        self.treadmill_filename = session_info["treadmill_filename"] + ".csv"
        self.clock = clock
        self._lock = Lock()
        self._closed = False
        self._running = False

        treadmill_setup = session_info["treadmill_setup"]
        self.encoder_a_pin = treadmill_setup["encoder_a_pin"]
        self.encoder_b_pin = treadmill_setup["encoder_b_pin"]
        self.treadmill_log: List[Dict[str, object]] = []

        self.counts = 0
        self.distance_mm = 0.0
        self.distance_cm = 0.0
        self.speed_mms = 0.0
        self.direction = 0

        if decoder_factory is None:
            decoder_factory = TreadmillDecoder

        self.decoder = decoder_factory(
            self.encoder_a_pin,
            self.encoder_b_pin,
            DISTANCE_MM_PER_COUNT,
            event_callback=self._record_decoder_state,
        )

    # Helper methods: decoder callback bridge and buffering.
    def _record_decoder_state(self, state: EncoderState) -> None:
        self.record_event(
            counts=state.counts,
            distance_mm=state.distance_mm,
            speed_mms=state.run_speed_mms,
            direction=state.direction,
        )

    # User-facing lifecycle methods.
    def start(self, background: bool = True) -> None:
        del background
        self._running = True
        self.decoder.start()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True

        self._running = False
        try:
            self.decoder.close()
        finally:
            self.treadmill_flush()

    def record_event(
        self,
        *,
        counts: int,
        distance_mm: float,
        speed_mms: float,
        direction: int,
    ) -> None:
        """Store one treadmill event.

        Data contract:
        - Inputs:
          - `counts`: `int`, cumulative encoder counts.
          - `distance_mm`: `float`, cumulative treadmill distance in millimeters.
          - `speed_mms`: `float`, instantaneous treadmill speed in millimeters/second.
          - `direction`: `int`, `1` for forward and `-1` for backward.
        - Output:
          - Appends one row to the in-memory treadmill event buffer.
        """
        timestamp = self.clock()
        event_row = {
            "timestamp": timestamp,
            "counts": counts,
            "distance_mm": distance_mm,
            "speed_mms": speed_mms,
            "direction": direction,
        }

        with self._lock:
            self.counts = counts
            self.distance_mm = distance_mm
            self.distance_cm = distance_mm / 10.0
            self.speed_mms = speed_mms
            self.direction = direction
            self.treadmill_log.append(event_row)

    def treadmill_flush(self) -> None:
        """Write buffered treadmill rows to CSV.

        Data contract:
        - Output file:
          - path: `<session_info['treadmill_filename']>.csv`
          - columns: `timestamp`, `counts`, `distance_mm`, `speed_mms`, `direction`
          - timestamp units: `float` seconds from `time.time()`
          - distance units: millimeters
          - speed units: millimeters/second
        """
        treadmill_path = Path(self.treadmill_filename)
        treadmill_path.parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            treadmill_rows = list(self.treadmill_log)

        with io.open(treadmill_path, "w", newline="") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=["timestamp", "counts", "distance_mm", "speed_mms", "direction"],
            )
            writer.writeheader()
            writer.writerows(treadmill_rows)
