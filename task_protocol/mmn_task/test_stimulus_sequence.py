"""Check sequence export and the fixed 22.5-degree grating ID convention."""

import csv

import pytest

from task_protocol.mmn_task.mmn_protocol import MMNConfig, StimulusEvent, build_schedule


@pytest.mark.parametrize('angle, grating_id', [
    (22.5, 1), (45, 2), (67.5, 3), (90, 4),
    (112.5, 5), (135, 6), (157.5, 7), (180, 8), (30, ''),
])
def test_grating_ids_are_fixed_by_angle(angle, grating_id):
    from task_protocol.mmn_task.stimulus_sequence import stimulus_row

    event = StimulusEvent(3, 1, 1, 'control', angle, None, 'control')
    row = stimulus_row(event, 100)
    assert row['stimulus_index'] == 100
    assert row['orientation_deg'] == angle
    assert row['grating_id'] == grating_id
    assert row['block_type'] == 'control'


def test_sequence_export_preserves_the_supplied_randomized_schedule(tmp_path):
    from task_protocol.mmn_task.stimulus_sequence import write_stimulus_sequence

    config = MMNConfig(
        block_count=3, block_order=('control', 'oddball_A', 'oddball_B'),
        trials_per_block=1, standard_count_options=(4,), control_trials_per_block=8,
    )
    schedule = build_schedule(config)  # No seed: exporter must use this exact order.
    path = tmp_path / 'sequence.csv'
    write_stimulus_sequence(path, schedule)
    with path.open() as output:
        rows = list(csv.DictReader(output))
    assert len(rows) == 24
    assert [int(row['stimulus_index']) for row in rows] == list(range(1, 25))
    assert [float(row['orientation_deg']) for row in rows] == [event.orientation_deg for event in schedule]
    assert [int(row['grating_id']) for row in rows] == [int(event.orientation_deg / 22.5) for event in schedule]
    assert [row['block_type'] for row in rows] == ['control'] * 8 + ['oddball_A'] * 8 + ['oddball_B'] * 8
    assert all(row['standards_before_deviant'] == '' for row in rows[:8])
    with pytest.raises(FileExistsError):
        write_stimulus_sequence(path, schedule)
