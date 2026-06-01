import logging
import sys
import time
import types
from collections import namedtuple

import pytest

pygame_stub = types.SimpleNamespace(
    event=types.SimpleNamespace(get=lambda: []),
    KEYDOWN=1,
    KEYUP=2,
    K_ESCAPE=27,
    K_1=1,
    K_2=2,
    K_3=3,
    K_4=4,
    K_5=5,
    K_6=6,
    K_7=7,
    K_q=ord("q"),
    K_w=ord("w"),
    K_e=ord("e"),
    K_r=ord("r"),
    K_t=ord("t"),
    K_y=ord("y"),
    K_a=ord("a"),
    K_g=ord("g"),
    K_l=ord("l"),
    K_z=ord("z"),
    K_x=ord("x"),
    K_b=ord("b"),
    K_v=ord("v"),
    K_d=ord("d"),
    K_f=ord("f"),
    K_s=ord("s"),
)
sys.modules.setdefault("pygame", pygame_stub)
sys.modules.setdefault("icecream", types.SimpleNamespace(ic=lambda *args, **kwargs: args[0] if args else None))

from essential import base_classes
from essential.base_classes import Presenter
from task_protocol.latent_inference_forage import latent_inference_model
from task_protocol.latent_inference_forage.latent_inference_model import LatentInferenceModel


FallbackInputEvent = namedtuple("FallbackInputEvent", ["name", "timestamp"])


class CallbackPresenter(Presenter):
    """Minimal presenter used to exercise inherited input callbacks.

    Data contract:
    - Inputs:
      - `task`: object with an `event_list` deque-like attribute.
    - Output:
      - Callback methods inherited from `Presenter` append events to `task.event_list`.
    """

    def __init__(self, task):
        self.task = task

    def run(self) -> None:
        """No-op run method required by the abstract base class.

        Data contract:
        - Inputs: none.
        - Output: returns `None`.
        """
        return None


class FakeTimer:
    """Controllable replacement for `threading.Timer` in model tests.

    Data contract:
    - Inputs:
      - `interval`: float, timer interval in seconds.
      - `function`: callable invoked by production timers when elapsed.
    - Output:
      - Instances record whether `start()` and `cancel()` were called.
    """

    instances = []

    def __init__(self, interval, function):
        self.interval = interval
        self.function = function
        self.started = False
        self.cancelled = False
        FakeTimer.instances.append(self)

    def start(self):
        """Record that the timer was started.

        Data contract:
        - Inputs: none.
        - Output: returns `None`; sets `started=True`.
        """
        self.started = True

    def cancel(self):
        """Record that the timer was cancelled.

        Data contract:
        - Inputs: none.
        - Output: returns `None`; sets `cancelled=True`.
        """
        self.cancelled = True


@pytest.fixture
def session_info():
    """Return minimal latent-inference settings for lick-processing tests.

    Data contract:
    - Inputs: none.
    - Output:
      - `dict` containing the task parameters required by `LatentInferenceModel`.
      - Time values are in seconds; reward sizes are irrelevant for these tests.
    """

    return {
        "max_correct_trials_in_block": 100,
        "intertrial_interval": 2.0,
        "lick_threshold": 1,
        "right_ix": 0,
        "left_ix": 1,
        "debounce_licks": False,
        "lick_min_time": 0.05,
        "lick_max_time": 1.0,
        "quiet_ITI": False,
        "use_dark_period": True,
        "epoch_length": 120.0,
        "dark_period_times": [10.0],
        "correct_reward_probability": 1.0,
        "incorrect_reward_probability": 0.0,
        "switch_probability": 0.0,
        "default_switch_probability": 0.0,
        "biased_switch_probability": 0.0,
        "biased_side": "none",
    }


@pytest.fixture(autouse=True)
def fake_timer(monkeypatch):
    """Replace background timers so tests do not spawn threads.

    Data contract:
    - Inputs:
      - `monkeypatch`: pytest fixture.
    - Output:
      - `FakeTimer.instances` records model timer usage.
    """

    FakeTimer.instances = []
    monkeypatch.setattr(latent_inference_model.threading, "Timer", FakeTimer)
    yield
    FakeTimer.instances = []


@pytest.fixture
def task(session_info):
    """Create a latent-inference model in the left patch with an open choice window.

    Data contract:
    - Inputs:
      - `session_info`: fixture dict.
    - Output:
      - `LatentInferenceModel` with state `left_patch`, empty event queue, and
        choice-window timestamps measured by `time.time()` seconds.
    """

    model = LatentInferenceModel(session_info=session_info)
    model.switch_to_left_patch()
    model.t_choice_window_open = time.time() - 1.0
    model.event_list.clear()
    model.presenter_commands.clear()
    model.trial_choice_list.clear()
    model.trial_choice_times.clear()
    model.trial_correct_list.clear()
    model.trial_reward_given.clear()
    return model


