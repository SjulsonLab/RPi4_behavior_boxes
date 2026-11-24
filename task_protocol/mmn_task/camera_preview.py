"""Open a preview on the camera Pi's monitor or desktop to adjust it before MMN."""

import argparse
import sys
import tempfile
import time
from pathlib import Path

from session_info import make_session_info
from task_protocol.mmn_task.acquisition import RecordingWorker


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
    name = node.get('camera_id', 'cam0')
    config = dict(node, kind='preview', preview=True)
    config['remote_output_dir'] = '/tmp/mmn_camera_preview'
    if args.preview_backend is not None:
        config['preview_backend'] = args.preview_backend
    if args.display is not None:
        config['preview_display'] = args.display
    if args.xauthority is not None:
        config['preview_xauthority'] = args.xauthority
    directory = Path(tempfile.mkdtemp(prefix='mmn-preview-')) / 'video' / name
    worker = RecordingWorker(name, config, directory,
                             settings.get('acquisition_start_timeout_s', 30),
                             settings.get('acquisition_stop_timeout_s', 30), sys.executable)
    status = 0
    try:
        mode = config.get('preview_backend', 'qt')
        target = 'attached monitor (DRM)' if mode == 'drm' else 'desktop {}'.format(config.get('preview_display', ':0'))
        print('Opening {} preview on {} {}...'.format(name, worker.info['host'], target), flush=True)
        worker.start()
        print('Live preview is running. Adjust the camera, then press Ctrl+C here before starting MMN.', flush=True)
        while True:
            worker.check_health()
            time.sleep(0.2)
    except KeyboardInterrupt:
        print('\nStopping camera preview...', flush=True)
    except Exception as error:
        print('Camera preview failed: {}'.format(error), flush=True)
        status = 1
    finally:
        errors = worker.stop()
        if errors:
            status = 1
            print('\n'.join(errors), flush=True)
        if status:
            log = Path(worker.info['log_file'])
            if log.exists():
                print('\n'.join(log.read_text().splitlines()[-25:]), flush=True)
    return status


if __name__ == '__main__':
    raise SystemExit(main())
