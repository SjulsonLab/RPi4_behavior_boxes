"""Start isolated recording workers and keep all session outputs together."""

import json
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Event, Thread


WORKER_SCRIPT = Path(__file__).with_name('acquisition_worker.py')


def create_session_directory(root: Path, mouse_name: str) -> Path:
    """Create/return root/<mouse>_YYYYMMDD_HHMMSS_microseconds; never reuse a folder."""
    mouse = re.sub(r'[^A-Za-z0-9_-]', '_', str(mouse_name)).strip('_') or 'mouse'
    directory = Path(root) / (mouse + '_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    directory.mkdir(parents=True, exist_ok=False)
    return directory


class RecordingWorker:
    """Own one local/SSH worker; STOP on stdin closes its files and camera cleanly."""

    def __init__(self, name, config, directory, start_timeout, stop_timeout, python):
        """Use config dict, local output Path, timeouts in seconds and Python executable str."""
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
            raise ValueError('Recording IDs must contain only letters, digits, underscores or hyphens')
        self.name, self.config = name, dict(config)
        self.directory = Path(directory).resolve()
        self.control_dir = self.directory / 'acquisition'
        self.start_timeout, self.stop_timeout, self.python = start_timeout, stop_timeout, python
        self.remote = config.get('transport', 'local') == 'ssh'
        if config.get('transport', 'local') not in ('local', 'ssh'):
            raise ValueError('Camera transport must be local or ssh')
        self.target = '{}@{}'.format(config.get('ssh_user', 'pi'), config.get('host', ''))
        if self.remote and (not config.get('host') or any(ch.isspace() for ch in self.target)):
            raise ValueError('Set the remote camera host and ssh_user in session_info.py')
        self.remote_dir = None
        if self.remote:
            root = Path(config.get('remote_output_dir', '/home/pi/experimental_data/mmn'))
            if not root.is_absolute():
                raise ValueError('Remote camera output directory must be absolute')
            self.remote_dir = root / self.directory.parent.parent.name / 'video' / name
        self.ready = Event()
        self.process = None
        self.reader = None
        self.closed = False
        self.errors = []
        self.info = {
            'name': name, 'kind': config['kind'], 'backend': config.get('backend'),
            'host': self.target if self.remote else 'local',
            'output_dir': str(self.directory),
            'remote_output_dir': str(self.remote_dir) if self.remote else None,
            'status': 'not_started', 'log_file': str(self.control_dir / 'worker.log'),
        }

    def ssh(self, command):
        """Return SSH argv for one safely quoted remote shell command str."""
        return ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', self.target, command]

    def prepare(self):
        """Write this worker's config and stage its standalone code on a remote Pi, if used."""
        self.control_dir.mkdir(parents=True, exist_ok=True)
        output_dir = self.remote_dir if self.remote else self.directory
        self.config['output_dir'] = str(output_dir)
        text = json.dumps(self.config, indent=2)
        (self.control_dir / 'config.json').write_text(text)
        if self.remote:
            remote_control = self.remote_dir / 'acquisition'
            for filename, contents in [('acquisition_worker.py', WORKER_SCRIPT.read_text()), ('config.json', text)]:
                command = 'mkdir -p {} && cat > {}'.format(
                    shlex.quote(str(remote_control)), shlex.quote(str(remote_control / filename)))
                result = subprocess.run(self.ssh(command), input=contents, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, universal_newlines=True,
                                        timeout=self.start_timeout)
                if result.returncode:
                    raise RuntimeError('{}: cannot stage recorder: {}'.format(self.name, result.stderr.strip()))

    def command(self):
        """Return argv that runs only this session's worker, without unrelated process kills."""
        if self.remote:
            control = self.remote_dir / 'acquisition'
            argv = [self.config.get('python', 'python3'), '-u', str(control / 'acquisition_worker.py'),
                    str(control / 'config.json')]
            return self.ssh('exec ' + ' '.join(shlex.quote(arg) for arg in argv))
        return [self.python, '-u', str(WORKER_SCRIPT), str(self.control_dir / 'config.json')]

    def _read_output(self):
        """Drain process output to its log; READY and RESULT lines update serializable metadata."""
        with (self.control_dir / 'worker.log').open('w') as output:
            for line in self.process.stdout:
                output.write(line)
                output.flush()
                if line.startswith('MMN_READY '):
                    self.info['ready'] = json.loads(line[len('MMN_READY '):])
                    self.info['status'] = 'recording'
                    self.ready.set()
                elif line.startswith('MMN_RESULT '):
                    self.info['result'] = json.loads(line[len('MMN_RESULT '):])

    def start(self):
        """Start and wait up to start_timeout seconds for actual hardware/data readiness."""
        self.info['status'] = 'starting'
        try:
            self.prepare()
            self.process = subprocess.Popen(
                self.command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, bufsize=1, start_new_session=True,
            )
        except Exception as error:
            self.errors.append('{} startup failed: {}'.format(self.name, error))
            raise
        self.reader = Thread(target=self._read_output, daemon=True)
        self.reader.start()
        deadline = time.monotonic() + self.start_timeout
        while not self.ready.wait(0.05):
            if self.process.poll() is not None or time.monotonic() >= deadline:
                message = '{} recording did not become ready; inspect {}'.format(self.name, self.info['log_file'])
                self.errors.append(message)
                raise RuntimeError(message)
        self.check_health()

    def check_health(self):
        """Raise RuntimeError if a started recorder has exited unexpectedly."""
        if self.process is not None and not self.closed and self.process.poll() is not None:
            raise RuntimeError('{} recorder exited with status {}; inspect {}'.format(
                self.name, self.process.returncode, self.info['log_file']))

    def collect(self):
        """Copy remote video/CSV files into the session; preserve source files; return errors list."""
        if not self.remote:
            return []
        try:
            result = subprocess.run([
                'rsync', '-a', '--protect-args', '-e', 'ssh -o BatchMode=yes -o ConnectTimeout=5',
                self.target + ':' + str(self.remote_dir) + '/', str(self.directory) + '/',
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            if result.returncode:
                return ['{} transfer failed: {}. Source remains at {}:{}'.format(
                    self.name, result.stderr.strip(), self.target, self.remote_dir)]
        except OSError as error:
            return ['{} transfer failed: {}'.format(self.name, error)]
        return []

    def stop(self):
        """Stop this worker once and wait for flushing; return errors list."""
        if self.closed:
            return self.errors
        self.closed = True
        if self.process is not None:
            if self.process.poll() is None:
                try:
                    self.process.stdin.write('STOP\n')
                    self.process.stdin.flush()
                    self.process.stdin.close()
                except (OSError, ValueError):
                    pass
                try:
                    self.process.wait(timeout=self.stop_timeout)
                except subprocess.TimeoutExpired:
                    self.errors.append('{} recorder did not stop cleanly'.format(self.name))
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait()
            if self.reader is not None:
                self.reader.join(timeout=2)
            if self.process.stdin is not None and not self.process.stdin.closed:
                try:
                    self.process.stdin.close()
                except OSError:
                    pass
            if self.process.stdout is not None:
                self.process.stdout.close()
            if self.process.returncode != 0:
                self.errors.append('{} recorder exited with status {}'.format(self.name, self.process.returncode))
            if self.info.get('result', {}).get('status') != 'complete':
                self.errors.append('{} recorder did not confirm flushed output'.format(self.name))
        if self.config['kind'] == 'treadmill' and self.info.get('result', {}).get('bytes_copied') == 0:
            self.info['warning'] = 'No new treadmill bytes arrived; check the source writer and file path.'
            print(self.info['warning'], flush=True)
        self.info['status'] = 'failed' if self.errors else 'complete' if self.process is not None else 'not_started'
        self.info['errors'] = list(self.errors)
        return self.errors


class SessionAcquisition:
    """Manage the enabled treadmill and camera recorders for one MMN session."""

    def __init__(self, settings, directory):
        """Read settings dict and exact session directory Path; hardware opens only in start()."""
        self.workers = []
        self.closed = False
        self.report = {'workers': []}
        start_timeout = float(settings.get('acquisition_start_timeout_s', 30))
        stop_timeout = float(settings.get('acquisition_stop_timeout_s', 30))
        if start_timeout <= 0 or stop_timeout <= 0:
            raise ValueError('Acquisition timeouts must be positive seconds')
        python = settings.get('acquisition_python', sys.executable)
        if settings.get('treadmill', False):
            config = dict(settings.get('treadmill_setup', {}), kind='treadmill', transport='local')
            config.setdefault('backend', 'file')
            self.workers.append(RecordingWorker('treadmill', config, directory, start_timeout, stop_timeout, python))
        if settings.get('camera_enabled', False):
            nodes = settings.get('camera_nodes', [])
            if not nodes:
                raise ValueError('camera_enabled requires at least one camera_nodes entry')
            ids = [node.get('camera_id', 'cam0') for node in nodes]
            if len(ids) != len(set(ids)):
                raise ValueError('Camera IDs must be unique')
            for node, name in zip(nodes, ids):
                self.workers.append(RecordingWorker(
                    name, dict(node, kind='camera'), Path(directory) / 'video' / name,
                    start_timeout, stop_timeout, python,
                ))
        self.report['workers'] = [worker.info for worker in self.workers]

    def start(self):
        """Start every enabled recorder; stop earlier workers if any start fails."""
        try:
            for worker in self.workers:
                worker.start()
        except BaseException:
            self.stop()
            raise

    def check_health(self):
        """Raise on recorder failure; process polling is local and does not delay frames with SSH."""
        for worker in self.workers:
            worker.check_health()

    def stop(self):
        """Attempt all recorder shutdowns/transfers even if another fails; return error strings."""
        if self.closed:
            return self.report.get('errors', [])
        self.closed = True
        errors = []
        for worker in reversed(self.workers):
            try:
                errors.extend(worker.stop())
            except Exception as error:
                worker.info.update(status='failed', error=str(error))
                errors.append('{}: {}'.format(worker.name, error))
        # Stop all captures before a potentially long video transfer, so other
        # cameras and the treadmill do not keep recording throughout rsync.
        for worker in self.workers:
            if worker.remote and worker.process is not None:
                transfer_errors = worker.collect()
                worker.info['transfer_status'] = 'failed' if transfer_errors else 'complete'
                if transfer_errors:
                    worker.errors.extend(transfer_errors)
                    worker.info.update(status='failed', errors=list(worker.errors))
                    errors.extend(transfer_errors)
        self.report['errors'] = errors
        return errors


class RecordingDisplay:
    """Delegate drawing while checking acquisition between frames and during gray waits."""

    def __init__(self, display, acquisition, clock=time.monotonic):
        self.display, self.acquisition, self.clock = display, acquisition, clock

    def __getattr__(self, name):
        return getattr(self.display, name)

    def wait_until(self, deadline):
        if not self.acquisition.workers:
            return self.display.wait_until(deadline)
        while True:
            self.acquisition.check_health()
            step = min(deadline, self.clock() + 0.1)
            if not self.display.wait_until(step):
                return False
            if step >= deadline:
                return True

    def present_grating(self, angle):
        self.acquisition.check_health()
        return self.display.present_grating(angle)
