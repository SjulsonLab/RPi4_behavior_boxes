import importlib
import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest


class FakeBox:
    """Minimal behavior-box test double that records camera stop calls."""

    last_instance = None

    def __init__(self, session_info):
        self.session_info = session_info
        self.video_stop_calls = 0
        FakeBox.last_instance = self

    def set_callbacks(self, presenter):
        self.presenter = presenter

    def video_stop(self):
        self.video_stop_calls += 1

    def transfer_files_to_external_storage(self):
        self.transfer_called = True


class FakePump:
    """Minimal pump test double for main.run_program construction."""

    def __init__(self, session_info):
        self.session_info = session_info


class FakeModel:
    """Minimal task model with the command queues used by main.run_program."""

    def __init__(self, session_info):
        self.session_info = session_info
        self.presenter_commands = []

    def start_task(self):
        """No-op task startup hook.

        Data contract:
        - Inputs: none.
        - Output: returns `None`.
        """
        return None


class InterruptingPresenter:
    """Presenter that simulates Ctrl-C immediately after session start."""

    def __init__(self, model, box, pump, gui, session_info):
        self.box = box
        self.end_session_calls = 0

    def start_session(self):
        raise KeyboardInterrupt

    def end_session(self):
        self.end_session_calls += 1
        self.box.video_stop()


class FailingEndSessionPresenter(InterruptingPresenter):
    """Presenter that fails before it can stop the camera."""

    def end_session(self):
        self.end_session_calls += 1
        raise RuntimeError("end_session failed before camera stop")


class CompletingPresenter(InterruptingPresenter):
    """Presenter that lets startup proceed until the timed task loop exits."""

    def __init__(self, model, box, pump, gui, session_info):
        super().__init__(model, box, pump, gui, session_info)
        self.print_controls_calls = 0

    def start_session(self):
        """Allow normal startup to continue.

        Data contract:
        - Inputs: none.
        - Output: returns `None`.
        """
        return None

    def print_controls(self):
        """Record that controls would be printed.

        Data contract:
        - Inputs: none.
        - Output: returns `None`; increments `print_controls_calls`.
        """
        self.print_controls_calls += 1

    def run(self):
        """No-op task loop iteration.

        Data contract:
        - Inputs: none.
        - Output: returns `None`.
        """
        return None


def load_main_with_fakes(monkeypatch, presenter_class):
    """Import main.py with hardware-facing modules replaced by fakes."""

    fake_pygame = types.SimpleNamespace(
        display=types.SimpleNamespace(quit=lambda: None),
        quit=lambda: None,
    )
    fake_gui_module = types.SimpleNamespace(PygameGUI=lambda session_info: object())
    fake_behavbox_module = types.SimpleNamespace(BehavBox=FakeBox, Pump=FakePump)
    fake_model_module = types.SimpleNamespace(AlternatingLatentModel=FakeModel)
    fake_presenter_module = types.SimpleNamespace(
        AlternatingLatentPresenter=presenter_class
    )

    monkeypatch.setitem(sys.modules, "pygame", fake_pygame)
    monkeypatch.setitem(sys.modules, "essential.gui", fake_gui_module)
    monkeypatch.setitem(sys.modules, "essential.behavbox", fake_behavbox_module)
    monkeypatch.setitem(
        sys.modules,
        "task_protocol.alternating_latent.alternating_latent_model",
        fake_model_module,
    )
    monkeypatch.setitem(
        sys.modules,
        "task_protocol.alternating_latent.alternating_latent_presenter",
        fake_presenter_module,
    )
    monkeypatch.setitem(
        sys.modules,
        "icecream",
        types.SimpleNamespace(ic=lambda *args, **kwargs: None),
    )

    sys.modules.pop("main", None)
    return importlib.import_module("main")


def make_session_info(tmp_path):
    return {
        "debug": False,
        "mouse_name": "test_mouse",
        "buffer_dir": str(tmp_path / "buffer"),
        "external_storage": str(tmp_path / "external"),
        "visual_stimulus": False,
        "task_config": "alternating_latent",
        "treadmill": False,
        "control": False,
    }


def prepare_main_for_shutdown_test(monkeypatch, main_module):
    monkeypatch.setattr(main_module, "confirm_options", lambda session_info: True)
    monkeypatch.setattr(main_module, "check_output", lambda command: b"sda\n")
    monkeypatch.setattr(main_module.scipy.io, "savemat", lambda *args, **kwargs: None)


