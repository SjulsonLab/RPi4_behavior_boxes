#!/usr/bin/env python3

# import the necessary modules
from gpiozero import Button
import io
import time
import datetime as dt
from picamera import PiCamera
from threading import Thread, Event
from queue import Queue, Empty
import sys
import RPi.GPIO as GPIO
import os
import signal
from typing import List, Tuple


# camera parameter setting
WIDTH = 640
HEIGHT = 480
FRAMERATE = 30
VIDEO_STABILIZATION = True
EXPOSURE_MODE = 'night'
BRIGHTNESS = 55
CONTRAST = 50
SHARPNESS = 50
SATURATION = 30
AWB_MODE = 'off'
AWB_GAINS = 1.4

# Flipper TTL pulse debounce time in milliseconds.
BOUNCETIME = 100

# Pin number to receive TTL input, using Raspberry Pi BCM numbering.
pin_flipper = 4


def make_output_filenames(base_path: str, cam_id: str) -> Tuple[str, str, str]:
    """Build video, frame timestamp, and flipper timestamp output filenames.

    Data contract:
    - Inputs:
      - `base_path`: `str`, absolute or relative path prefix for this session output.
      - `cam_id`: `str`, camera identifier appended after `_cam`.
    - Output:
      - Returns `(video_filename, timestamp_filename, flipper_filename)`, a tuple of
        three `str` paths. Video is H264 bytes; timestamp/flipper files are CSV text.
    """
    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    video_filename = base_path + "_cam" + cam_id + "_output_" + timestamp + ".h264"
    timestamp_filename = base_path + "_cam" + cam_id + "_timestamp_" + timestamp + ".csv"
    flipper_filename = base_path + "_cam" + cam_id + "_flipper_" + timestamp + ".csv"
    return video_filename, timestamp_filename, flipper_filename


def set_high_priority() -> None:
    """Request high process priority for acquisition.

    Data contract:
    - Inputs: none.
    - Output: returns `None`. The process nice value may be changed by the OS.
    """
    try:
        os.nice(-20)
    except Exception:
        print("set nice level failed. \nsudo nano /etc/security/limits.conf \npi\t-\tnice\t-20")


def configure_flipper_gpio() -> None:
    """Configure the flipper TTL input pin.

    Data contract:
    - Inputs: none.
    - Output: returns `None`. GPIO pin 4 is configured as a BCM input with pulldown.
    """
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin_flipper, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


def cleanup_acquisition(camera=None, output=None, cleanup_gpio: bool = True) -> None:
    """Stop camera acquisition and close output resources exactly once.

    Data contract:
    - Inputs:
      - `camera`: PiCamera-like object or `None`. If provided, must support
        `stop_recording()` and `stop_preview()`.
      - `output`: TimestampOutput-like object or `None`. If provided, may support
        `close_threads()`, `flush()`, and `close()`.
      - `cleanup_gpio`: `bool`, whether to call `GPIO.cleanup()`.
    - Output:
      - Returns `None`. Video bytes and CSV timestamp metadata are flushed and closed.
    """
    cleanup_target = output if output is not None else camera
    if cleanup_target is not None and getattr(cleanup_target, "_cleanup_done", False):
        return

    if cleanup_target is not None:
        try:
            setattr(cleanup_target, "_cleanup_done", True)
        except Exception:
            pass

    if output is not None and hasattr(output, "close_threads"):
        try:
            output.close_threads()
        except Exception:
            pass

    if camera is not None:
        try:
            camera.stop_recording()
        except Exception:
            pass

        try:
            camera.stop_preview()
        except Exception:
            pass

    if output is not None and hasattr(output, "flush"):
        try:
            output.flush()
        except Exception:
            pass

    if output is not None and hasattr(output, "close"):
        try:
            output.close()
        except Exception:
            pass

    if cleanup_gpio:
        try:
            GPIO.cleanup()
        except Exception:
            pass


