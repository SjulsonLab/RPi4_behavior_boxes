import logging
import importlib
import sys
import time
import types

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

from essential.base_classes import InputEvent
from task_protocol.alternating_latent import alternating_latent_model
from task_protocol.alternating_latent.alternating_latent_model import AlternatingLatentModel
from task_protocol.alternating_latent.alternating_latent_presenter import AlternatingLatentPresenter
from task_protocol.flush.flush_model import FlushModel


class FakeTimer:
    """Controllable replacement for `threading.Timer`.

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
        """Record timer start.

        Data contract:
        - Inputs: none.
        - Output: returns `None`; sets `started=True`.
        """
        self.started = True

    def cancel(self):
        """Record timer cancellation.

        Data contract:
        - Inputs: none.
        - Output: returns `None`; sets `cancelled=True`.
        """
        self.cancelled = True


class PumpStub:
    """Presenter pump double that records delivered rewards.

    Data contract:
    - Inputs: none.
    - Output:
      - `rewards`: list of `(pump_key, reward_size)` tuples.
    """

    def __init__(self):
        self.rewards = []

    def reward(self, pump_key, reward_size):
        """Record a reward delivery request.

        Data contract:
        - Inputs:
          - `pump_key`: str pump identifier.
          - `reward_size`: float reward amount in microliters.
        - Output: returns `None`.
        """
        self.rewards.append((pump_key, reward_size))


@pytest.fixture(autouse=True)
def fake_timers(monkeypatch):
    """Replace model timers so tests do not spawn background threads.

    Data contract:
    - Inputs:
      - `monkeypatch`: pytest fixture.
    - Output:
      - `FakeTimer.instances` records timer usage.
    """

    FakeTimer.instances = []
    monkeypatch.setattr(alternating_latent_model.threading, "Timer", FakeTimer)
    yield
    FakeTimer.instances = []


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
        ("task_protocol.flush", "flush_model"),
    ]
    for package_name, module_attr in imported_modules:
        package = importlib.import_module(package_name)
        if hasattr(package, module_attr):
            delattr(package, module_attr)
        sys.modules.pop(f"{package_name}.{module_attr}", None)


@pytest.fixture
def session_info():
    """Return minimal behavior-task settings for event compatibility tests.

    Data contract:
    - Inputs: none.
    - Output:
      - `dict` with time values in seconds and reward sizes in microliters.
    """

    return {
        "intertrial_interval": 2.0,
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
    }


def make_event(name, timestamp=None):
    """Create a timestamped input event.

    Data contract:
    - Inputs:
      - `name`: str event name.
      - `timestamp`: optional float seconds from `time.time()`.
    - Output:
      - `InputEvent`.
    """
    return InputEvent(name=name, timestamp=time.time() if timestamp is None else timestamp)


def make_alternating_model(session_info, state="left_patch"):
    """Create an alternating-latent model in a choice state.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
      - `state`: str, either `"left_patch"` or `"right_patch"`.
    - Output:
      - `AlternatingLatentModel` with empty event and command queues.
    """
    model = AlternatingLatentModel(session_info=session_info)
    if state == "left_patch":
        model.switch_to_left_patch()
    elif state == "right_patch":
        model.switch_to_right_patch()
    else:
        raise ValueError("Unsupported state")
    model.event_list.clear()
    model.presenter_commands.clear()
    return model


def make_alternating_presenter(model, session_info, monkeypatch):
    """Create an alternating presenter with plotting disabled.

    Data contract:
    - Inputs:
      - `model`: `AlternatingLatentModel`.
      - `session_info`: dict fixture.
      - `monkeypatch`: pytest fixture.
    - Output:
      - Tuple `(presenter, pump)` where `pump` records reward deliveries.
    """
    pump = PumpStub()
    presenter = AlternatingLatentPresenter(
        model=model,
        box=types.SimpleNamespace(),
        pump=pump,
        gui=None,
        session_info=session_info,
    )
    monkeypatch.setattr(presenter, "update_plot", lambda *args, **kwargs: None)
    return presenter, pump


def test_alternating_latent_input_event_left_choice_still_rewards_left_patch(session_info):
    model = make_alternating_model(session_info, state="left_patch")
    model.event_list.append(make_event("left_entry"))

    model.run_event_loop()

    assert model.trial_choice_list == [session_info["left_ix"]]
    assert model.trial_correct_list == [True]
    assert list(model.presenter_commands) == ["give_correct_reward"]
    assert model.rewards_earned_in_block == 0


def test_alternating_latent_input_event_right_choice_still_rewards_right_patch(session_info):
    model = make_alternating_model(session_info, state="right_patch")
    model.event_list.append(make_event("right_entry"))

    model.run_event_loop()

    assert model.trial_choice_list == [session_info["right_ix"]]
    assert model.trial_correct_list == [True]
    assert list(model.presenter_commands) == ["give_correct_reward"]
    assert model.rewards_earned_in_block == 0


def test_alternating_latent_threshold_two_counts_two_events_in_one_drain(session_info):
    session_info["lick_threshold"] = 2
    model = make_alternating_model(session_info, state="left_patch")
    event_time = time.time()
    model.event_list.append(make_event("left_entry", event_time))
    model.event_list.append(make_event("left_entry", event_time + 0.001))

    model.run_event_loop()

    assert len(model.event_list) == 0
    assert model.trial_choice_list == [session_info["left_ix"]]
    assert list(model.presenter_commands) == ["give_correct_reward"]


def test_alternating_latent_iti_lick_is_logged_discarded_and_no_choice(session_info, caplog):
    model = make_alternating_model(session_info, state="left_patch")
    model.activate_ITI()
    model.event_list.append(make_event("left_entry"))

    with caplog.at_level(logging.INFO):
        model.run_event_loop()

    assert len(model.event_list) == 0
    assert model.trial_choice_list == []
    assert any("[action];discarded_left_entry;reason_ITI" in record.message for record in caplog.records)


def test_alternating_latent_quiet_iti_lick_restarts_iti(session_info):
    session_info["quiet_ITI"] = True
    model = make_alternating_model(session_info, state="left_patch")
    model.activate_ITI()
    original_timer = model.ITI_thread
    model.event_list.append(make_event("left_entry"))

    model.run_event_loop()

    assert original_timer.cancelled is True
    assert model.ITI_thread is not original_timer
    assert model.ITI_active is True


def test_alternating_presenter_processes_iti_events_through_model(session_info, monkeypatch, caplog):
    """Presenter should not silently clear ITI licks before model discard logging.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
      - `monkeypatch`: pytest fixture.
      - `caplog`: pytest log capture fixture.
    - Output:
      - Asserts presenter-run drains ITI events through model logic and logs discard.
    """
    model = make_alternating_model(session_info, state="left_patch")
    presenter, _ = make_alternating_presenter(model, session_info, monkeypatch)
    model.activate_ITI()
    model.event_list.append(make_event("left_entry"))

    with caplog.at_level(logging.INFO):
        presenter.run()

    assert len(model.event_list) == 0
    assert model.trial_choice_list == []
    assert any("[action];discarded_left_entry;reason_ITI" in record.message for record in caplog.records)


def test_alternating_presenter_quiet_iti_lick_restarts_iti(session_info, monkeypatch):
    """Presenter-run should preserve model quiet-ITI extension behavior.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
      - `monkeypatch`: pytest fixture.
    - Output:
      - Asserts an ITI lick cancels the old timer and starts a replacement timer.
    """
    session_info["quiet_ITI"] = True
    model = make_alternating_model(session_info, state="left_patch")
    presenter, _ = make_alternating_presenter(model, session_info, monkeypatch)
    model.activate_ITI()
    original_timer = model.ITI_thread
    model.event_list.append(make_event("left_entry"))

    presenter.run()

    assert original_timer.cancelled is True
    assert model.ITI_thread is not original_timer
    assert model.ITI_active is True


def test_alternating_presenter_iti_licks_do_not_trigger_choice_or_reward(session_info, monkeypatch):
    """Queued ITI licks should not be converted into choices by presenter-run.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
      - `monkeypatch`: pytest fixture.
    - Output:
      - Asserts threshold-satisfying ITI licks leave no choice, command, or reward.
    """
    session_info["lick_threshold"] = 2
    model = make_alternating_model(session_info, state="left_patch")
    presenter, pump = make_alternating_presenter(model, session_info, monkeypatch)
    model.activate_ITI()
    event_time = time.time()
    model.event_list.append(make_event("left_entry", event_time))
    model.event_list.append(make_event("left_entry", event_time + 0.001))

    presenter.run()

    assert model.trial_choice_list == []
    assert list(model.presenter_commands) == []
    assert pump.rewards == []


def test_alternating_presenter_active_choice_path_still_rewards(session_info, monkeypatch):
    """Presenter-run should still deliver a reward for an eligible active choice.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
      - `monkeypatch`: pytest fixture.
    - Output:
      - Asserts a left-patch left lick logs a choice and delivers the left reward.
    """
    model = make_alternating_model(session_info, state="left_patch")
    model.rewards_available_in_block = 100
    presenter, pump = make_alternating_presenter(model, session_info, monkeypatch)
    model.event_list.append(make_event("left_entry"))

    presenter.run()

    assert model.trial_choice_list == [session_info["left_ix"]]
    assert model.trial_correct_list == [True]
    assert pump.rewards == [(session_info["left_reward_pump"], session_info["reward_size_large"])]


def test_alternating_latent_instances_do_not_share_event_or_trial_state(session_info):
    first_model = make_alternating_model(session_info, state="left_patch")
    second_model = make_alternating_model(session_info, state="left_patch")

    first_model.event_list.append(make_event("left_entry"))
    first_model.trial_choice_list.append(session_info["left_ix"])

    assert len(second_model.event_list) == 0
    assert second_model.trial_choice_list == []


def test_flush_drains_input_events_without_adding_choice_behavior(session_info):
    model = FlushModel(session_info=session_info)
    model.event_list.append(make_event("left_entry"))
    model.event_list.append(make_event("right_entry"))

    model.run_event_loop()

    assert len(model.event_list) == 0
    assert model.trial_choice_list == []
    assert list(model.presenter_commands) == []


def test_flush_instances_do_not_share_event_or_command_state(session_info):
    first_model = FlushModel(session_info=session_info)
    second_model = FlushModel(session_info=session_info)

    first_model.event_list.append(make_event("left_entry"))
    first_model.presenter_commands.append("toggle_pump1")

    assert len(second_model.event_list) == 0
    assert list(second_model.presenter_commands) == []
