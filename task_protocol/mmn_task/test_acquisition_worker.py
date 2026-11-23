"""Check camera timestamps and recorder shutdown using strict camera stand-ins."""

import csv
import sys
from threading import Event
from types import SimpleNamespace


def test_legacy_camera_streams_video_and_frame_timestamps(monkeypatch, tmp_path):
    from task_protocol.mmn_task.acquisition_worker import record_camera

    stop = Event()
    calls = []

    class Camera:
        def __init__(self, resolution, framerate, camera_num=0):
            self.frame = SimpleNamespace(complete=True, timestamp=1000)

        def start_recording(self, output, format, bitrate):
            self.output = output
            output.write(b'first frame')

        def wait_recording(self, seconds):
            self.frame.timestamp += 1000
            self.output.write(b'next frame')
            stop.set()

        def stop_recording(self):
            calls.append('stop')

        def close(self):
            calls.append('close')

    monkeypatch.setitem(sys.modules, 'picamera', SimpleNamespace(PiCamera=Camera))
    ready = []
    result = record_camera({'backend': 'picamera', 'output_dir': str(tmp_path)}, stop, ready.append)
    assert ready
    assert result['frame_count'] >= 1
    assert (tmp_path / 'video.h264').stat().st_size > 0
    with (tmp_path / 'frames.csv').open() as output:
        rows = list(csv.DictReader(output))
    assert all(row['sensor_timestamp_unit'] == 'us' for row in rows)
    assert all(float(row['timestamp']) > 0 for row in rows)
    assert calls == ['stop', 'close']


def test_picamera2_writes_sensor_nanoseconds_and_closes(monkeypatch, tmp_path):
    from task_protocol.mmn_task.acquisition_worker import record_camera

    stop = Event()
    calls = []

    class Camera:
        def __init__(self, camera_num=0):
            pass

        def create_video_configuration(self, main, controls):
            return {'main': main, 'controls': controls}

        def configure(self, config):
            pass

        def start_recording(self, encoder, output):
            output.path.write_bytes(b'h264')
            self.pre_callback(SimpleNamespace(get_metadata=lambda: {
                'SensorTimestamp': 1234567890, 'FrameDuration': 33333,
            }))

        def stop_recording(self):
            calls.append('stop')

        def close(self):
            calls.append('close')

    monkeypatch.setitem(sys.modules, 'picamera2', SimpleNamespace(Picamera2=Camera))
    monkeypatch.setitem(sys.modules, 'picamera2.encoders', SimpleNamespace(H264Encoder=lambda bitrate: object()))
    from pathlib import Path
    monkeypatch.setitem(sys.modules, 'picamera2.outputs', SimpleNamespace(FileOutput=lambda filename: SimpleNamespace(path=Path(filename))))
    result = record_camera(
        {'backend': 'picamera2', 'output_dir': str(tmp_path)}, stop,
        lambda info: stop.set(),
    )
    with (tmp_path / 'frames.csv').open() as output:
        rows = list(csv.DictReader(output))
    assert rows[0]['sensor_timestamp'] == '1234567890'
    assert rows[0]['sensor_timestamp_unit'] == 'ns'
    assert result['frame_count'] == 1
    assert calls == ['stop', 'close']


def test_existing_treadmill_csv_is_copied_without_changing_values(tmp_path):
    from task_protocol.mmn_task.acquisition_worker import record_treadmill

    source = tmp_path / 'original.csv'
    source.write_text('timestamp,speed\n1.0,10.5\n')
    destination = tmp_path / 'session'
    stop = Event()

    def ready(info):
        with source.open('a') as output:
            output.write('2.0,12.75\n3.0,0\n')
        stop.set()

    result = record_treadmill({
        'backend': 'file', 'output_dir': str(destination), 'source_file': str(source),
        'source_header_lines': 1,
    }, stop, ready)
    assert (destination / 'treadmill.csv').read_text() == 'timestamp,speed\n2.0,12.75\n3.0,0\n'
    assert source.read_text() == 'timestamp,speed\n1.0,10.5\n2.0,12.75\n3.0,0\n'
    assert result['bytes_copied'] == len(b'2.0,12.75\n3.0,0\n')
    assert result['source_offset_start'] == len(b'timestamp,speed\n1.0,10.5\n')


def test_treadmill_file_rotation_is_reported_instead_of_recording_stale_data(tmp_path):
    import pytest
    from task_protocol.mmn_task.acquisition_worker import record_treadmill

    source = tmp_path / 'original.csv'
    source.write_text('timestamp,speed\n1,2\n')
    stop = Event()

    def ready(info):
        source.rename(tmp_path / 'old.csv')
        source.write_text('timestamp,speed\n3,4\n')

    with pytest.raises(RuntimeError, match='replaced|truncated'):
        record_treadmill({'backend': 'file', 'output_dir': str(tmp_path / 'session'),
                         'source_file': str(source)}, stop, ready)
