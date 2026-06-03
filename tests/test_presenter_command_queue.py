import importlib
import sys
import types
from collections import deque

import pytest

pygame_stub = types.SimpleNamespace(
    event=types.SimpleNamespace(get=lambda: []),
    KEYDOWN=1,
    KEYUP=2,
    K_ESCAPE=27,
)
sys.modules.setdefault("pygame", pygame_stub)
sys.modules.setdefault("icecream", types.SimpleNamespace(ic=lambda *args, **kwargs: args[0] if args else None))

from task_protocol.alternating_latent.alternating_latent_model import AlternatingLatentModel
from task_protocol.alternating_latent.alternating_latent_presenter import AlternatingLatentPresenter
from task_protocol.flush.flush_model import FlushModel
from task_protocol.flush.flush_presenter import FlushPresenter
from task_protocol.latent_inference_forage.latent_inference_model import LatentInferenceModel
from task_protocol.latent_inference_forage.latent_inference_presenter import LatentInferencePresenter
from task_protocol.latent_inference_with_stimuli.stimulus_inference_presenter import StimulusInferencePresenter


class LateAppendCommandQueue:
    """Command queue that simulates a timer append after iteration finishes.

    Data contract:
    - Inputs:
      - `initial_commands`: iterable of str commands already queued.
      - `late_command`: str command appended when the old iterator becomes exhausted,
        or when the new drain loop checks an empty queue.
    - Output:
      - Queue-like object supporting iteration, `clear`, `append`, `popleft`, and truth testing.
    """

    def __init__(self, initial_commands, late_command):
        self.items = list(initial_commands)
        self.late_command = late_command
        self.late_command_injected = False
        self.clear_called = False

    def __iter__(self):
        """Yield initial commands, then inject the late command without yielding it.

        Data contract:
        - Inputs: none.
        - Output:
          - Iterator over commands present before the simulated timer append.
        """
        index = 0
        while index < len(self.items):
            yield self.items[index]
            index += 1
        if not self.late_command_injected:
            self.items.append(self.late_command)
            self.late_command_injected = True

    def __bool__(self):
        """Return whether the queue has work, injecting the late command once.

        Data contract:
        - Inputs: none.
        - Output:
          - `bool`, true when `popleft()` can return a command.
        """
        if self.items:
            return True
        if not self.late_command_injected:
            self.items.append(self.late_command)
            self.late_command_injected = True
            return True
        return False

    def append(self, command):
        """Append a command to the queue.

        Data contract:
        - Inputs:
          - `command`: str presenter command.
        - Output: returns `None`.
        """
        self.items.append(command)

    def popleft(self):
        """Remove and return the oldest command.

        Data contract:
        - Inputs: none.
        - Output:
          - `str`, oldest queued command.
        """
        return self.items.pop(0)

    def clear(self):
        """Clear queued commands.

        Data contract:
        - Inputs: none.
        - Output: returns `None`; records that `clear()` was called.
        """
        self.clear_called = True
        self.items.clear()


class HardwareSignal:
    """Small hardware double for LED, sound, and visual-stimulus channels.

    Data contract:
    - Inputs:
      - `name`: str channel name.
      - `event_log`: list collecting command tuples.
    - Output:
      - Methods append `(name, action, args)` tuples to `event_log`.
    """

    def __init__(self, name, event_log):
        self.name = name
        self.event_log = event_log
        self.value = False

    def on(self):
        """Record an on command.

        Data contract:
        - Inputs: none.
        - Output: returns `None`.
        """
        self.value = True
        self.event_log.append((self.name, "on", ()))

    def off(self):
        """Record an off command.

        Data contract:
        - Inputs: none.
        - Output: returns `None`.
        """
        self.value = False
        self.event_log.append((self.name, "off", ()))

    def toggle(self):
        """Record a toggle command.

        Data contract:
        - Inputs: none.
        - Output: returns `None`.
        """
        self.value = not self.value
        self.event_log.append((self.name, "toggle", ()))

    def blink(self, on_time, off_time=0.1):
        """Record a blink command.

        Data contract:
        - Inputs:
          - `on_time`: float seconds.
          - `off_time`: float seconds.
        - Output: returns `None`.
        """
        self.event_log.append((self.name, "blink", (on_time, off_time)))

    def display_default_greyscale(self):
        """Record default greyscale display.

        Data contract:
        - Inputs: none.
        - Output: returns `None`.
        """
        self.event_log.append((self.name, "display_default_greyscale", ()))

    def display_dark_greyscale(self):
        """Record dark greyscale display.

        Data contract:
        - Inputs: none.
        - Output: returns `None`.
        """
        self.event_log.append((self.name, "display_dark_greyscale", ()))