def test_keyboard_interrupt_stops_camera_only_once_after_successful_end_session(
    monkeypatch, tmp_path
):
    main_module = load_main_with_fakes(monkeypatch, InterruptingPresenter)
    prepare_main_for_shutdown_test(monkeypatch, main_module)

    exit_code = main_module.run_program(session_info=make_session_info(tmp_path))

    assert exit_code == 0
    assert FakeBox.last_instance.video_stop_calls == 1


def test_keyboard_interrupt_uses_fallback_video_stop_if_end_session_fails(
    monkeypatch, tmp_path
):
    main_module = load_main_with_fakes(monkeypatch, FailingEndSessionPresenter)
    prepare_main_for_shutdown_test(monkeypatch, main_module)

    exit_code = main_module.run_program(session_info=make_session_info(tmp_path))

    assert exit_code == 0
    assert FakeBox.last_instance.video_stop_calls == 1


def test_startup_does_not_require_box_presenter_commands(monkeypatch, tmp_path):
    main_module = load_main_with_fakes(monkeypatch, CompletingPresenter)
    prepare_main_for_shutdown_test(monkeypatch, main_module)
    monkeypatch.setattr(main_module, "set_session_time", lambda: 0)

    exit_code = main_module.run_program(session_info=make_session_info(tmp_path))

    assert exit_code == 0
    assert FakeBox.last_instance.video_stop_calls == 1


def test_parse_args_accepts_external_output_dir(monkeypatch):
    """Command-line parsing should accept an external output parent directory.

    Data contract:
    - Inputs:
      - `monkeypatch`: pytest fixture for fake hardware imports.
    - Output:
      - Asserts parsed args expose the requested relative parent path string.
    """
    main_module = load_main_with_fakes(monkeypatch, CompletingPresenter)

    args = main_module.parse_args([
        "--external-output-dir",
        "CT020_20260603_latent_inference/rpi",
    ])

    assert args.external_output_dir == "CT020_20260603_latent_inference/rpi"


def test_configure_session_output_paths_uses_relative_external_output_parent(monkeypatch, tmp_path):
    """Relative external parents should resolve under external storage and keep session naming.

    Data contract:
    - Inputs:
      - `monkeypatch`: pytest fixture for fake hardware imports.
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts `external_storage_dir` is `<external parent>/<session_name>`.
    """
    main_module = load_main_with_fakes(monkeypatch, CompletingPresenter)
    session_info = make_session_info(tmp_path)
    external_parent = Path(session_info["external_storage"]) / "CT020_20260603_latent_inference" / "rpi"
    external_parent.mkdir(parents=True)

    configured = main_module.configure_session_output_paths(
        session_info,
        datestr="2026-06-03",
        timestr="123456",
        external_output_dir="CT020_20260603_latent_inference/rpi",
    )

    expected_session_name = "test_mouse_2026-06-03_123456"
    assert configured["session_name"] == expected_session_name
    assert configured["external_storage_dir"] == str(external_parent / expected_session_name)


def test_configure_session_output_paths_uses_absolute_external_output_parent(monkeypatch, tmp_path):
    """Absolute external parents under external storage should keep session naming.

    Data contract:
    - Inputs:
      - `monkeypatch`: pytest fixture for fake hardware imports.
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts an absolute parent path is used as `<parent>/<session_name>`.
    """
    main_module = load_main_with_fakes(monkeypatch, CompletingPresenter)
    session_info = make_session_info(tmp_path)
    external_parent = Path(session_info["external_storage"]) / "CT020_20260603_latent_inference" / "rpi"
    external_parent.mkdir(parents=True)

    configured = main_module.configure_session_output_paths(
        session_info,
        datestr="2026-06-03",
        timestr="123456",
        external_output_dir=str(external_parent),
    )

    expected_session_name = "test_mouse_2026-06-03_123456"
    assert configured["external_storage_dir"] == str(external_parent / expected_session_name)


def test_external_output_parent_must_exist(monkeypatch, tmp_path):
    """External output parent validation should not auto-create the requested parent.

    Data contract:
    - Inputs:
      - `monkeypatch`: pytest fixture for fake hardware imports.
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts missing parent directories raise `RuntimeError`.
    """
    main_module = load_main_with_fakes(monkeypatch, CompletingPresenter)
    session_info = make_session_info(tmp_path)

    with pytest.raises(RuntimeError, match="does not exist"):
        main_module.configure_session_output_paths(
            session_info,
            datestr="2026-06-03",
            timestr="123456",
            external_output_dir="CT020_20260603_latent_inference/rpi",
        )


