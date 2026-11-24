"""Verify camera-Pi desktop targeting, preview cleanup and adjustment-only CLI."""

import os
import sys
from threading import Event
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('cancel_before_frame', [False, True])
@pytest.mark.parametrize('preview_backend', ['qt', 'drm'])
def test_preview_waits_for_frame_then_stops_camera_without_recording(monkeypatch, tmp_path, cancel_before_frame, preview_backend):
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
            assert os.environ['DISPLAY'] == (':99' if preview_backend == 'drm' else ':1')
            assert os.environ['XAUTHORITY'] == ('/tmp/original-desktop-auth' if preview_backend == 'drm' else '/tmp/camera-desktop-auth')
            assert os.environ['QT_QPA_PLATFORM'] == ('offscreen' if preview_backend == 'drm' else 'xcb')
            assert mode == preview_backend
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
        Picamera2=Camera, Preview=SimpleNamespace(QT='qt', QTGL='qtgl', DRM='drm'),
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
              'preview_xauthority': '/tmp/camera-desktop-auth', 'output_dir': str(tmp_path),
              'preview_backend': preview_backend}
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


@pytest.mark.parametrize('preview_backend', ['qt', 'drm'])
def test_preview_cli_starts_even_if_recording_disabled_and_stops_on_ctrl_c(monkeypatch, tmp_path, preview_backend):
    from session_info import make_session_info
    from task_protocol.mmn_task import camera_preview

    settings = make_session_info()
    settings['camera_enabled'] = False
    captured = {}
    calls = []

    class Worker:
        def __init__(self, name, config, directory, *args):
            captured.update(config=config, directory=directory)
            self.name, self.config = name, config
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
    monkeypatch.setattr(sys, 'argv', ['preview', '--display', ':1', '--backend', preview_backend])
    assert camera_preview.main() == 0
    assert calls == ['start', 'stop']
    assert captured['config']['kind'] == 'preview'
    assert captured['config']['preview_display'] == ':1'
    assert captured['config']['preview'] is True
    assert captured['config']['preview_backend'] == preview_backend
    assert captured['config']['host'] == '10.49.98.252'
    assert captured['config']['remote_output_dir'] == '/tmp/mmn_camera_preview'
    assert 'preview_display' not in settings['camera_nodes'][0]


@pytest.mark.parametrize('preview_backend', ['qt', 'drm'])
def test_preview_worker_stops_cleanly_in_real_subprocess(monkeypatch, tmp_path, preview_backend):
    from task_protocol.mmn_task.acquisition import RecordingWorker

    # No camera/Qt hardware is used; the real worker process still performs
    # the native-preview lifecycle and READY/STOP/RESULT handshake.
    (tmp_path / 'picamera2.py').write_text('''import os
from pathlib import Path
from types import SimpleNamespace
Preview = SimpleNamespace(QT='qt', QTGL='qtgl', DRM='drm')
def log(event):
    with Path(os.environ['MMN_PREVIEW_TEST_TRACE']).open('a') as output:
        output.write(event + '\\n')
class Picamera2:
    def __init__(self, camera_num=0): log('open')
    def create_video_configuration(self, **kwargs): return kwargs
    def configure(self, config): pass
    def start_preview(self, mode, **kwargs):
        assert mode == os.environ['MMN_PREVIEW_TEST_BACKEND']
        assert os.environ['DISPLAY'] == (':99' if mode == 'drm' else ':1')
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
    monkeypatch.setenv('MMN_PREVIEW_TEST_BACKEND', preview_backend)
    monkeypatch.setenv('DISPLAY', ':99')
    monkeypatch.setenv('PYTHONPATH', str(tmp_path))
    directory = tmp_path / 'session' / 'video' / 'cam0'
    worker = RecordingWorker('cam0', {
        'kind': 'preview', 'backend': 'picamera2', 'transport': 'local', 'preview_display': ':1',
        'preview_backend': preview_backend,
    }, directory, 2, 2, sys.executable)
    try:
        worker.start()
        assert worker.info['ready']['display'] == (None if preview_backend == 'drm' else ':1')
        assert worker.info['ready']['preview_backend'] == preview_backend
    finally:
        errors = worker.stop()
    assert errors == []
    assert worker.process.poll() == 0
    assert worker.info['result']['preview_only'] is True
    assert trace.read_text().splitlines() == ['open', 'preview', 'start', 'stop', 'stop_preview', 'close']
    assert not list(directory.glob('*.h264'))


@pytest.mark.parametrize('failure', [None, 'startup_interrupt', 'startup_error', 'cleanup_error'])
def test_adjustment_starts_recording_only_after_ready_preview_and_clean_shutdown(monkeypatch, tmp_path, failure):
    from task_protocol.mmn_task import camera_preview

    calls = []

    class Worker:
        def __init__(self, name, config, directory, *args):
            self.name, self.config = name, config
            self.info = {'host': 'camera', 'log_file': str(tmp_path / 'worker.log')}

        def start(self):
            calls.append('preview_start')
            if failure == 'startup_interrupt':
                raise KeyboardInterrupt
            if failure == 'startup_error':
                raise RuntimeError('camera unavailable')

        def check_health(self):
            calls.append('adjustment')
            raise KeyboardInterrupt

        def stop(self):
            calls.append('preview_stop')
            return ['camera did not close'] if failure == 'cleanup_error' else []

    monkeypatch.setattr(camera_preview, 'RecordingWorker', Worker)
    monkeypatch.setattr(camera_preview.tempfile, 'mkdtemp', lambda **kwargs: str(tmp_path))
    status = camera_preview.run_preview({'camera_nodes': [{'camera_id': 'cam0'}]}, continue_to_recording=True)
    assert status == {None: 0, 'startup_interrupt': 130, 'startup_error': 1, 'cleanup_error': 1}[failure]
    assert calls[-1] == 'preview_stop'
    assert ('adjustment' in calls) is (failure not in ('startup_interrupt', 'startup_error'))
