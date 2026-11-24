"""Independent camera/treadmill process; also runs standalone on a camera Pi.

The controller sends STOP (or closes stdin) to request a clean shutdown. Camera
recording waits for frames in the output file; preview waits for a camera frame.
"""

import csv
import io
import json
import os
import signal
import sys
import time
from pathlib import Path
from threading import Event, Thread


def _prepare_preview_environment(config):
    """Select the camera Pi's X desktop before loading Qt; leave the controller untouched."""
    if config.get('backend', 'picamera2') == 'picamera2':
        display = config.get('preview_display', ':0')
        if not isinstance(display, str) or not display:
            raise ValueError('Set preview_display to the camera desktop DISPLAY, e.g. :0')
        os.environ['DISPLAY'] = display
        os.environ['QT_QPA_PLATFORM'] = 'xcb'
        authority = config.get('preview_xauthority')
        if authority:
            os.environ['XAUTHORITY'] = str(Path(authority).expanduser())
        elif 'XAUTHORITY' not in os.environ and (Path.home() / '.Xauthority').is_file():
            os.environ['XAUTHORITY'] = str(Path.home() / '.Xauthority')


def _start_camera_preview(camera, config):
    """Open a native preview on the camera's own desktop/monitor; return None."""
    x, y, width, height = config.get('preview_window', (0, 0, 640, 480))
    if width <= 0 or height <= 0:
        raise ValueError('Preview width and height must be positive pixels')
    if config.get('backend', 'picamera2') == 'picamera2':
        from picamera2 import Preview
        mode = config.get('preview_backend', 'qt')
        if mode not in ('qt', 'qtgl'):
            raise ValueError('preview_backend must be qt or qtgl')
        camera.start_preview(Preview.QT if mode == 'qt' else Preview.QTGL,
                             x=x, y=y, width=width, height=height)
    else:
        camera.start_preview(fullscreen=False, window=(x, y, width, height))


def preview_camera(config, stop, ready):
    """Show a preview until stop Event; wait for a real camera frame before readiness."""
    _prepare_preview_environment(config)
    camera = None
    started = False
    preview_started = False
    first_frame = Event()
    resolution = tuple(config.get('resolution', (640, 480)))
    fps = config.get('framerate', 30)
    backend = config.get('backend', 'picamera2')
    try:
        if backend == 'picamera2':
            from picamera2 import Picamera2
            camera = Picamera2(camera_num=config.get('camera_num', 0))
            camera.configure(camera.create_video_configuration(
                main={'size': resolution}, controls={'FrameRate': fps},
            ))
            camera.pre_callback = lambda request: first_frame.set()
            _start_camera_preview(camera, config)
            preview_started = True
            camera.start()
            started = True
            while not first_frame.wait(0.05) and not stop.is_set():
                pass
            if not first_frame.is_set():
                return {'preview_only': True, 'frame_received': False}
        elif backend == 'picamera':
            from picamera import PiCamera
            camera = PiCamera(resolution=resolution, framerate=fps,
                              camera_num=config.get('camera_num', 0))
            _start_camera_preview(camera, config)
            preview_started = True
            # Capture into memory to confirm frames without creating a movie.
            camera.capture(io.BytesIO(), format='jpeg', use_video_port=True)
        else:
            raise ValueError('Camera backend must be picamera or picamera2')
        ready({'timestamp': time.time(), 'display': config.get('preview_display', ':0')})
        stop.wait()
    finally:
        try:
            if started:
                camera.stop()
        finally:
            try:
                if preview_started:
                    camera.stop_preview()
            finally:
                if camera is not None:
                    camera.close()
    return {'preview_only': True}


