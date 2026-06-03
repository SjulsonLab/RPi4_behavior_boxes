import sys
import threading
import types

import pytest

pygame_stub = types.SimpleNamespace(
    event=types.SimpleNamespace(get=lambda: []),
    KEYDOWN=1,
    KEYUP=2,
    K_ESCAPE=27,
)
sys.modules.setdefault("pygame", pygame_stub)
sys.modules.setdefault("icecream", types.SimpleNamespace(ic=lambda *args, **kwargs: args[0] if args else None))

from task_protocol.latent_inference_with_stimuli.stimulus_inference_model import StimulusInferenceModel
from task_protocol.latent_inference_with_stimuli.stimulus_inference_presenter import StimulusInferencePresenter


class HardwareStub:
    """Minimal hardware object that records method calls by name.

    Data contract:
    - Inputs: none.
    - Output:
      - Attribute access returns objects whose `on`, `off`, `blink`, and visual-display
        methods append call names to `calls`.
    """

    def __init__(self):
        self.calls = []

    def on(self):
        """Record an on command.

        Data contract:
        - Inputs: none.
        - Output: returns `None`; appends `"on"` to `calls`.
        """
        self.calls.append("on")

    def off(self):
        """Record an off command.

        Data contract:
        - Inputs: none.
        - Output: returns `None`; appends `"off"` to `calls`.
        """
        self.calls.append("off")

    def blink(self, on_time, off_time):
        """Record a blink command.

        Data contract:
        - Inputs:
          - `on_time`: float seconds.
          - `off_time`: float seconds.
        - Output: returns `None`; appends `"blink"` to `calls`.
        """
        self.calls.append(("blink", on_time, off_time))

    def display_default_greyscale(self):
        """Record default greyscale display.

        Data contract:
        - Inputs: none.
        - Output: returns `None`; appends `"display_default_greyscale"` to `calls`.
        """
        self.calls.append("display_default_greyscale")

    def display_dark_greyscale(self):
        """Record dark greyscale display.

        Data contract:
        - Inputs: none.
        - Output: returns `None`; appends `"display_dark_greyscale"` to `calls`.
        """
        self.calls.append("display_dark_greyscale")

    def show_grating(self, grating_name):
        """Record a grating presentation.

        Data contract:
        - Inputs:
          - `grating_name`: str filename.
        - Output: returns `None`; appends `("show_grating", grating_name)` to `calls`.
        """
        self.calls.append(("show_grating", grating_name))


class BoxStub:
    """Minimal behavior box for stimulus presenter tests.

    Data contract:
    - Inputs: none.
    - Output:
      - Provides LED, sound, and visualstim attributes used by `StimulusInferencePresenter`.
    """

    def __init__(self):
        self.cueLED1 = HardwareStub()
        self.cueLED2 = HardwareStub()
        self.cueLED3 = HardwareStub()
        self.sound1 = HardwareStub()
        self.sound2 = HardwareStub()
        self.sound3 = HardwareStub()
        self.visualstim = HardwareStub()


@pytest.fixture
def session_info():
    """Return minimal stimulus-inference settings.

    Data contract:
    - Inputs: none.
    - Output:
      - `dict` with time values in seconds and reward sizes in microliters.
    """

    return {
        "max_correct_trials_in_block": 3,
        "intertrial_interval": 1.0,
        "lick_threshold": 1,
        "p_stimulus": 1.0,
        "epoch_length": 100.0,
        "dark_period_times": [1.0],
        "reward_size_large": 5,
        "reward_size_small": 0,
        "right_reward_pump": "3",
        "left_reward_pump": "2",
        "counterbalance_type": "leftA",
        "ephys_rig": False,
        "num_sounds": 2,
        "grating_duration": 0.01,
        "stimulus_duration": 0.05,
        "inter_grating_interval": 0.01,
    }


def make_model(session_info):
    """Create a stimulus-inference model with nonzero block counters.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
    - Output:
      - `StimulusInferenceModel` with counters set to nonzero test values.
    """

    model = StimulusInferenceModel(session_info=session_info)
    model.rewards_earned_in_block = 2
    model.correct_trials_in_block = 2
    model.presenter_commands.clear()
    return model


def make_presenter(session_info):
    """Create a stimulus presenter with stubbed hardware.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
    - Output:
      - `StimulusInferencePresenter`.
    """

    model = StimulusInferenceModel(session_info=session_info)
    box = BoxStub()
    return StimulusInferencePresenter(model=model, box=box, pump=None, gui=None, session_info=session_info)


@pytest.mark.parametrize(
    "method_name, expected_command",
    [
        ("enter_left_patch", "turn_L_stimulus_on"),
        ("enter_right_patch", "turn_R_stimulus_on"),
        ("exit_left_patch", None),
        ("exit_right_patch", None),
    ],
)
def test_stimulus_patch_transitions_preserve_parent_counter_resets(session_info, method_name, expected_command):
    """Stimulus patch hooks should keep parent block-counter bookkeeping.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
      - `method_name`: str name of patch transition hook.
      - `expected_command`: optional str stimulus command expected on patch entry.
    - Output:
      - Asserts counters reset to zero and stimulus commands are still queued when expected.
    """

    model = make_model(session_info)

    getattr(model, method_name)()

    assert model.rewards_earned_in_block == 0
    assert model.correct_trials_in_block == 0
    if expected_command is not None:
        assert expected_command in model.presenter_commands


def test_join_stimulus_threads_skips_current_thread(session_info):
    """Joining stimulus threads should not join the currently running thread.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
    - Output:
      - Asserts calling `join_stimulus_threads()` inside the stimulus thread does not
        raise `RuntimeError`.
    """

    presenter = make_presenter(session_info)
    errors = []

    def call_join_from_stimulus_thread():
        presenter.stimulus_A_thread = threading.current_thread()
        try:
            presenter.join_stimulus_threads()
        except RuntimeError as error:
            errors.append(error)

    thread = threading.Thread(target=call_join_from_stimulus_thread)
    thread.start()
    thread.join()

    assert errors == []


def test_stimulus_loop_dark_period_shutdown_does_not_join_current_thread(session_info, monkeypatch):
    """Dark-period shutdown inside `stimulus_loop()` should not self-join.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
      - `monkeypatch`: pytest fixture.
    - Output:
      - Asserts `stimulus_loop()` returns without `RuntimeError` when the task enters
        dark period during the loop.
    """

    presenter = make_presenter(session_info)
    presenter.current_stimulus = "A"
    presenter.task.state = "left_patch"
    presenter.stimulus_A_thread = threading.current_thread()
    monkeypatch.setattr(
        "task_protocol.latent_inference_with_stimuli.stimulus_inference_presenter.time.sleep",
        lambda duration: None,
    )

    def enter_dark_period():
        presenter.task.state = "dark_period"

    presenter.stimulus_loop("vertical_grating_0.01s.dat", enter_dark_period, prev_stim_thread=None)

    assert presenter.task.state == "dark_period"
