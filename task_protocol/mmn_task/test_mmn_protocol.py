"""Check oddball/control ordering, balanced randomization, and trial identities."""

from collections import Counter, defaultdict

import pytest

from task_protocol.mmn_task.mmn_protocol import MMNConfig, build_schedule


CONTROL_ANGLES = (22.5, 45, 67.5, 90, 112.5, 135, 157.5, 180)


def test_default_schedule_repeats_oddball_a_b_control_three_times():
    config = MMNConfig(random_seed=10)
    schedule = build_schedule(config)
    assert config.block_count == 9
    assert len(schedule) == 6 * 96 * 8 + 3 * 640
    by_block = defaultdict(list)
    for event in schedule:
        by_block[event.block_number].append(event)
    assert list(by_block) == list(range(1, 10))
    assert [events[0].block_type for events in by_block.values()] == [
        "oddball_A", "oddball_B", "control"
    ] * 3

    for events in by_block.values():
        if events[0].block_type == "control":
            assert len(events) == 640
            assert Counter(event.orientation_deg for event in events) == Counter(
                {angle: 80 for angle in CONTROL_ANGLES}
            )
            assert [event.trial_number for event in events] == list(range(1, 641))
            assert all(event.sequence_position == 1 for event in events)
            assert all(event.stimulus_type == "control" for event in events)
            assert all(event.standards_before_deviant is None for event in events)
            continue

        assert len(events) == 96 * 8
        by_trial = defaultdict(list)
        for event in events:
            by_trial[event.trial_number].append(event)
        assert Counter(trial[0].standards_before_deviant for trial in by_trial.values()) == Counter(
            {4: 24, 5: 24, 6: 24, 7: 24}
        )
        standard, deviant = (135, 45) if events[0].block_type == "oddball_A" else (45, 135)
        for trial in by_trial.values():
            assert len(trial) == 8
            deviants = [event for event in trial if event.stimulus_type == "deviant"]
            assert len(deviants) == 1
            assert deviants[0].orientation_deg == deviant
            assert deviants[0].sequence_position == deviants[0].standards_before_deviant + 1
            assert all(event.orientation_deg == standard for event in trial if event.stimulus_type == "standard")


def test_seed_reproduces_control_order_and_each_repeat_is_shuffled():
    config = MMNConfig(random_seed=42)
    schedule = build_schedule(config)
    assert schedule == build_schedule(config)
    controls = [
        [event.orientation_deg for event in schedule if event.block_number == block]
        for block in (3, 6, 9)
    ]
    assert all(angles != sorted(angles) for angles in controls)
    assert controls[0] != controls[1] != controls[2]
    different_seed = build_schedule(MMNConfig(random_seed=43))
    assert controls[0] != [event.orientation_deg for event in different_seed if event.block_number == 3]


@pytest.mark.parametrize("block_order", [
    ("oddball_A", "oddball_B", "control"),
    ("control", "oddball_A", "oddball_B"),
])
def test_selected_order_repeats_without_changing_block_identities(block_order):
    config = MMNConfig(block_order=block_order, random_seed=42)
    schedule = build_schedule(config)
    by_block = defaultdict(list)
    for event in schedule:
        by_block[event.block_number].append(event)
    assert config.block_types == block_order * 3
    assert [events[0].block_type for events in by_block.values()] == list(block_order) * 3
    assert len(schedule) == 6528
    for events in by_block.values():
        block_type = events[0].block_type
        if block_type == "control":
            assert len(events) == 640
            assert Counter(event.orientation_deg for event in events) == Counter(
                {angle: 80 for angle in CONTROL_ANGLES}
            )
        else:
            standard, deviant = (135, 45) if block_type == "oddball_A" else (45, 135)
            assert len(events) == 96 * 8
            assert {event.orientation_deg for event in events if event.stimulus_type == "standard"} == {standard}
            assert Counter(event.orientation_deg for event in events if event.stimulus_type == "deviant") == {deviant: 96}


@pytest.mark.parametrize("settings", [
    {"trials_per_block": 95},
    {"control_trials_per_block": 639},
    {"control_trials_per_block": 0},
    {"control_orientations_deg": ()},
    {"control_orientations_deg": (45, 45)},
    {"control_orientations_deg": (45, float("nan"))},
    {"spontaneous_duration_s": -1.0},
    {"spontaneous_duration_s": float("inf")},
    {"spontaneous_duration_s": float("nan")},
    {"block_order": ()},
    {"block_order": ("oddball_A", "oddball_A", "control")},
    {"block_order": ("oddball_A", "control", "oddball_B")},
    {"block_order": "control_first"},
])
def test_rejects_invalid_block_settings(settings):
    with pytest.raises(ValueError):
        MMNConfig(**settings)


def test_single_oddball_block_does_not_require_control_gratings():
    config = MMNConfig(block_count=1, trials_per_block=1, standard_count_options=(4,))
    assert len(build_schedule(config)) == 8
    assert config.grating_orientations_deg == (45, 135)
