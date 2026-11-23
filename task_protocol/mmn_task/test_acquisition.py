"""Exercise real recorder subprocess lifecycle without GPIO or camera hardware."""

import json
import sys
import time
from pathlib import Path

import pytest


@pytest.fixture
def synthetic_worker(tmp_path, monkeypatch):
    """Replace hardware worker with a tiny subprocess using the same control protocol."""
    from task_protocol.mmn_task import acquisition

    path = tmp_path / 'test worker.py'
    path.write_text('''import json, sys
from pathlib import Path
c = json.loads(Path(sys.argv[1]).read_text())
p = Path(c['output_dir']); p.mkdir(parents=True, exist_ok=True)
if c.get('fail'):
    raise RuntimeError('test startup failure')
if c['kind'] == 'treadmill':
    (p / 'treadmill.csv').write_text('timestamp,counts,distance_mm,speed_mms,direction\\n1,0,0,0,0\\n')
else:
    (p / 'video.h264').write_bytes(b'video data')
    (p / 'frames.csv').write_text('frame_index,timestamp\\n1,1\\n')
print('MMN_READY ' + json.dumps({'timestamp': 1, 'pid': 123}), flush=True)
if c.get('crash'):
    raise SystemExit(7)
for line in sys.stdin:
    if line.strip() == 'STOP': break
print('MMN_RESULT ' + json.dumps({'status': 'complete', 'timestamp': 2}), flush=True)
''')
    monkeypatch.setattr(acquisition, 'WORKER_SCRIPT', path)
    return path


def test_local_recorders_start_stop_and_save_both_modalities(synthetic_worker, tmp_path):
    from task_protocol.mmn_task.acquisition import SessionAcquisition

    settings = {
        'treadmill': True, 'treadmill_setup': {'backend': 'file'},
        'camera_enabled': True,
        'camera_nodes': [{'camera_id': 'cam0', 'transport': 'local', 'backend': 'picamera'}],
        'acquisition_python': sys.executable,
        'acquisition_start_timeout_s': 2, 'acquisition_stop_timeout_s': 2,
    }
    recorder = SessionAcquisition(settings, tmp_path / 'session with spaces')
    recorder.start()
    recorder.check_health()
    assert all(worker.process.poll() is None for worker in recorder.workers)
    assert recorder.stop() == []
    assert recorder.stop() == []
    assert all(worker.process.poll() == 0 for worker in recorder.workers)
    assert (tmp_path / 'session with spaces' / 'treadmill.csv').is_file()
    assert (tmp_path / 'session with spaces' / 'video' / 'cam0' / 'video.h264').read_bytes() == b'video data'
    assert all(info['status'] == 'complete' for info in recorder.report['workers'])


def test_failed_start_stops_already_running_recorders(synthetic_worker, tmp_path):
    from task_protocol.mmn_task.acquisition import SessionAcquisition

    recorder = SessionAcquisition({
        'treadmill': True, 'treadmill_setup': {'backend': 'file'},
        'camera_enabled': True,
        'camera_nodes': [{'camera_id': 'cam0', 'transport': 'local', 'backend': 'picamera', 'fail': True}],
        'acquisition_python': sys.executable,
        'acquisition_start_timeout_s': 2, 'acquisition_stop_timeout_s': 2,
    }, tmp_path)
    with pytest.raises(RuntimeError, match='cam0'):
        recorder.start()
    assert all(worker.process.poll() is not None for worker in recorder.workers)


def test_early_worker_exit_is_reported_as_recording_failure(synthetic_worker, tmp_path):
    from task_protocol.mmn_task.acquisition import SessionAcquisition

    recorder = SessionAcquisition({
        'treadmill': True, 'treadmill_setup': {'backend': 'file', 'crash': True},
        'acquisition_python': sys.executable, 'acquisition_start_timeout_s': 2,
        'acquisition_stop_timeout_s': 2,
    }, tmp_path)
    try:
        recorder.start()
    except RuntimeError:
        assert recorder.report['errors']  # The startup handshake detected it.
        return
    deadline = time.monotonic() + 2
    while recorder.workers[0].process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    with pytest.raises(RuntimeError, match='treadmill'):
        recorder.check_health()
    recorder.stop()


