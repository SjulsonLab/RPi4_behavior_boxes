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
        """Record a transfer; return bool success under the revised box contract."""
        self.transfer_called = True
        return True


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
    # Earlier tests may have imported these submodules onto the package itself.
    task_package = importlib.import_module("task_protocol.alternating_latent")
    monkeypatch.setattr(task_package, "alternating_latent_model", fake_model_module, raising=False)
    monkeypatch.setattr(task_package, "alternating_latent_presenter", fake_presenter_module, raising=False)
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
    monkeypatch.setattr(main_module.scipy.io, "savemat", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_module.os.path, "ismount", fake_external_mount)


def fake_external_mount(path):
    """Accept filesystem path; return True for tests with disposable external storage."""
    return True


@pytest.fixture
def timed_latent_session(monkeypatch, tmp_path):
    """Build a hardware-free session with independently adjustable setup delays.

    Inputs: pytest monkeypatch and tmp_path fixtures. Returns a SimpleNamespace
    with a run() callable, mutable clock/settings in seconds, the constructed
    model, task start/stop epoch seconds, and a list of plotted elapsed seconds.
    Each simulated presenter iteration advances the clock by one second.
    """
    module = load_main_with_fakes(monkeypatch, CompletingPresenter)
    prepare_main_for_shutdown_test(monkeypatch, module)
    session = types.SimpleNamespace(
        now=1_000_000.0,
        preview_delay=180.0,
        input_delay=45.0,
        controls_delay=15.0,
        model=None,
        task_started_at=None,
        stopped_at=None,
        plotted_times=[],
    )

    def current_time():
        """Return the simulated float epoch time in seconds; accepts no inputs."""
        return session.now

    def skip_sleep(seconds):
        """Accept sleep duration in seconds; return None without a real delay."""
        return None

    def record_task_start():
        """Record task start as float epoch seconds; no inputs or return value."""
        session.task_started_at = session.now

    def make_timed_model(session_info):
        """Accept settings dict; return a fake model with an epoch-second origin."""
        model = FakeModel(session_info)
        model.t_session_start = session.now
        model.start_task = record_task_start
        session.model = model
        return model

    def preview_camera(presenter):
        """Accept fake presenter; advance setup seconds and return None."""
        session.now += session.preview_delay

    def enter_duration():
        """Simulate input delay in seconds; accept no inputs and return 60 minutes."""
        session.now += session.input_delay
        return 60

    def print_controls(presenter):
        """Accept fake presenter; advance pre-task seconds and return None."""
        session.now += session.controls_delay

    def run_iteration(presenter):
        """Accept fake presenter; record elapsed seconds, advance 1 s, return None."""
        if len(session.plotted_times) >= 3_610:
            pytest.fail("Session did not stop after the configured duration")
        session.plotted_times.append(session.now - session.model.t_session_start)
        session.now += 1.0

    def stop_session(presenter):
        """Accept fake presenter; record stop epoch seconds, stop camera, return None."""
        session.stopped_at = session.now
        presenter.end_session_calls += 1
        presenter.box.video_stop()

    def run_session():
        """Run simulated latent inference; accept no inputs and return int status."""
        settings = make_session_info(tmp_path)
        settings["task_config"] = "latent_inference"
        return module.run_program(session_info=settings)

    # Select the latent-inference branch while keeping hardware-facing code fake.
    task_package = importlib.import_module("task_protocol.latent_inference_forage")
    model_module = types.SimpleNamespace(LatentInferenceModel=make_timed_model)
    presenter_module = types.SimpleNamespace(LatentInferencePresenter=CompletingPresenter)
    monkeypatch.setitem(sys.modules, task_package.__name__ + ".latent_inference_model", model_module)
    monkeypatch.setitem(sys.modules, task_package.__name__ + ".latent_inference_presenter", presenter_module)
    monkeypatch.setattr(task_package, "latent_inference_model", model_module, raising=False)
    monkeypatch.setattr(task_package, "latent_inference_presenter", presenter_module, raising=False)
    monkeypatch.setattr(module, "time", types.SimpleNamespace(time=current_time, sleep=skip_sleep))
    monkeypatch.setattr(module, "set_session_time", enter_duration)
    monkeypatch.setattr(CompletingPresenter, "start_session", preview_camera)
    monkeypatch.setattr(CompletingPresenter, "print_controls", print_controls)
    monkeypatch.setattr(CompletingPresenter, "run", run_iteration)
    monkeypatch.setattr(CompletingPresenter, "end_session", stop_session)
    session.run = run_session
    return session


@pytest.mark.parametrize("preview_delay,input_delay", [(0, 0), (180, 45), (1800, 120)])
def test_latent_session_plot_excludes_setup_delay(timed_latent_session, preview_delay, input_delay):
    """Accept timing fixture and setup seconds; assert plotted time starts at zero."""
    session = timed_latent_session
    session.preview_delay = preview_delay
    session.input_delay = input_delay

    assert session.run() == 0

    assert session.model.t_session_start == session.task_started_at
    assert session.plotted_times[0] == 0.0


def test_latent_session_stops_3600_seconds_after_task_start(timed_latent_session):
    """Accept timing fixture; assert 60 minutes of task time and no later trials."""
    session = timed_latent_session

    assert session.run() == 0

    assert session.stopped_at - session.task_started_at == 3_600.0
    assert session.plotted_times[-1] == 3_599.0
    assert len(session.plotted_times) == 3_600
    assert FakeBox.last_instance.video_stop_calls == 1


def test_failed_transfer_returns_nonzero_and_still_closes_gui(monkeypatch, tmp_path, capsys):
    """Accept fixtures; False transfer status yields a visible failure and GUI cleanup."""
    module = load_main_with_fakes(monkeypatch, InterruptingPresenter)
    prepare_main_for_shutdown_test(monkeypatch, module)
    cleanup_calls = []

    def failed_transfer(self):
        """Accept fake box; return False to simulate exhausted transfer retries."""
        return False

    def close_display():
        """Record display closure; no inputs or return value."""
        cleanup_calls.append("display")

    def close_pygame():
        """Record GUI closure; no inputs or return value."""
        cleanup_calls.append("pygame")

    monkeypatch.setattr(FakeBox, "transfer_files_to_external_storage", failed_transfer)
    monkeypatch.setattr(module.pygame.display, "quit", close_display)
    monkeypatch.setattr(module.pygame, "quit", close_pygame)
    assert module.run_program(session_info=make_session_info(tmp_path)) != 0
    assert cleanup_calls == ["display", "pygame"]
    assert "TRANSFER INCOMPLETE" in capsys.readouterr().out


def test_missing_mount_aborts_before_creating_external_session_directory(monkeypatch, tmp_path, capsys):
    """Accept fixtures; reject unmounted storage even when lsblk contains sda."""
    module = load_main_with_fakes(monkeypatch, InterruptingPresenter)
    prepare_main_for_shutdown_test(monkeypatch, module)

    def no_mount(path):
        """Accept path; simulate an unmounted external disk."""
        return False

    monkeypatch.setattr(module.os.path, "ismount", no_mount)
    session_info = make_session_info(tmp_path)
    assert module.run_program(session_info=session_info) != 0
    assert not Path(session_info["external_storage"]).exists()
    assert "mount" in capsys.readouterr().out.lower()


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