def record_camera(config, stop, ready):
    """Record H264 and per-frame CSV until stop Event; return frame-count dict.

    config: output_dir str, backend picamera/picamera2, optional resolution
    (width,height) pixels, framerate Hz, bitrate bits/s, and camera_num integer.
    ready(dict) is called once after the first frame is written. Sensor times
    are microseconds for PiCamera, nanoseconds for Picamera2; wall timestamps
    are epoch seconds, and monotonic_s belongs to the camera Pi's clock.
    """
    directory = Path(config['output_dir'])
    directory.mkdir(parents=True, exist_ok=True)
    video_path = directory / 'video.h264'
    resolution = tuple(config.get('resolution', (640, 480)))
    fps = config.get('framerate', 30)
    bitrate = config.get('bitrate', 2000000)
    backend = config.get('backend', 'picamera')
    config = dict(config, backend=backend)
    count = 0
    previous_sensor_time = None
    started = False
    camera = None
    callback_errors = []
    preview_started = False
    if config.get('preview', False):
        _prepare_preview_environment(config)
    with (directory / 'frames.csv').open('x', newline='') as timestamps:
        writer = csv.writer(timestamps)
        writer.writerow(['frame_index', 'sensor_timestamp', 'sensor_timestamp_unit',
                         'frame_duration_us', 'timestamp', 'monotonic_s'])
        timestamps.flush()
        last_flush = time.monotonic()

        def append_frame(sensor_time, unit, duration=''):
            nonlocal count, previous_sensor_time, last_flush
            if sensor_time is None or sensor_time == previous_sensor_time:
                return
            previous_sensor_time = sensor_time
            count += 1
            now = time.monotonic()
            try:
                writer.writerow([count, sensor_time, unit, duration, time.time(), now])
                if count == 1 or now - last_flush >= 1:
                    timestamps.flush()
                    last_flush = now
            except Exception as error:
                # Camera libraries may swallow callback exceptions; report the
                # failure from this worker's main thread after closing files.
                callback_errors.append(error)
                stop.set()

        try:
            if backend == 'picamera2':
                from picamera2 import Picamera2
                from picamera2.encoders import H264Encoder
                from picamera2.outputs import FileOutput
                camera = Picamera2(camera_num=config.get('camera_num', 0))
                camera.configure(camera.create_video_configuration(
                    main={'size': resolution}, controls={'FrameRate': fps}
                ))
                if config.get('preview', False):
                    _start_camera_preview(camera, config)
                    preview_started = True

                def on_frame(request):
                    data = request.get_metadata()
                    append_frame(data.get('SensorTimestamp'), 'ns', data.get('FrameDuration', ''))

                camera.pre_callback = on_frame
                camera.start_recording(H264Encoder(bitrate=bitrate), FileOutput(str(video_path)))
                started = True
                wait_for_camera = lambda: stop.wait(0.05)
            elif backend == 'picamera':
                from picamera import PiCamera
                camera = PiCamera(resolution=resolution, framerate=fps,
                                  camera_num=config.get('camera_num', 0))
                if config.get('preview', False):
                    _start_camera_preview(camera, config)
                    preview_started = True
                video = video_path.open('xb', buffering=0)

                class VideoOutput:
                    def write(self, buf):
                        size = video.write(buf)
                        frame = camera.frame
                        if frame.complete:
                            append_frame(frame.timestamp, 'us')
                        return size

                    def flush(self):
                        video.flush()

                camera.start_recording(VideoOutput(), format='h264', bitrate=bitrate)
                started = True
                wait_for_camera = lambda: camera.wait_recording(0.05)
            else:
                raise ValueError('Camera backend must be picamera or picamera2')

            announced = False
            while not stop.is_set():
                if not announced and count and video_path.exists() and video_path.stat().st_size:
                    ready({'timestamp': time.time(), 'pid': os.getpid(), 'frame_count': count})
                    announced = True
                if not stop.is_set():
                    wait_for_camera()
        finally:
            # Close the camera before its timestamp/output files, so final
            # encoder callbacks still have valid destinations.
            try:
                if camera is not None and started:
                    camera.stop_recording()
            finally:
                try:
                    try:
                        if preview_started:
                            camera.stop_preview()
                    finally:
                        if camera is not None:
                            camera.close()
                finally:
                    if 'video' in locals():
                        video.close()
                    timestamps.flush()
    if callback_errors:
        raise RuntimeError('Camera timestamp recording failed: {}'.format(callback_errors[0]))
    return {'frame_count': count, 'video_file': str(video_path)}


