"""Read-only checks for camera settings and existing treadmill log files."""

import argparse
import os
import re
import shlex
import subprocess
from datetime import datetime
from pathlib import Path

from session_info import make_session_info


def find_treadmill_files(roots, limit=3000):
    """Return recent matching Paths from a bounded scan, without reading or changing data."""
    matches = {}
    visited = 0
    ignored = {'.git', '.cache', '__pycache__', 'gratings', 'venv', '.venv'}
    for root in roots:
        pending = [(Path(root), 0)]
        while pending and visited < limit:
            directory, depth = pending.pop()
            try:
                with os.scandir(str(directory)) as entries:
                    for entry in entries:
                        visited += 1
                        path = Path(entry.path)
                        if entry.is_dir(follow_symlinks=False) and depth < 5 and entry.name not in ignored:
                            pending.append((path, depth + 1))
                        elif entry.is_file(follow_symlinks=False) and path.suffix.lower() in ('.csv', '.txt', '.log'):
                            if re.search(r'treadmill|teensy|wheel', str(path.relative_to(root)), flags=re.IGNORECASE):
                                matches[path] = entry.stat(follow_symlinks=False).st_mtime
                        if visited >= limit:
                            break
            except OSError:
                continue
    return sorted(matches, key=matches.get, reverse=True)[:20]


def active_treadmill_files():
    """Return (PID str, filename str) for readable active treadmill/serial writer handles."""
    found = set()
    for process in Path('/proc').glob('[0-9]*'):
        try:
            command = (process / 'cmdline').read_bytes().decode(errors='replace')
            relevant_process = re.search(r'treadmill|teensy|encoder|serial', command, re.IGNORECASE)
            for fd in (process / 'fd').iterdir():
                filename = os.readlink(str(fd))
                if Path(filename).suffix.lower() not in ('.csv', '.txt', '.log'):
                    continue
                if relevant_process or re.search(r'treadmill|teensy|wheel', filename, re.IGNORECASE):
                    found.add((process.name, filename))
        except (OSError, UnicodeError):
            continue
    return sorted(found)


def main():
    """Print configured camera targets and treadmill candidates; optional SSH import check only."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-camera', action='store_true', help='Check camera SSH and import its backend; do not record')
    parser.add_argument('--search-root', action='append', type=Path, help='Limit treadmill search to this directory (repeatable)')
    args = parser.parse_args()
    settings = make_session_info()
    failed = False
    print('Camera recording enabled: {}'.format(settings.get('camera_enabled', False)))
    for camera in settings.get('camera_nodes', []):
        host = camera.get('host', '')
        target = '{}@{}'.format(camera.get('ssh_user', 'pi'), host)
        backend = camera.get('backend', 'picamera2')
        print('{}: {} {}, backend={}'.format(camera.get('camera_id', 'cam0'), camera.get('transport', 'local'), target, backend))
        if args.check_camera:
            if backend not in ('picamera', 'picamera2'):
                raise ValueError('Camera backend must be picamera or picamera2')
            check = [camera.get('python', 'python3'), '-c', 'import {}; print("camera backend available")'.format(backend)]
            if camera.get('transport', 'local') == 'ssh':
                check = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', target,
                         ' '.join(shlex.quote(arg) for arg in check)]
            try:
                result = subprocess.run(check, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        universal_newlines=True, timeout=15)
                print((result.stdout or result.stderr).strip())
                failed = failed or result.returncode != 0
            except (OSError, subprocess.TimeoutExpired) as error:
                print('Camera check failed: {}'.format(error))
                failed = True
    print('\nConfigured treadmill source: {}'.format(settings.get('treadmill_setup', {}).get('source_file') or '(not set)'))
    print('Active treadmill-related log handles:')
    handles = active_treadmill_files()
    for pid, filename in handles:
        print('  PID {}: {}'.format(pid, filename))
    if not handles:
        print('  None found for the current user.')
    print('Recent treadmill/Teensy file candidates (not automatically selected):')
    roots = args.search_root or [Path.home(), Path('/mnt'), Path('/media'), Path('/tmp')]
    paths = find_treadmill_files(roots)
    for path in paths:
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds')
        except OSError:
            continue
        print('  {}  {}'.format(modified, path))
    if not paths:
        print('  None found; use --search-root to search the recording directory.')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