def test_external_output_parent_must_be_under_external_storage(monkeypatch, tmp_path):
    """External output parents outside external storage should be rejected.

    Data contract:
    - Inputs:
      - `monkeypatch`: pytest fixture for fake hardware imports.
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts absolute paths outside `external_storage` raise `RuntimeError`.
    """
    main_module = load_main_with_fakes(monkeypatch, CompletingPresenter)
    session_info = make_session_info(tmp_path)
    outside_parent = tmp_path / "outside" / "rpi"
    outside_parent.mkdir(parents=True)

    with pytest.raises(RuntimeError, match="must be inside external storage"):
        main_module.configure_session_output_paths(
            session_info,
            datestr="2026-06-03",
            timestr="123456",
            external_output_dir=str(outside_parent),
        )


def test_run_program_applies_external_output_dir_to_session_info(monkeypatch, tmp_path):
    """Startup should pass the requested external parent into session path configuration.

    Data contract:
    - Inputs:
      - `monkeypatch`: pytest fixture for fake hardware imports.
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts the behavior box receives a session-specific destination under the parent.
    """
    main_module = load_main_with_fakes(monkeypatch, CompletingPresenter)
    prepare_main_for_shutdown_test(monkeypatch, main_module)
    monkeypatch.setattr(main_module, "set_session_time", lambda: 0)
    session_info = make_session_info(tmp_path)
    external_parent = Path(session_info["external_storage"]) / "CT020_20260603_latent_inference" / "rpi"
    external_parent.mkdir(parents=True)

    exit_code = main_module.run_program(
        session_info=session_info,
        external_output_dir="CT020_20260603_latent_inference/rpi",
    )

    assert exit_code == 0
    assert FakeBox.last_instance.session_info["external_storage_dir"] == str(
        external_parent / FakeBox.last_instance.session_info["session_name"]
    )


def test_make_json_safe_converts_numpy_and_nonfinite_values(monkeypatch):
    """Session-info JSON conversion should produce strict, readable JSON values.

    Data contract:
    - Inputs:
      - `monkeypatch`: pytest fixture for fake hardware imports.
    - Output:
      - Asserts nested NumPy values and non-finite floats become JSON-safe values.
    """
    main_module = load_main_with_fakes(monkeypatch, CompletingPresenter)

    converted = main_module.make_json_safe(
        {
            "positive_infinity": np.inf,
            "negative_infinity": -np.inf,
            "not_a_number": np.nan,
            "numpy_int": np.int64(7),
            "numpy_float": np.float64(1.25),
            "path": Path("/tmp/session"),
            "nested": [np.float32(2.5), {"flag": np.bool_(True)}],
        }
    )

    assert converted == {
        "positive_infinity": "Infinity",
        "negative_infinity": "-Infinity",
        "not_a_number": "NaN",
        "numpy_int": 7,
        "numpy_float": 1.25,
        "path": "/tmp/session",
        "nested": [2.5, {"flag": True}],
    }
    json.dumps(converted, allow_nan=False)


def test_run_program_saves_readable_session_info_json(monkeypatch, tmp_path):
    """Startup should save a JSON sidecar beside the pickle session-info file.

    Data contract:
    - Inputs:
      - `monkeypatch`: pytest fixture for fake hardware imports.
      - `tmp_path`: pytest temporary directory fixture.
    - Output:
      - Asserts `_session_info.json` exists and contains representative settings.
    """
    main_module = load_main_with_fakes(monkeypatch, CompletingPresenter)
    prepare_main_for_shutdown_test(monkeypatch, main_module)
    monkeypatch.setattr(main_module, "set_session_time", lambda: 0)
    session_info = make_session_info(tmp_path)
    session_info["errors_to_reward_delivery"] = np.inf

    exit_code = main_module.run_program(session_info=session_info)

    assert exit_code == 0
    saved_session_info = FakeBox.last_instance.session_info
    json_path = (
        Path(saved_session_info["output_dir"])
        / (saved_session_info["file_basename"] + "_session_info.json")
    )
    assert json_path.is_file()

    with open(json_path, "r") as f:
        json_session_info = json.load(f)

    assert json_session_info["mouse_name"] == saved_session_info["mouse_name"]
    assert json_session_info["task_config"] == saved_session_info["task_config"]
    assert json_session_info["output_dir"] == saved_session_info["output_dir"]
    assert json_session_info["external_storage_dir"] == saved_session_info["external_storage_dir"]
    assert json_session_info["errors_to_reward_delivery"] == "Infinity"
