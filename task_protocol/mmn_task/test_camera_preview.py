"""Verify camera-Pi desktop targeting, preview cleanup and adjustment-only CLI."""

import os
import sys
from threading import Event
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('cancel_before_frame', [False, True])
def test_preview_waits_for_frame_then_stops_camera_without_recording(monkeypatch, tmp_path, cancel_before_frame):
    from task_protocol.mmn_task.acquisition_worker import preview_camera

    stop = Event()
    calls = []

    class Camera:
        def __init__(self, camera_num):
            calls.append('open')

        def create_video_configuration(self, main, controls):
            return {'main': main, 'controls': controls}

        def configure(self, config):
            calls.append('configure')

        def start_preview(self, mode, **geometry):
            assert os.environ['DISPLAY'] == ':1'
            assert os.environ['XAUTHORITY'] == '/tmp/camera-desktop-auth'
            assert mode == 'qt'
            calls.append('preview')

        def start(self):
            calls.append('start')
            if cancel_before_frame:
                stop.set()
            else:
                self.pre_callback(object())

        def stop(self):
            calls.append('stop')

        def stop_preview(self):
            calls.append('stop_preview')

        def close(self):
            calls.append('close')

    monkeypatch.setitem(sys.modules, 'picamera2', SimpleNamespace(
        Picamera2=Camera, Preview=SimpleNamespace(QT='qt', QTGL='qtgl'),
    ))
    # Changes made by the worker must not escape this test process.
    monkeypatch.setenv('DISPLAY', ':99')
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    monkeypatch.setenv('XAUTHORITY', '/tmp/original-desktop-auth')

    def ready(info):
        assert calls[-1] == 'start'
        calls.append('ready')
        stop.set()

    config = {'backend': 'picamera2', 'preview_display': ':1',
              'preview_xauthority': '/tmp/camera-desktop-auth', 'output_dir': str(tmp_path)}
    if cancel_before_frame:
        assert preview_camera(config, stop, ready) == {'preview_only': True, 'frame_received': False}
    else:
        assert preview_camera(config, stop, ready) == {'preview_only': True}
    assert calls[-3:] == ['stop', 'stop_preview', 'close']
    assert ('ready' in calls) is not cancel_before_frame
    assert list(tmp_path.iterdir()) == []


def test_preview_failure_still_releases_camera(monkeypatch):
    from task_protocol.mmn_task.acquisition_worker import preview_camera

    closed = []

    class Camera:
        def __init__(self, **kwargs):
            pass

        def create_video_configuration(self, **kwargs):
            return kwargs

        def configure(self, config):
            pass

        def start_preview(self, *args, **kwargs):
            raise RuntimeError('desktop unavailable')

        def close(self):
            closed.append(True)

    monkeypatch.setitem(sys.modules, 'picamera2', SimpleNamespace(
        Picamera2=Camera, Preview=SimpleNamespace(QT='qt', QTGL='qtgl'),
    ))
    monkeypatch.setenv('DISPLAY', ':99')
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    with pytest.raises(RuntimeError, match='desktop unavailable'):
        preview_camera({'backend': 'picamera2'}, Event(), lambda info: None)
    assert closed == [True]


def test_preview_cli_starts_even_if_recording_disabled_and_stops_on_ctrl_c(monkeypatch, tmp_path):
    from session_info import make_session_info
    from task_protocol.mmn_task import camera_preview

    settings = make_session_info()
    assert settings['camera_enabled'] is False
    captured = {}
    calls = []

    class Worker:
        def __init__(self, name, config, directory, *args):
            captured.update(config=config, directory=directory)
            self.info = {'host': 'pi@10.49.98.252', 'log_file': str(tmp_path / 'worker.log')}

        def start(self):
            calls.append('start')

        def check_health(self):
            raise KeyboardInterrupt

        def stop(self):
            calls.append('stop')
            return []

    monkeypatch.setattr(camera_preview, 'make_session_info', lambda: settings)
    monkeypatch.setattr(camera_preview, 'RecordingWorker', Worker)
    monkeypatch.setattr(camera_preview.tempfile, 'mkdtemp', lambda **kwargs: str(tmp_path))
    monkeypatch.setattr(sys, 'argv', ['preview', '--display', ':1'])
    assert camera_preview.main() == 0
    assert calls == ['start', 'stop']
    assert captured['config']['kind'] == 'preview'
    assert captured['config']['preview_display'] == ':1'
    assert captured['config']['preview'] is True
    assert captured['config']['host'] == '10.49.98.252'
    assert captured['config']['remote_output_dir'] == '/tmp/mmn_camera_preview'
    assert 'preview_display' not in settings['camera_nodes'][0]


def test_preview_worker_stops_cleanly_in_real_subprocess(monkeypatch, tmp_path):
    from task_protocol.mmn_task.acquisition import RecordingWorker

    # No camera/Qt hardware is used; the real worker process still performs
    # the native-preview lifecycle and READY/STOP/RESULT handshake.
    (tmp_path / 'picamera2.py').write_text('''import os
from pathlib import Path
from types import SimpleNamespace
Preview = SimpleNamespace(QT='qt', QTGL='qtgl')
def log(event):
    with Path(os.environ['MMN_PREVIEW_TEST_TRACE']).open('a') as output:
        output.write(event + '\\n')
class Picamera2:
    def __init__(self, camera_num=0): log('open')
    def create_video_configuration(self, **kwargs): return kwargs
    def configure(self, config): pass
    def start_preview(self, mode, **kwargs):
        assert mode == 'qt'
        assert os.environ['DISPLAY'] == ':1'
        log('preview')
    def start(self):
        log('start')
        self.pre_callback(object())
    def stop(self): log('stop')
    def stop_preview(self): log('stop_preview')
    def close(self): log('close')
''')
    trace = tmp_path / 'camera_trace.txt'
    monkeypatch.setenv('MMN_PREVIEW_TEST_TRACE', str(trace))
    monkeypatch.setenv('PYTHONPATH', str(tmp_path))
    directory = tmp_path / 'session' / 'video' / 'cam0'
    worker = RecordingWorker('cam0', {
        'kind': 'preview', 'backend': 'picamera2', 'transport': 'local', 'preview_display': ':1',
    }, directory, 2, 2, sys.executable)
    try:
        worker.start()
        assert worker.info['ready']['display'] == ':1'
    finally:
        errors = worker.stop()
    assert errors == []
    assert worker.process.poll() == 0
    assert worker.info['result']['preview_only'] is True
    assert trace.read_text().splitlines() == ['open', 'preview', 'start', 'stop', 'stop_preview', 'close']
    assert not list(directory.glob('*.h264'))