def make_signal_handler(camera, output):
    """Create a SIGINT handler that uses the shared acquisition cleanup path.

    Data contract:
    - Inputs:
      - `camera`: PiCamera-like object currently used for recording.
      - `output`: TimestampOutput-like object currently receiving video bytes.
    - Output:
      - Returns a callable signal handler with signature `(signum, frame) -> None`.
        The handler raises `SystemExit(0)` after cleanup.
    """
    def signal_handler(signum, frame):
        print("SIGINT detected")
        cleanup_acquisition(camera=camera, output=output)
        print('Recording Stopped')
        print('Closing Output File')
        raise SystemExit(0)

    return signal_handler


# video output thread to save video file
class VideoOutput(Thread):
    """Threaded binary video writer used by PiCamera.

    Data contract:
    - Inputs:
      - `filename`: `str`, path to an H264 output file.
    - Methods:
      - `write(buf)`: accepts `bytes`, writes asynchronously, returns `int` byte count.
      - `flush()`: blocks until queued bytes are written and flushes the file handle.
      - `close()`: stops the writer thread and closes the file handle.
    """

    def __init__(self, filename):
        super(VideoOutput, self).__init__()
        self._output = io.open(filename, 'wb', buffering=0)
        self._event = Event()
        self._queue = Queue()
        self._closed = False
        self.start()

    def write(self, buf):
        """Queue H264 bytes for writing.

        Data contract:
        - Inputs: `buf`, bytes-like object containing encoded H264 data.
        - Output: `int`, number of bytes accepted.
        """
        self._queue.put(buf)
        return len(buf)

    def run(self):
        """Write queued H264 buffers until close is requested.

        Data contract:
        - Inputs: none.
        - Output: returns `None` after `_event` is set.
        """
        while not self._event.wait(0):
            try:
                buf = self._queue.get(timeout=0.1)
            except Empty:
                pass
            else:
                self._output.write(buf)
                self._queue.task_done()

    def flush(self):
        """Flush all queued H264 bytes.

        Data contract:
        - Inputs: none.
        - Output: returns `None` after queued bytes reach the file handle.
        """
        self._queue.join()
        self._output.flush()

    def close(self):
        """Stop the writer thread and close the H264 file.

        Data contract:
        - Inputs: none.
        - Output: returns `None`. The file descriptor is closed.
        """
        if self._closed:
            return
        self._closed = True
        self._event.set()
        self.join()
        self._output.close()

    @property
    def name(self):
        """Return the H264 output filename.

        Data contract:
        - Inputs: none.
        - Output: `str`, path of the underlying file handle.
        """
        return self._output.name