class BoxStub:
    """Behavior-box presenter double.

    Data contract:
    - Inputs: none.
    - Output:
      - Exposes cue LEDs, sound channels, and visual-stimulus methods used by presenters.
    """

    def __init__(self):
        self.events = []
        self.cueLED1 = HardwareSignal("cueLED1", self.events)
        self.cueLED2 = HardwareSignal("cueLED2", self.events)
        self.cueLED3 = HardwareSignal("cueLED3", self.events)
        self.sound1 = HardwareSignal("sound1", self.events)
        self.sound2 = HardwareSignal("sound2", self.events)
        self.sound3 = HardwareSignal("sound3", self.events)
        self.visualstim = HardwareSignal("visualstim", self.events)

    def clear(self):
        """Clear recorded hardware events.

        Data contract:
        - Inputs: none.
        - Output: returns `None`.
        """
        self.events.clear()


class PumpStub:
    """Pump double that records reward and toggle commands.

    Data contract:
    - Inputs: none.
    - Output:
      - `rewards`: list of `(pump_key, reward_size)` tuples.
      - `toggles`: list of pump-key strings.
    """

    def __init__(self):
        self.rewards = []
        self.toggles = []

    def reward(self, pump_key, reward_size):
        """Record a reward command.

        Data contract:
        - Inputs:
          - `pump_key`: str pump identifier.
          - `reward_size`: float reward amount in microliters.
        - Output: returns `None`.
        """
        self.rewards.append((pump_key, reward_size))

    def toggle(self, pump_key):
        """Record a pump toggle command.

        Data contract:
        - Inputs:
          - `pump_key`: str pump identifier.
        - Output: returns `None`.
        """
        self.toggles.append(pump_key)


@pytest.fixture(scope="module", autouse=True)
def cleanup_imported_protocol_modules():
    """Avoid leaking real task modules into tests that replace them with fakes.

    Data contract:
    - Inputs: none.
    - Output:
      - After this module's tests finish, removes imported protocol submodules from
        `sys.modules` and their parent package attributes.
    """
    yield
    imported_modules = [
        ("task_protocol.alternating_latent", "alternating_latent_model"),
        ("task_protocol.alternating_latent", "alternating_latent_presenter"),
        ("task_protocol.flush", "flush_model"),
        ("task_protocol.flush", "flush_presenter"),
    ]
    for package_name, module_attr in imported_modules:
        package = importlib.import_module(package_name)
        if hasattr(package, module_attr):
            delattr(package, module_attr)
        sys.modules.pop(f"{package_name}.{module_attr}", None)


@pytest.fixture
def session_info():
    """Return behavior-task settings used by presenter command tests.

    Data contract:
    - Inputs: none.
    - Output:
      - `dict` with time values in seconds and reward sizes in microliters.
    """
    return {
        "intertrial_interval": 1.0,
        "lick_threshold": 1,
        "right_ix": 0,
        "left_ix": 1,
        "debounce_licks": False,
        "lick_min_time": 0.05,
        "lick_max_time": 1.0,
        "quiet_ITI": False,
        "right_reward_pump": "3",
        "left_reward_pump": "2",
        "reward_size_large": 5,
        "reward_size_small": 0,
        "max_correct_trials_in_block": 3,
        "counterbalance_type": "leftA",
        "ephys_rig": False,
        "num_sounds": 2,
        "grating_duration": 0.01,
        "stimulus_duration": 0.05,
        "inter_grating_interval": 0.01,
    }


def test_active_models_initialize_presenter_commands_as_deque(session_info):
    """Active task models should expose presenter commands as a drainable deque.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
    - Output:
      - Asserts the three active models use `collections.deque`.
    """
    assert isinstance(LatentInferenceModel(session_info).presenter_commands, deque)
    assert isinstance(AlternatingLatentModel(session_info).presenter_commands, deque)
    assert isinstance(FlushModel(session_info).presenter_commands, deque)


