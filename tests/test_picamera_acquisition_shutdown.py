import importlib
import sys
import types
from pathlib import Path


MODULE_NAME = "video_acquisition.start_acquisition"
MODULE_PATH = Path(__file__).resolve().parents[1] / "video_acquisition" / "start_acquisition.py"


class FakeCamera:
    """Camera test double that records stop calls and rejects double cleanup."""

    def __init__(self):
        self.recording_stopped = 0
        self.preview_stopped = 0

    def stop_recording(self):
        self.recording_stopped += 1

    def stop_preview(self):
        self.preview_stopped += 1


class FakeOutput:
    """Output test double that records flush and close calls."""

    def __init__(self):
        self.flushed = 0
        self.closed = 0
        self.threads_closed = 0

    def flush(self):
        self.flushed += 1

    def close(self):
        self.closed += 1

    def close_threads(self):
        self.threads_closed += 1


def load_acquisition_module(monkeypatch):
    picamera_stub = types.SimpleNamespace(PiCamera=object)
    gpio_stub = types.SimpleNamespace(
        BCM="BCM",
        IN="IN",
        PUD_DOWN="PUD_DOWN",
        setmode=lambda *args, **kwargs: None,
        setup=lambda *args, **kwargs: None,
        input=lambda *args, **kwargs: 0,
        cleanup=lambda *args, **kwargs: None,
    )
    gpiozero_stub = types.SimpleNamespace(Button=object)

    monkeypatch.setitem(sys.modules, "picamera", picamera_stub)
    monkeypatch.setitem(sys.modules, "RPi", types.SimpleNamespace(GPIO=gpio_stub))
    monkeypatch.setitem(sys.modules, "RPi.GPIO", gpio_stub)
    monkeypatch.setitem(sys.modules, "gpiozero", gpiozero_stub)
    sys.modules.pop(MODULE_NAME, None)
    return importlib.import_module(MODULE_NAME)


def test_picamera_acquisition_defines_import_safe_cleanup_api():
    source = MODULE_PATH.read_text()

    assert "def cleanup_acquisition" in source
    assert "if __name__ == '__main__'" in source or 'if __name__ == "__main__"' in source


def test_picamera_cleanup_is_idempotent_and_flushes_before_close(monkeypatch):
    module = load_acquisition_module(monkeypatch)
    camera = FakeCamera()
    output = FakeOutput()

    module.cleanup_acquisition(camera=camera, output=output)
    module.cleanup_acquisition(camera=camera, output=output)

    assert output.threads_closed == 1
    assert camera.recording_stopped == 1
    assert camera.preview_stopped == 1
    assert output.flushed == 1
    assert output.closed == 1


def test_make_output_filenames_uses_full_camera_label(monkeypatch):
    """Output filenames should treat `camera_id` as the complete camera label.

    Data contract:
    - Inputs:
      - `monkeypatch`: pytest fixture used to stub hardware imports.
    - Output:
      - Asserts `cam0` appears once and is not expanded to `camcam0`.
    """
    module = load_acquisition_module(monkeypatch)

    filenames = module.make_output_filenames("/tmp/session", "cam0")

    assert all("_cam0_" in filename for filename in filenames)
    assert all("_camcam0_" not in filename for filename in filenames)


def test_make_output_filenames_preserves_nonstandard_camera_label(monkeypatch):
    """Output filenames should preserve nonstandard camera labels exactly.

    Data contract:
    - Inputs:
      - `monkeypatch`: pytest fixture used to stub hardware imports.
    - Output:
      - Asserts labels such as `side_cam` are not prefixed or normalized.
    """
    module = load_acquisition_module(monkeypatch)

    filenames = module.make_output_filenames("/tmp/session", "side_cam")

    assert all("_side_cam_" in filename for filename in filenames)
    assert all("_camside_cam_" not in filename for filename in filenames)
