"""Threshold choices must not depend on how the event queue is batched."""

import logging
import random
import time

import numpy as np
import pytest

from test_latent_inference_lick_processing import (
    FakeTimer, fake_timer, make_event, session_info,
)
from task_protocol.latent_inference_forage.latent_inference_model import LatentInferenceModel


@pytest.fixture
def threshold_task(session_info):
    """Return a left-patch task with timestamped inputs in epoch seconds; no hardware."""
    session_info["errors_to_reward_delivery"] = 5
    random.seed(12345)
    task = LatentInferenceModel(session_info)
    task.switch_to_left_patch()
    task.open_choice_window()
    task.presenter_commands.clear()
    return task


@pytest.mark.parametrize("threshold,sides,expected", [
    (1, ["left", "right"], "left"),
    (1, ["right", "left"], "right"),
    (2, ["left", "right"], "switch"),
    (2, ["right", "left"], "switch"),
    (2, ["left", "left", "right"], "left"),
    (2, ["right", "right", "left"], "right"),
    (3, ["left", "left", "right"], "switch"),
])
@pytest.mark.parametrize("split_batches", [False, True])
def test_threshold_outcome_independent_of_batching(threshold_task, threshold, sides, expected,
                                                  split_batches, caplog):
    """Ordered side strings produce the same terminal choice with any queue batching."""
    task = threshold_task
    task.lick_threshold = threshold
    task.session_info["quiet_ITI"] = False
    started = time.time()
    with caplog.at_level(logging.INFO):
        for index, side in enumerate(sides):
            task.event_list.append(make_event(side + "_entry", started + index * 0.001))
            if split_batches:
                task.run_event_loop()
        if not split_batches:
            task.run_event_loop()
        task.run_event_loop()  # Drain any input left after the terminal event during ITI.
    messages = [record.message for record in caplog.records]
    assert sum(";trial_stop;" in message for message in messages) == 1
    assert len(FakeTimer.instances) == 1
    assert not task.event_list
    if expected == "switch":
        assert task.trial_choice_list == task.trial_reward_given == []
        assert task.correct_trials_in_block == task.error_count == task.rewards_earned_in_block == 0
        assert not any("give_" in command for command in task.presenter_commands)
        assert sum(";invalid_switch;reason_both_ports" in message for message in messages) == 1
    else:
        assert task.trial_choice_list == [1 if expected == "left" else 0]
        assert not any(";invalid_switch;" in message for message in messages)


def test_debounced_threshold_uses_completed_licks(threshold_task, caplog):
    """Epoch-second entry/exit pairs qualify by duration before counting side activity."""
    task = threshold_task
    task.lick_threshold = 2
    task.session_info["debounce_licks"] = True
    start = time.time()
    for name, delay in [("left_entry", 0), ("left_exit", .1),
                        ("right_entry", .2), ("right_exit", .3)]:
        task.event_list.append(make_event(name, start + delay))
    with caplog.at_level(logging.INFO):
        task.run_event_loop()
    assert task.trial_choice_list == []
    assert any(";invalid_switch;" in record.message for record in caplog.records)


def test_switch_reset_does_not_contaminate_next_trial(threshold_task):
    """Invalid counts and pending ITI events cannot carry into the next open window."""
    task = threshold_task
    task.lick_threshold = 2
    stamp = time.time()
    for side in ("left", "right", "left"):
        task.event_list.append(make_event(side + "_entry", stamp))
    task.run_event_loop()
    task.run_event_loop()
    task.end_ITI()
    stamp = time.time()
    for _ in range(2):
        task.event_list.append(make_event("right_entry", stamp))
    task.run_event_loop()
    assert task.trial_choice_list == [0]


def test_rule_version_logged_when_task_starts(threshold_task, caplog):
    """A session-start log identifies the threshold rule without changing parameters."""
    threshold_task.switch_to_standby()
    with caplog.at_level(logging.INFO):
        threshold_task.start_task()
    assert any("threshold_ordered_v1" in record.message for record in caplog.records)