def record_treadmill(config, stop, ready):
    """Copy the existing treadmill log without opening GPIO or other interfaces."""
    if config.get('backend', 'file') != 'file':
        raise ValueError('Treadmill backend must be file; configure the existing source_file')
    return record_treadmill_file(config, stop, ready)


def record_treadmill_file(config, stop, ready):
    """Preserve source CSV header and newly appended bytes in session/treadmill.csv.

    config supplies an absolute source_file, output_dir, source_header_lines
    (default 1), include_existing_data (default False), and poll_interval_s.
    Source sample values/units/timestamps are unchanged. The separate copy log
    records receipt times in epoch/monotonic seconds and byte offsets; those
    receipt times are not measurement timestamps. The source writer is neither
    started nor stopped. Replaced/truncated source files raise RuntimeError.
    """
    if not config.get('source_file'):
        raise ValueError('Set treadmill_setup[source_file] to the existing treadmill CSV path')
    source_path = Path(config['source_file']).expanduser()
    if not source_path.is_absolute() or not source_path.is_file():
        raise ValueError('Treadmill source_file must be an existing absolute file path: {}'.format(source_path))
    header_lines = config.get('source_header_lines', 1)
    interval = config.get('poll_interval_s', 0.05)
    if not isinstance(header_lines, int) or header_lines < 0 or interval <= 0:
        raise ValueError('Treadmill header count must be nonnegative and poll interval must be positive')
    directory = Path(config['output_dir'])
    directory.mkdir(parents=True, exist_ok=True)
    copied = 0
    with source_path.open('rb') as source, (directory / 'treadmill.csv').open('xb') as output, \
            (directory / 'treadmill_copy_times.csv').open('x', newline='') as copy_times:
        identity = os.fstat(source.fileno())
        for _ in range(header_lines):
            output.write(source.readline())
        if not config.get('include_existing_data', False):
            source.seek(0, os.SEEK_END)
        start_offset = source.tell()
        writer = csv.writer(copy_times)
        writer.writerow(['timestamp', 'monotonic_s', 'source_byte_offset', 'bytes_copied'])
        output.flush()
        copy_times.flush()
        ready({'timestamp': time.time(), 'pid': os.getpid(), 'source_file': str(source_path),
               'source_offset_start': start_offset})
        while True:
            current = source_path.stat()
            if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino) or current.st_size < source.tell():
                raise RuntimeError('Treadmill source file was replaced or truncated: {}'.format(source_path))
            offset = source.tell()
            chunk = source.read(1024 * 1024)
            if chunk:
                output.write(chunk)
                copied += len(chunk)
                writer.writerow([time.time(), time.monotonic(), offset, len(chunk)])
                output.flush()
                copy_times.flush()
                continue
            if stop.is_set():
                break
            stop.wait(interval)
        end_offset = source.tell()
    return {'source_file': str(source_path), 'source_offset_start': start_offset,
            'source_offset_end': end_offset, 'bytes_copied': copied,
            'treadmill_file': str(directory / 'treadmill.csv'),
            'copy_timestamp_meaning': 'receipt time, not per-sample acquisition time'}


def main():
    """Read a config JSON path from argv; emit READY/RESULT JSON lines; return status."""
    config = json.loads(Path(sys.argv[1]).read_text())
    stop = Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda signum, frame: stop.set())

    def control():
        for line in sys.stdin:
            if line.strip() == 'STOP':
                break
        stop.set()  # EOF also stops the remote worker if SSH disconnects.

    Thread(target=control, daemon=True).start()

    def ready(info):
        print('MMN_READY ' + json.dumps(info), flush=True)

    status = 0
    try:
        operation = {'treadmill': record_treadmill, 'camera': record_camera, 'preview': preview_camera}[config['kind']]
        result = operation(config, stop, ready)
        result['status'] = 'complete'
    except Exception as error:
        result = {'status': 'failed', 'error': str(error)}
        status = 1
    result['timestamp'] = time.time()
    Path(config['output_dir'], 'recording_result.json').write_text(json.dumps(result, indent=2))
    print('MMN_RESULT ' + json.dumps(result), flush=True)
    return status


if __name__ == '__main__':
    raise SystemExit(main())