# timestamp output object to save timestamps according to pi and TTL inputs received and write to file
class TimestampOutput(object):
    """PiCamera output adapter that records frame and flipper timestamps.

    Data contract:
    - Inputs:
      - `camera`: PiCamera object. Frame timestamps use PiCamera GPU time units.
      - `video_filename`: `str`, path for H264 video bytes.
      - `timestamp_filename`: `str`, CSV path with columns GPU time, `time.time()`,
        and realtime clock, in seconds where applicable.
      - `flipper_filename`: `str`, CSV path with input state and timestamps in seconds.
    - Output:
      - Instances implement PiCamera's output object methods `write()` and `flush()`.
    """

    def __init__(self, camera, video_filename, timestamp_filename, flipper_filename):
        self.camera = camera
        self._video = VideoOutput(video_filename)
        self._timestampFile = timestamp_filename
        self._flipper_file = flipper_filename
        self._timestamps: List[Tuple[float, float, float]] = []
        self._flipper_timestamps: List[Tuple[float, float, float]] = []

        self.flip_state = GPIO.input(pin_flipper)
        self.flip_thread = None
        self.event_thread = None
        self.state_change = Event()
        self._stop_flag = False
        self._closed = False

    def append_timestamps(self):
        """Append one frame timestamp sample.

        Data contract:
        - Inputs: none; reads `self.camera.frame`.
        - Output: returns `None`; appends `(gpu_time, time_time, realtime_clock)`.
    """
        self._timestamps.append((
            self.camera.frame.timestamp,
            self.camera.dateTime,  # time.time(),
            self.camera.clockRealTime,  # time.clock_gettime(time.CLOCK_REALTIME)
            ))

    def flipper_timestamps_write(self, pin_flipper):
        """Record a flipper timestamp from a GPIO event callback.

        Data contract:
        - Inputs: `pin_flipper`, `int` BCM pin number.
        - Output: returns `None`; appends `(input_state, timestamp_seconds)`.
    """
        input_state = GPIO.input(pin_flipper)
        GPIO.remove_event_detect(pin_flipper)
        self._flipper_timestamps.append((
            input_state,
            time.time(),
            dt.datetime.now(dt.timezone.utc).timestamp(),
        ))
        print(str(self._flipper_timestamps))
        GPIO.add_event_detect(pin_flipper, GPIO.BOTH, bouncetime=BOUNCETIME)

    def write(self, buf):
        """Record frame timestamp metadata and queue encoded video bytes.

        Data contract:
        - Inputs: `buf`, bytes-like object containing encoded H264 data.
        - Output: `int`, number of bytes accepted by the video writer.
    """
        if self.camera.frame.complete and self.camera.frame.timestamp is not None:
            if len(self._timestamps) > 0:
                if self.camera.frame.timestamp != self._timestamps[-1][0]:  # Ignore duplicate consecutive timestamps.
                    self.append_timestamps()
            else:
                self.append_timestamps()
        return self._video.write(buf)

    def flush(self):
        """Write timestamp CSV files and flush queued video bytes.

        Data contract:
        - Inputs: none.
        - Output: returns `None`. CSV timestamps are stored in seconds where applicable;
          video bytes remain H264 encoded.
    """
        self._video.flush()
        with io.open(self._timestampFile, 'w') as f:
            f.write('GPU Times, time.time(), clock_realtime\n')
            for entry in self._timestamps:
                f.write('%d,%f,%f\n' % entry)
        with io.open(self._flipper_file, 'w') as f:
            f.write('Input State, Timestamp, UTC Time\n')
            for entry in self._flipper_timestamps:
                f.write('%f,%f,%f\n' % entry)

    def close(self):
        """Close the video writer.

        Data contract:
        - Inputs: none.
        - Output: returns `None`; H264 file handle is closed.
    """
        if self._closed:
            return
        self._closed = True
        self._video.close()

    def GPIO_loop(self, bouncetime=BOUNCETIME):
        """Poll the flipper input pin for state changes.

        Data contract:
        - Inputs: `bouncetime`, debounce interval in milliseconds.
        - Output: returns `None` when `_stop_flag` is set.
    """
        while True:
            cur_state = GPIO.input(pin_flipper)
            if cur_state != self.flip_state:
                self.flip_state = cur_state
                self.state_change.set()
                time.sleep(bouncetime / 1000)  # Convert milliseconds to seconds.
            else:
                self.state_change.clear()
                time.sleep(.001)

            if self._stop_flag:
                print("Stopping GPIO loop")
                break

    def flipper_callback(self):
        """Append the current flipper state and wall-clock timestamps.

        Data contract:
        - Inputs: none.
        - Output: returns `None`; appends `(state, local_time_s, utc_time_s)`.
    """
        self._flipper_timestamps.append((self.flip_state,
                                         time.time(),
                                         dt.datetime.now(dt.timezone.utc).timestamp()))

    def event_loop(self):
        """Convert GPIO state-change events into timestamp records.

        Data contract:
        - Inputs: none.
        - Output: returns `None` when `_stop_flag` is set.
    """
        while True:
            if self.state_change.is_set():
                self.flipper_callback()
                self.state_change.clear()
            else:
                time.sleep(0.001)

            if self._stop_flag:
                print("Stopping event loop")
                break

    def close_threads(self):
        """Stop and join flipper polling/event threads.

        Data contract:
        - Inputs: none.
        - Output: returns `None`; background threads are no longer alive.
    """
        if self._stop_flag:
            return
        print("Closing threads")
        self._stop_flag = True
        if self.flip_thread is not None:
            self.flip_thread.join()
            self.flip_thread = None
        if self.event_thread is not None:
            self.event_thread.join()
            self.event_thread = None

    def start_flipper_thread(self):
        """Start flipper polling and event-processing threads.

        Data contract:
        - Inputs: none.
        - Output: returns `None`; creates two background threads if absent.
    """
        if self.flip_thread is None:
            self.flip_thread = Thread(target=self.GPIO_loop)
            self.event_thread = Thread(target=self.event_loop)
            self.event_thread.start()
            self.flip_thread.start()
        else:
            print("Flipper thread already running")


