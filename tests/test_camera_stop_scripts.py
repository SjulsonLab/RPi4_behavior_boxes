import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PICAMERA_STOP_SCRIPT = PROJECT_ROOT / "video_acquisition" / "stop_acquisition.sh"
PICAMERA2_STOP_SCRIPT = (
    PROJECT_ROOT / "video_acquisition" / "stop_acquisition_picamera2.sh"
)


def run_script(script_path, *args):
    return subprocess.run(
        ["bash", str(script_path), *map(str, args)],
        capture_output=True,
        text=True,
        timeout=10,
    )


def start_signal_ignoring_process(process_name):
    command = (
        "trap '' INT; "
        f"exec -a {process_name} "
        f"{sys.executable} -c 'import time; time.sleep(60)'"
    )
    return subprocess.Popen(["bash", "-c", command])


def terminate_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def test_picamera_stop_script_succeeds_when_no_acquisition_process_is_running():
    result = run_script(PICAMERA_STOP_SCRIPT)

    assert result.returncode == 0
    assert "No running acquisition process found" in result.stdout


def test_picamera2_stop_script_succeeds_when_no_acquisition_process_is_running(
    tmp_path,
):
    result = run_script(PICAMERA2_STOP_SCRIPT, tmp_path)

    assert result.returncode == 0
    assert "No running acquisition process found" in result.stdout


def test_picamera_stop_script_hard_kills_process_that_ignores_sigint():
    process = start_signal_ignoring_process(
        "/home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition.py"
    )
    try:
        time.sleep(0.2)

        result = run_script(PICAMERA_STOP_SCRIPT)

        assert result.returncode == 0
        assert "Hard-kill fallback used" in result.stdout
        process.wait(timeout=2)
    finally:
        terminate_process(process)


def test_picamera2_stop_script_hard_kills_process_that_ignores_sigint(tmp_path):
    process = start_signal_ignoring_process(
        "/home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition_v3_camera_fast.py"
    )
    try:
        time.sleep(0.2)

        result = run_script(PICAMERA2_STOP_SCRIPT, tmp_path)

        assert result.returncode == 0
        assert "Hard-kill fallback used" in result.stdout
        process.wait(timeout=2)
    finally:
        terminate_process(process)