def test_remote_camera_commands_are_scoped_and_copy_without_deleting_sources(monkeypatch, tmp_path):
    from task_protocol.mmn_task.acquisition import RecordingWorker

    calls = []
    monkeypatch.setattr('subprocess.run', lambda argv, **kwargs: calls.append((argv, kwargs)) or
                        type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})())
    worker = RecordingWorker('cam0', {
        'kind': 'camera', 'transport': 'ssh', 'host': 'camera-host', 'ssh_user': 'pi',
        'remote_output_dir': '/home/pi/video', 'backend': 'picamera2',
    }, tmp_path / 'session' / 'video' / 'cam0', 2, 2, sys.executable)
    worker.prepare()
    command = worker.command()
    assert command[0] == 'ssh'
    assert 'pi@camera-host' in command
    assert 'acquisition_worker.py' in command[-1]
    assert 'pkill' not in ' '.join(command)
    assert worker.collect() == []
    assert calls[-1][0][0] == 'rsync'
    assert '--remove-source-files' not in calls[-1][0]
    assert '--delete' not in calls[-1][0]


def test_session_directory_has_mouse_date_time_and_never_reuses_a_folder(tmp_path):
    from task_protocol.mmn_task.acquisition import create_session_directory

    first = create_session_directory(tmp_path, 'mouse/one')
    second = create_session_directory(tmp_path, 'mouse/one')
    assert first.parent == tmp_path
    assert first.name.startswith('mouse_one_')
    assert first != second
    assert first.is_dir() and second.is_dir()


def test_real_file_worker_captures_treadmill_csv_without_gpio(tmp_path):
    from task_protocol.mmn_task.acquisition import SessionAcquisition

    source = tmp_path / 'source.csv'
    source.write_text('timestamp,speed\n1,2\n')
    session = tmp_path / 'session'
    recorder = SessionAcquisition({
        'treadmill': True, 'treadmill_setup': {
            'backend': 'file', 'source_file': str(source), 'source_header_lines': 1,
        },
        'acquisition_python': sys.executable, 'acquisition_start_timeout_s': 2,
        'acquisition_stop_timeout_s': 2,
    }, session)
    recorder.start()
    try:
        with source.open('a') as output:
            output.write('2,4\n')
    finally:
        assert recorder.stop() == []
    assert (session / 'treadmill.csv').read_text() == 'timestamp,speed\n2,4\n'
    assert recorder.report['workers'][0]['result']['bytes_copied'] == 4


def test_health_is_checked_during_long_spontaneous_wait():
    from types import SimpleNamespace
    from task_protocol.mmn_task.acquisition import RecordingDisplay

    clock = SimpleNamespace(now=0.0)

    class Display:
        def wait_until(self, deadline):
            clock.now = deadline
            return True

    class Recorder:
        workers = [object()]

        def check_health(self):
            if clock.now >= 0.2:
                raise RuntimeError('camera stopped')

    display = RecordingDisplay(Display(), Recorder(), clock=lambda: clock.now)
    with pytest.raises(RuntimeError, match='camera stopped'):
        display.wait_until(900)
    assert clock.now <= 0.3


def test_recorders_stop_before_any_remote_video_transfer(monkeypatch, tmp_path):
    from task_protocol.mmn_task.acquisition import SessionAcquisition

    recorder = SessionAcquisition({
        'treadmill': True,
        'camera_enabled': True,
        'camera_nodes': [{'camera_id': 'cam0', 'transport': 'ssh', 'host': 'camera'}],
    }, tmp_path)
    calls = []
    for worker in recorder.workers:
        worker.process = object()
        monkeypatch.setattr(worker, 'stop', lambda name=worker.name: calls.append(('stop', name)) or [])
        monkeypatch.setattr(worker, 'collect', lambda name=worker.name: calls.append(('copy', name)) or [])
    assert recorder.stop() == []
    assert calls == [('stop', 'cam0'), ('stop', 'treadmill'), ('copy', 'cam0')]
    recorder.stop()
    assert len(calls) == 3


def test_failed_source_configuration_is_saved_and_prevents_start(tmp_path):
    from task_protocol.mmn_task.acquisition import SessionAcquisition

    recorder = SessionAcquisition({
        'treadmill': True, 'treadmill_setup': {'backend': 'file', 'source_file': ''},
        'acquisition_start_timeout_s': 2, 'acquisition_stop_timeout_s': 2,
    }, tmp_path)
    with pytest.raises(RuntimeError, match='did not become ready'):
        recorder.start()
    assert recorder.workers[0].process.poll() == 1
    result = recorder.report['workers'][0]['result']
    assert result['status'] == 'failed'
    assert 'source_file' in result['error']