def run_acquisition(base_path: str, cam_id: str) -> int:
    """Run PiCamera acquisition until interrupted.

    Data contract:
    - Inputs:
      - `base_path`: `str`, output path prefix for video and CSV metadata.
      - `cam_id`: `str`, camera identifier appended to output filenames.
    - Output:
      - Returns process exit code `0` for normal completion and `1` for acquisition
        exceptions. Video is H264; timestamp outputs are CSV files.
    """
    video_filename, timestamp_filename, flipper_filename = make_output_filenames(base_path, cam_id)

    set_high_priority()
    configure_flipper_gpio()

    output = None
    with PiCamera(resolution=(WIDTH, HEIGHT), framerate=FRAMERATE) as camera:
        camera.brightness = BRIGHTNESS
        camera.contrast = CONTRAST
        camera.sharpness = SHARPNESS
        camera.video_stabilization = VIDEO_STABILIZATION
        camera.hflip = False
        camera.vflip = False

        # Warm-up time for the camera to set initial settings.
        time.sleep(2)

        camera.exposure_mode = EXPOSURE_MODE
        camera.awb_mode = AWB_MODE
        camera.awb_gains = AWB_GAINS

        # Let exposure and AWB settle before locking exposure.
        time.sleep(2)
        camera.exposure_mode = 'off'

        output = TimestampOutput(camera, video_filename, timestamp_filename, flipper_filename)
        output.start_flipper_thread()
        signal.signal(signal.SIGINT, make_signal_handler(camera, output))

        try:
            camera.start_preview()
            time.sleep(1)

            print('Starting Recording')
            camera.start_recording(output, format='h264')
            print('Started Recording')
            camera.annotate_text_size = 10
            last_frame = 0
            while True:
                camera.wait_recording(0.005)
                try:
                    frame = output._timestamps[-1][0]
                except IndexError:  # if no frames are available yet
                    frame = None
                if frame is not None and frame > last_frame:
                    camera.annotate_text = str(frame) + "; " + dt.datetime.now().strftime("%H:%M:%S.%f")
                    last_frame = frame

        except SystemExit:
            raise
        except Exception as exc:
            print(exc)
            return 1
        finally:
            cleanup_acquisition(camera=camera, output=output)
            print('Recording Stopped')
            print('Closing Output File')

    return 0


def main(argv=None) -> int:
    """Parse command-line arguments and run PiCamera acquisition.

    Data contract:
    - Inputs:
      - `argv`: `list[str]` or `None`. Expected shape is
        `[base_path, optional_camera_id]`.
    - Output:
      - Returns process exit code `int`.
    """
    args = sys.argv[1:] if argv is None else argv
    if len(args) < 1:
        raise SystemExit("Usage: start_acquisition.py <base_path> [camera_id]")

    base_path = args[0]
    cam_id = str(args[1]) if len(args) > 1 else "0"
    return run_acquisition(base_path, cam_id)


if __name__ == "__main__":
    sys.exit(main())