def make_event(name, timestamp):
    """Create an input event compatible with the new event contract.

    Data contract:
    - Inputs:
      - `name`: str event name such as `"left_entry"`.
      - `timestamp`: float seconds from `time.time()`.
    - Output:
      - Event object with `.name` and `.timestamp` attributes.
    """

    event_type = getattr(base_classes, "InputEvent", FallbackInputEvent)
    return event_type(name=name, timestamp=timestamp)


def test_callback_appends_input_event_and_keeps_normal_action_log(task, caplog):
    presenter = CallbackPresenter(task)

    with caplog.at_level(logging.INFO):
        presenter.left_entry()

    event = task.event_list[-1]
    assert event.name == "left_entry"
    assert isinstance(event.timestamp, float)
    assert any("[action];left_entry;" in record.message for record in caplog.records)


def test_iti_lick_is_discarded_from_choice_processing(task, caplog):
    task.activate_ITI()
    task.event_list.append(make_event("left_entry", time.time()))

    with caplog.at_level(logging.INFO):
        task.run_event_loop()

    assert len(task.event_list) == 0
    assert task.trial_choice_list == []
    assert any("[action];discarded_left_entry;reason_ITI" in record.message for record in caplog.records)


def test_discard_log_does_not_replace_normal_action_log(task, caplog):
    presenter = CallbackPresenter(task)
    task.activate_ITI()

    with caplog.at_level(logging.INFO):
        presenter.right_entry()
        task.run_event_loop()

    messages = [record.message for record in caplog.records]
    assert any("[action];right_entry;" in message for message in messages)
    assert any("[action];discarded_right_entry;reason_ITI" in message for message in messages)


def test_run_event_loop_drains_all_pending_events_with_threshold_two(session_info):
    session_info["lick_threshold"] = 2
    model = LatentInferenceModel(session_info=session_info)
    model.switch_to_left_patch()
    model.t_choice_window_open = time.time() - 1.0
    model.event_list.clear()
    event_time = time.time()
    model.event_list.append(make_event("left_entry", event_time))
    model.event_list.append(make_event("left_entry", event_time + 0.001))

    model.run_event_loop()

    assert len(model.event_list) == 0
    assert model.trial_choice_list == [session_info["left_ix"]]
    assert model.trial_correct_list == [True]


def test_stale_lick_timestamped_before_choice_window_cannot_trigger_choice(task, caplog):
    task.t_choice_window_open = time.time()
    stale_time = task.t_choice_window_open - 0.5
    task.event_list.append(make_event("left_entry", stale_time))

    with caplog.at_level(logging.INFO):
        task.run_event_loop()

    assert task.trial_choice_list == []
    assert any("[action];discarded_left_entry;reason_stale" in record.message for record in caplog.records)


def test_active_patch_lick_after_choice_window_triggers_choice(task):
    task.event_list.append(make_event("left_entry", task.t_choice_window_open + 0.1))

    task.run_event_loop()

    assert task.trial_choice_list == [task.session_info["left_ix"]]
    assert task.trial_correct_list == [True]


def test_dark_period_lick_is_discarded_from_choice_processing(task, caplog):
    task.switch_to_dark_period()
    task.event_list.append(make_event("left_entry", time.time()))

    with caplog.at_level(logging.INFO):
        task.run_event_loop()

    assert len(task.event_list) == 0
    assert task.trial_choice_list == []
    assert any("[action];discarded_left_entry;reason_dark_period" in record.message for record in caplog.records)


def test_quiet_iti_lick_restarts_iti_timer(session_info):
    session_info["quiet_ITI"] = True
    model = LatentInferenceModel(session_info=session_info)
    model.switch_to_left_patch()
    model.t_choice_window_open = time.time() - 1.0
    model.activate_ITI()
    original_timer = model.ITI_thread
    model.event_list.append(make_event("left_entry", time.time()))

    model.run_event_loop()

    assert original_timer.cancelled is True
    assert model.ITI_thread is not original_timer
    assert model.ITI_active is True


def test_string_events_still_work_through_normalize_event(task):
    task.event_list.append("left_entry")

    task.run_event_loop()

    assert task.trial_choice_list == [task.session_info["left_ix"]]
