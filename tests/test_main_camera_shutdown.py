import importlib
import sys
import types


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