def test_latent_presenter_does_not_clear_late_timer_command(session_info):
    """Latent presenter should process a command appended after drain exhaustion.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
    - Output:
      - Asserts a simulated timer-appended `turn_LED_on` command is not erased.
    """
    task = types.SimpleNamespace(
        presenter_commands=LateAppendCommandQueue(["turn_LED_off"], "turn_LED_on"),
    )
    box = BoxStub()
    presenter = LatentInferencePresenter(task, box, PumpStub(), gui=None, session_info=session_info)

    presenter.perform_task_commands(correct_pump="3", incorrect_pump="2")

    assert ("cueLED1", "off", ()) in box.events
    assert ("cueLED2", "off", ()) in box.events
    assert ("cueLED1", "on", ()) in box.events
    assert ("cueLED2", "on", ()) in box.events
    assert task.presenter_commands.clear_called is False


def test_alternating_presenter_does_not_clear_late_command(session_info):
    """Alternating presenter should drain late commands without a final clear.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
    - Output:
      - Asserts both initial and late reward commands are processed in order.
    """
    task = types.SimpleNamespace(
        presenter_commands=LateAppendCommandQueue(["give_correct_reward"], "give_incorrect_reward"),
        rewards_earned_in_block=0,
        trial_reward_given=[],
        state="left_patch",
    )
    pump = PumpStub()
    presenter = AlternatingLatentPresenter(task, BoxStub(), pump, gui=None, session_info=session_info)

    presenter.perform_task_commands(correct_pump="2", incorrect_pump="3")

    assert pump.rewards == [("2", 5), ("3", 0)]
    assert task.trial_reward_given == [True, False]
    assert task.presenter_commands.clear_called is False


def test_flush_presenter_does_not_clear_late_command(session_info):
    """Flush presenter should drain late commands without a final clear.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
    - Output:
      - Asserts both initial and late pump toggles are processed in order.
    """
    task = types.SimpleNamespace(
        presenter_commands=LateAppendCommandQueue(["toggle_pump1"], "toggle_pump2"),
    )
    pump = PumpStub()
    presenter = FlushPresenter(task, BoxStub(), pump, gui=None, session_info=session_info)

    presenter.perform_task_commands()

    assert pump.toggles == ["1", "2"]
    assert task.presenter_commands.clear_called is False


@pytest.mark.parametrize(
    "current_stimulus, expected_event",
    [
        ("A", ("sound1", "blink", (0.1, 0.1))),
        ("B", ("sound3", "blink", (0.2, 0.1))),
        (None, ("sound2", "on", ())),
    ],
)
def test_stimulus_presenter_handles_turn_sounds_on(session_info, current_stimulus, expected_event):
    """Stimulus presenter should handle `turn_sounds_on` for A, B, and neutral states.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
      - `current_stimulus`: optional str current stimulus label.
      - `expected_event`: tuple describing the expected hardware call.
    - Output:
      - Asserts `match_command("turn_sounds_on")` does not raise and drives sounds.
    """
    task = types.SimpleNamespace(state="left_patch", presenter_commands=deque())
    box = BoxStub()
    presenter = StimulusInferencePresenter(task, box, PumpStub(), gui=None, session_info=session_info)
    presenter.current_stimulus = current_stimulus
    box.clear()

    presenter.match_command("turn_sounds_on", correct_pump="2", incorrect_pump="3")

    assert expected_event in box.events


def test_stimulus_presenter_turn_sounds_off_still_turns_all_sounds_off(session_info):
    """Existing `turn_sounds_off` behavior should remain intact.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
    - Output:
      - Asserts all sound channels receive `off`.
    """
    task = types.SimpleNamespace(state="left_patch", presenter_commands=deque())
    box = BoxStub()
    presenter = StimulusInferencePresenter(task, box, PumpStub(), gui=None, session_info=session_info)
    box.clear()

    presenter.match_command("turn_sounds_off", correct_pump="2", incorrect_pump="3")

    assert ("sound1", "off", ()) in box.events
    assert ("sound2", "off", ()) in box.events
    assert ("sound3", "off", ()) in box.events


def test_stimulus_presenter_perform_task_commands_drains_deque(session_info):
    """Stimulus presenter should drain deque-backed command queues.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
    - Output:
      - Asserts `perform_task_commands()` processes a deque command and leaves it empty.
    """
    task = types.SimpleNamespace(state="left_patch", presenter_commands=deque(["turn_sounds_off"]))
    box = BoxStub()
    presenter = StimulusInferencePresenter(task, box, PumpStub(), gui=None, session_info=session_info)
    box.clear()

    presenter.perform_task_commands(correct_pump="2", incorrect_pump="3")

    assert len(task.presenter_commands) == 0
    assert ("sound1", "off", ()) in box.events
    assert ("sound2", "off", ()) in box.events
    assert ("sound3", "off", ()) in box.events
