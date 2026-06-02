import importlib
import sys
import types
from collections import deque

import numpy as np
import pytest

pygame_stub = types.SimpleNamespace(
    event=types.SimpleNamespace(get=lambda: []),
    KEYDOWN=1,
    KEYUP=2,
    K_ESCAPE=27,
)
sys.modules.setdefault("pygame", pygame_stub)
sys.modules.setdefault("icecream", types.SimpleNamespace(ic=lambda *args, **kwargs: args[0] if args else None))

from essential.base_classes import Box, Model
from task_protocol.alternating_latent.alternating_latent_model import AlternatingLatentModel
from task_protocol.flush.flush_model import FlushModel
from task_protocol.latent_inference_forage.latent_inference_model import LatentInferenceModel


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
    """Return minimal active-model settings.

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
    }


@pytest.mark.parametrize(
    "attribute_name",
    [
        "event_list",
        "trial_choice_list",
        "trial_correct_list",
        "trial_choice_times",
        "trial_reward_given",
        "lick_side_buffer",
        "lick_entry_buffer",
        "lick_exit_buffer",
        "presenter_commands",
    ],
)
def test_model_does_not_define_mutable_class_defaults(attribute_name):
    """Base `Model` should not expose shared mutable defaults.

    Data contract:
    - Inputs:
      - `attribute_name`: str name of a queue, list, or NumPy buffer attribute.
    - Output:
      - Asserts the mutable attribute is not present in `Model.__dict__`.
    """
    assert attribute_name not in Model.__dict__


def test_box_does_not_define_mutable_presenter_command_default():
    """Base `Box` should not expose a shared presenter-command list.

    Data contract:
    - Inputs: none.
    - Output:
      - Asserts `presenter_commands` is not present in `Box.__dict__`.
    """
    assert "presenter_commands" not in Box.__dict__


@pytest.mark.parametrize(
    "model_class",
    [
        LatentInferenceModel,
        AlternatingLatentModel,
        FlushModel,
    ],
)
def test_active_models_initialize_instance_queues_and_buffers(session_info, model_class):
    """Active models should keep owning per-instance mutable state.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
      - `model_class`: task model class.
    - Output:
      - Asserts queues, logs, and lick buffers are instance attributes with expected types.
    """
    model = model_class(session_info)

    assert isinstance(model.event_list, deque)
    assert isinstance(model.presenter_commands, deque)
    assert isinstance(model.trial_choice_list, list)
    assert isinstance(model.trial_correct_list, list)
    assert isinstance(model.trial_choice_times, list)
    assert isinstance(model.trial_reward_given, list)
    assert isinstance(model.lick_side_buffer, np.ndarray)
    assert isinstance(model.lick_entry_buffer, np.ndarray)
    assert isinstance(model.lick_exit_buffer, np.ndarray)


@pytest.mark.parametrize(
    "model_class",
    [
        LatentInferenceModel,
        AlternatingLatentModel,
        FlushModel,
    ],
)
def test_active_model_instances_do_not_share_mutable_state(session_info, model_class):
    """Active model instances should not share queues, logs, or lick buffers.

    Data contract:
    - Inputs:
      - `session_info`: dict fixture.
      - `model_class`: task model class.
    - Output:
      - Asserts mutating one instance does not mutate another.
    """
    first_model = model_class(session_info)
    second_model = model_class(session_info)

    first_model.event_list.append("left_entry")
    first_model.presenter_commands.append("turn_LED_on")
    first_model.trial_choice_list.append(1)
    first_model.lick_side_buffer[0] = 1

    assert len(second_model.event_list) == 0
    assert len(second_model.presenter_commands) == 0
    assert second_model.trial_choice_list == []
    assert second_model.lick_side_buffer[0] == 0
