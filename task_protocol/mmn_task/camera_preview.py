"""Open a preview on the camera Pi's monitor or desktop to adjust it before MMN."""

import argparse
import sys
import tempfile
import time
from pathlib import Path

from session_info import make_session_info
from task_protocol.mmn_task.acquisition import RecordingWorker


def run_preview(settings, camera_nodes=None, continue_to_recording=False):
    """Preview selected cameras until Ctrl+C; return 0 only after a ready preview closes cleanly.

    No video or task session is created. Ctrl+C during startup returns 130;
    startup/health/cleanup failures return 1. continue_to_recording changes the
    prompt for main.py's adjustment step, without changing signal handlers.
    """
    nodes = settings.get('camera_nodes', []) if camera_nodes is None else camera_nodes
    if not nodes:
        print('Camera preview failed: set camera_nodes in session_info.py', flush=True)
        return 1
    workers = []
    ready = False
    status = 0
    try:
        names = [node.get('camera_id', 'cam0') for node in nodes]
        if len(names) != len(set(names)):
            raise ValueError('Camera IDs must be unique')
        root = Path(tempfile.mkdtemp(prefix='mmn-preview-'))
        for node, name in zip(nodes, names):
            config = dict(node, kind='preview', preview=True)
            config['remote_output_dir'] = '/tmp/mmn_camera_preview'
            workers.append(RecordingWorker(
                name, config, root / 'video' / name,
                settings.get('acquisition_start_timeout_s', 30),
                settings.get('acquisition_stop_timeout_s', 30), sys.executable,
            ))
        for worker in workers:
            mode = worker.config.get('preview_backend', 'qt')
            target = 'attached monitor (DRM)' if mode == 'drm' else 'desktop {}'.format(worker.config.get('preview_display', ':0'))
            print('Opening {} preview on {} {}...'.format(worker.name, worker.info['host'], target), flush=True)
            worker.start()
        ready = True
        if continue_to_recording:
            print('CAMERA ADJUSTMENT: no recording yet. Adjust the camera, then press Ctrl+C here to START RECORDING.', flush=True)
        else:
            print('Live preview is running. Adjust the camera, then press Ctrl+C here to close the preview.', flush=True)
        while True:
            for worker in workers:
                worker.check_health()
            time.sleep(0.2)
    except KeyboardInterrupt:
        if ready:
            print('\nClosing adjustment preview...' if continue_to_recording else '\nStopping camera preview...', flush=True)
        else:
            print('\nCamera preview startup cancelled; recording was not started.', flush=True)
            status = 130
    except Exception as error:
        print('Camera preview failed: {}'.format(error), flush=True)
        status = 1
    finally:
        for worker in reversed(workers):
            try:
                errors = worker.stop()
                if errors:
                    status = 1
                    print('\n'.join(errors), flush=True)
            except KeyboardInterrupt:
                status = 130
                print('Preview shutdown interrupted; recording was not started.', flush=True)
            except Exception as error:
                status = 1
                print('Preview shutdown failed: {}'.format(error), flush=True)
        if status:
            for worker in workers:
                log = Path(worker.info['log_file'])
                if log.exists():
                    print('\n'.join(log.read_text().splitlines()[-25:]), flush=True)
    return status


def main():
    """Use camera_nodes even if camera_enabled=False; preview until Ctrl+C without recording."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera', help='Camera ID from session_info.py; default: first camera')
    parser.add_argument('--backend', dest='preview_backend', choices=('qt', 'qtgl', 'drm'),
                        help='drm: attached monitor from text console; qt/qtgl: graphical desktop')
    parser.add_argument('--display', help="Qt desktop DISPLAY on the camera Pi, e.g. :0 or :1")
    parser.add_argument('--xauthority', help="Camera Pi's XAUTHORITY file, if its desktop needs an explicit path")
    args = parser.parse_args()
    settings = make_session_info()
    nodes = settings.get('camera_nodes', [])
    if not nodes:
        parser.error('Set camera_nodes in session_info.py')
    node = next((node for node in nodes if node.get('camera_id', 'cam0') == args.camera), None) if args.camera else nodes[0]
    if node is None:
        parser.error('Unknown camera ID: {}'.format(args.camera))
    config = dict(node)
    if args.preview_backend is not None:
        config['preview_backend'] = args.preview_backend
    if args.display is not None:
        config['preview_display'] = args.display
    if args.xauthority is not None:
        config['preview_xauthority'] = args.xauthority
    return run_preview(settings, [config])


if __name__ == '__main__':
    raise SystemExit(main())
