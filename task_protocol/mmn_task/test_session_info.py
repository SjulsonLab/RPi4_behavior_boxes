"""Verify editable session settings reach the MMN runner and saved metadata."""

import csv
import json
import sys
from types import SimpleNamespace

import pytest

from task_protocol.mmn_task import run_mmn_task as runner


def test_main_loads_session_file_and_applies_cli_overrides(monkeypatch, tmp_path):
    from session_info import make_session_info

    settings = make_session_info()
    settings.update(
        mouse_name="mouse-7",
        output_dir=str(tmp_path / "from-file"),
        block_count=2,
        block_order=("control", "oddball_A", "oddball_B"),
        trials_per_block=4,
        standard_count_options=(4,),
        grating_duration=0.3,
        inter_grating_interval=0.8,
        temporal_frequency_hz=1.0,
        spontaneous_duration_s=120.0,
    )
    captured = {}

    def run(config, output_dir, **kwargs):
        captured.update(config=config, output_dir=output_dir, **kwargs)
        return 0

    monkeypatch.setattr(runner, "make_session_info", lambda: settings)
    monkeypatch.setattr(runner, "run_protocol", run)
    monkeypatch.setattr(sys, "argv", ["mmn", "--seed", "42", "--output-dir", str(tmp_path)])
    assert runner.main() == 0
    config = captured["config"]
    assert config.block_count == 2
    assert config.block_types == ("control", "oddball_A")
    assert config.orientations_deg == (45, 135)
    assert config.stimulus_duration_s == 0.3
    assert config.inter_stimulus_interval_s == 0.8
    assert config.temporal_frequency_hz == 1.0
    assert config.spontaneous_duration_s == 120.0
    assert config.random_seed == 42
    assert captured["output_dir"].parent == tmp_path
    assert captured["output_dir"].name.startswith('mouse-7_')
    assert captured["session_info"]["mouse_name"] == "mouse-7"
    assert captured["session_info"]["visual_backend"] == "rpg"


@pytest.mark.parametrize("block_order", [
    ("oddball_A", "oddball_B", "control"),
    ("control", "oddball_A", "oddball_B"),
])
def test_windowed_cli_selects_pygame_and_short_trial(monkeypatch, tmp_path, block_order):
    from session_info import make_session_info

    captured = {}

    def run(config, output_dir, **kwargs):
        captured.update(config=config, **kwargs)
        return 0

    settings = make_session_info()
    settings['block_order'] = block_order
    monkeypatch.setattr(runner, "make_session_info", lambda: settings)
    monkeypatch.setattr(runner, "run_protocol", run)
    monkeypatch.setattr(sys, "argv", ["mmn", "--windowed", "--test-mode", "--output-dir", str(tmp_path)])
    assert runner.main() == 0
    assert captured["session_info"]["visual_backend"] == "pygame"
    assert captured["windowed"] is True
    assert captured["config"].block_count == 3
    assert captured["config"].block_types == block_order
    assert captured["config"].trials_per_block == 1
    assert captured["config"].standard_count_options == (4,)
    assert captured["config"].control_trials_per_block == 8
    assert captured["config"].spontaneous_duration_s == 5.0


def test_rpg_trial_logs_effective_settings_and_does_not_double_duration(monkeypatch, tmp_path):
    from session_info import make_session_info
    from task_protocol.mmn_task import rpg_stimulus
    from task_protocol.mmn_task.mmn_protocol import MMNConfig

    clock = SimpleNamespace(now=0.0)
    presented = []
    gray_times = []
    closed = []

    def sleep(seconds):
        clock.now += seconds

    class Screen:
        def __init__(self, **kwargs):
            pass

        def load_grating(self, filename):
            return filename

        def display_grating(self, grating):
            if 'mmn_gray_' in str(grating):
                gray_times.append(clock.now)
                return SimpleNamespace(start_time=int(clock.now))
            presented.append((grating, clock.now))
            clock.now += 0.5
            return SimpleNamespace(start_time=int(clock.now))

        def display_greyscale(self, level):
            gray_times.append(clock.now)

        def close(self):
            closed.append(True)

    def build(filename, options):
        from pathlib import Path
        Path(filename).write_bytes(b"grating")

    monkeypatch.setitem(sys.modules, "rpg", SimpleNamespace(Screen=Screen, build_grating=build, SINE=1))
    monkeypatch.setattr(rpg_stimulus, "write_rpg_grating", build)
    monkeypatch.setattr(rpg_stimulus, "write_rpg_gray", build)
    fake_time = SimpleNamespace(monotonic=lambda: clock.now, time=lambda: 1700000000 + clock.now, sleep=sleep)
    monkeypatch.setattr(runner, "time", fake_time)
    monkeypatch.setattr(rpg_stimulus, "time", fake_time)
    settings = make_session_info()
    settings.update(mouse_name="mouse-7", gratings_dir=str(tmp_path / "gratings"))
    config = MMNConfig(
        block_count=1, trials_per_block=1, standard_count_options=(4,),
        random_seed=3, spontaneous_duration_s=0.0,
    )
    assert runner.run_protocol(config, tmp_path, session_info=settings) == 0
    with next(tmp_path.glob("mmn_events_*.csv")).open() as output:
        rows = list(csv.DictReader(output))
    assert [int(row["orientation_deg"]) for row in rows] == [135] * 4 + [45] + [135] * 3
    assert all(row["status"] == "complete" for row in rows)
    assert all(float(row["actual_duration_s"]) == 0.5 for row in rows)
    assert [round(t, 3) for _, t in presented] == [round(1.2 * i, 3) for i in range(8)]
    metadata = json.loads(next(tmp_path.glob("mmn_metadata_*.json")).read_text())
    assert metadata["visual_backend"] == "rpg_precomputed_drifting_grating"
    assert metadata["session_info"]["mouse_name"] == "mouse-7"
    assert metadata["session_info"]["block_count"] == 1
    assert metadata["session_info"]["random_seed"] == 3
    assert metadata["spatial_frequency_cycles_per_degree"] == 0.2
    assert "spatial_frequency_cycles_per_cm" not in metadata
    assert metadata["display"]["photodiode_patch_enabled"] is True
    assert metadata["display"]["photodiode_rect_px"] == [0, 680, 80, 40]
    assert len(closed) == 1


def test_runner_executes_unequal_block_lengths_and_logs_control(monkeypatch, tmp_path):
    from session_info import make_session_info
    from task_protocol.mmn_task.mmn_protocol import MMNConfig, build_schedule

    clock = SimpleNamespace(now=0.0)
    starts = []

    def sleep(seconds):
        clock.now += seconds

    class Display:
        display_settings = {"photodiode_patch_enabled": False}

        def __init__(self, *args, **kwargs):
            pass

        def wait_until(self, deadline):
            clock.now = max(clock.now, deadline)
            return True

        def present_grating(self, angle):
            starts.append(clock.now)
            onset = clock.now
            clock.now += 0.5
            return onset

        def show_gray(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(runner, "RPGGratingDisplay", Display)
    monkeypatch.setattr(runner, "time", SimpleNamespace(
        monotonic=lambda: clock.now, time=lambda: 1700000000 + clock.now, sleep=sleep
    ))
    settings = make_session_info()
    config = MMNConfig(
        block_count=9, trials_per_block=1, standard_count_options=(4,),
        control_trials_per_block=16, inter_block_interval_s=2.0, random_seed=5,
    )
    assert runner.run_protocol(config, tmp_path, session_info=settings) == 0
    with next(tmp_path.glob("mmn_events_*.csv")).open() as output:
        rows = list(csv.DictReader(output))
    schedule = build_schedule(config)
    assert len(rows) == len(schedule) == 96
    assert [float(row["orientation_deg"]) for row in rows] == [event.orientation_deg for event in schedule]
    assert [row["block_type"] for row in rows] == [event.block_type for event in schedule]
    for row in rows:
        if row["block_type"] == "control":
            assert row["standards_before_deviant"] == ""
            assert row["sequence_position"] == "1"
        assert float(row["actual_duration_s"]) == 0.5
    boundaries = [i for i, event in enumerate(schedule) if i and event.block_number != schedule[i - 1].block_number]
    for i in boundaries:
        assert round(starts[i] - starts[i - 1], 6) == 3.2
    metadata = json.loads(next(tmp_path.glob("mmn_metadata_*.json")).read_text())
    assert metadata["block_order"] == ["oddball_A", "oddball_B", "control"] * 3
    assert metadata["control_trials_per_block"] == 16
    assert metadata["control_orientations_deg"] == [22.5, 45, 67.5, 90, 112.5, 135, 157.5, 180]


@pytest.fixture
def spontaneous_display(monkeypatch):
    """Simulate display time and interruptions without waiting for 15 real minutes."""
    clock = SimpleNamespace(now=0.0, interrupt=None)
    calls = []

    class Display:
        display_settings = {"gray_level": 40}

        def __init__(self, *args, **kwargs):
            # Device setup/preloading is outside the timed spontaneous period.
            clock.now += 30.0

        def show_gray(self):
            calls.append(("gray", clock.now))

        def wait_until(self, deadline):
            calls.append(("wait", clock.now, deadline))
            if clock.interrupt is not None:
                clock.now += 20.0
                if clock.interrupt == "keyboard":
                    raise KeyboardInterrupt
                return False
            clock.now = max(clock.now, deadline)
            return True

        def present_grating(self, angle):
            calls.append(("present", clock.now, angle))
            onset = clock.now
            clock.now += 0.5
            return onset

        def close(self):
            calls.append(("close", clock.now))

    monkeypatch.setattr(runner, "RPGGratingDisplay", Display)
    monkeypatch.setattr(runner, "time", SimpleNamespace(
        monotonic=lambda: clock.now, time=lambda: 1700000000 + clock.now,
    ))
    return clock, calls


@pytest.mark.parametrize("block_order", [
    ("oddball_A", "oddball_B", "control"),
    ("control", "oddball_A", "oddball_B"),
])
def test_spontaneous_gray_precedes_first_block_once_and_is_logged(spontaneous_display, tmp_path, block_order):
    from session_info import make_session_info
    from task_protocol.mmn_task.mmn_protocol import MMNConfig

    _, calls = spontaneous_display
    settings = make_session_info()
    settings['block_order'] = block_order
    assert settings["spontaneous_duration_s"] == 900.0
    assert runner._config_from_session_info(settings).spontaneous_duration_s == 900.0
    config = MMNConfig(
        block_count=3, block_order=block_order, trials_per_block=1, standard_count_options=(4,),
        control_trials_per_block=8, inter_block_interval_s=0.0,
    )
    assert runner.run_protocol(config, tmp_path, session_info=settings) == 0
    assert calls[0] == ("gray", 30.0)
    assert calls[1] == ("wait", 30.0, 930.0)
    starts = [call[1] for call in calls if call[0] == "present"]
    assert len(starts) == 24
    assert [round(start, 6) for start in starts] == [round(930 + 1.2 * i, 6) for i in range(24)]
    metadata = json.loads(next(tmp_path.glob("mmn_metadata_*.json")).read_text())
    phase = metadata["spontaneous"]
    assert metadata["spontaneous_duration_s"] == 900.0
    assert phase["status"] == "complete"
    assert phase["actual_onset_s"] == 0.0
    assert phase["actual_offset_s"] == 900.0
    assert phase["actual_duration_s"] == 900.0
    assert phase["onset_wall_time"] and phase["offset_wall_time"]
    assert metadata['block_order'] == list(block_order)
    assert metadata['session_info']['block_order'] == list(block_order)
    with next(tmp_path.glob("mmn_events_*.csv")).open() as output:
        rows = list(csv.DictReader(output))
    assert len(rows) == 24
    assert rows[0]['block_type'] == block_order[0]
    assert all(row['repetition'] == '1' for row in rows)
    assert float(rows[0]["actual_onset_s"]) == 0.0  # Still relative to the first block.
    assert calls[-1][0] == "close"


@pytest.mark.parametrize("interruption", ["display", "keyboard"])
def test_aborting_spontaneous_period_never_starts_gratings(spontaneous_display, tmp_path, interruption):
    from session_info import make_session_info
    from task_protocol.mmn_task.mmn_protocol import MMNConfig

    clock, calls = spontaneous_display
    clock.interrupt = interruption
    config = MMNConfig(block_count=1, trials_per_block=1, standard_count_options=(4,))
    assert runner.run_protocol(config, tmp_path, session_info=make_session_info()) == 130
    assert not any(call[0] == "present" for call in calls)
    assert calls[-1][0] == "close"
    metadata = json.loads(next(tmp_path.glob("mmn_metadata_*.json")).read_text())
    assert metadata["status"] == "aborted"
    assert metadata["spontaneous"]["status"] == "aborted"
    assert metadata["spontaneous"]["actual_duration_s"] == 20.0
    with next(tmp_path.glob("mmn_events_*.csv")).open() as output:
        assert list(csv.DictReader(output)) == []
    # The full planned sequence remains available if the session is stopped
    # during the spontaneous period, before any grating is actually shown.
    with next((tmp_path / 'task_output').glob('mmn_stimulus_sequence_*.csv')).open() as output:
        planned = list(csv.DictReader(output))
    assert len(planned) == 8


def test_zero_spontaneous_duration_starts_immediately(spontaneous_display, tmp_path):
    from session_info import make_session_info
    from task_protocol.mmn_task.mmn_protocol import MMNConfig

    _, calls = spontaneous_display
    config = MMNConfig(
        block_count=1, trials_per_block=1, standard_count_options=(4,),
        spontaneous_duration_s=0.0,
    )
    assert runner.run_protocol(config, tmp_path, session_info=make_session_info()) == 0
    assert next(call[1] for call in calls if call[0] == "present") == 30.0
    metadata = json.loads(next(tmp_path.glob("mmn_metadata_*.json")).read_text())
    assert metadata["spontaneous"]["status"] == "skipped"
    assert metadata["spontaneous"]["actual_duration_s"] == 0.0


@pytest.mark.parametrize('block_order', [
    ('oddball_A', 'oddball_B', 'control'),
    ('control', 'oddball_A', 'oddball_B'),
])
def test_full_sequence_is_saved_before_display_and_matches_presentations(
    spontaneous_display, tmp_path, monkeypatch, block_order
):
    from session_info import make_session_info
    from task_protocol.mmn_task.mmn_protocol import MMNConfig

    _, calls = spontaneous_display
    original_display = runner.RPGGratingDisplay
    saved_before_display = []

    def open_display(*args, **kwargs):
        sequence_path = next((tmp_path / 'task_output').glob('mmn_stimulus_sequence_*.csv'))
        with sequence_path.open() as output:
            saved_before_display.extend(csv.DictReader(output))
        assert len(saved_before_display) == 6528
        return original_display(*args, **kwargs)

    monkeypatch.setattr(runner, 'RPGGratingDisplay', open_display)
    config = MMNConfig(block_order=block_order)  # Unseeded, like a normal session.
    assert runner.run_protocol(config, tmp_path, session_info=make_session_info()) == 0
    presented_angles = [call[2] for call in calls if call[0] == 'present']
    assert [float(row['orientation_deg']) for row in saved_before_display] == presented_angles
    assert [int(row['stimulus_index']) for row in saved_before_display] == list(range(1, 6529))
    assert [int(row['grating_id']) for row in saved_before_display] == [int(angle / 22.5) for angle in presented_angles]
    assert saved_before_display[0]['block_type'] == block_order[0]
    with next(tmp_path.glob('mmn_events_*.csv')).open() as output:
        recorded = list(csv.DictReader(output))
    assert [row['stimulus_index'] for row in recorded] == [row['stimulus_index'] for row in saved_before_display]
    assert [row['grating_id'] for row in recorded] == [row['grating_id'] for row in saved_before_display]
    assert all(row['status'] == 'complete' for row in recorded)
    metadata = json.loads(next(tmp_path.glob('mmn_metadata_*.json')).read_text())
    sequence_path = next((tmp_path / 'task_output').glob('mmn_stimulus_sequence_*.csv'))
    assert metadata['stimulus_sequence_file'] == str(sequence_path)
    assert metadata['planned_stimulus_count'] == 6528
    assert metadata['grating_id_to_orientation_deg'] == {
        str(index): 22.5 * index for index in range(1, 9)
    }


@pytest.mark.parametrize('absolute_directory', [False, True])
def test_task_output_directory_can_be_configured(spontaneous_display, tmp_path, absolute_directory):
    from session_info import make_session_info
    from task_protocol.mmn_task.mmn_protocol import MMNConfig

    settings = make_session_info()
    destination = tmp_path / 'absolute_sequences' if absolute_directory else tmp_path / 'session' / 'sequences'
    settings['task_output_dir'] = str(destination) if absolute_directory else 'sequences'
    config = MMNConfig(
        block_count=1, trials_per_block=1, standard_count_options=(4,),
        spontaneous_duration_s=0.0,
    )
    assert runner.run_protocol(config, tmp_path / 'session', session_info=settings) == 0
    assert len(list(destination.glob('mmn_stimulus_sequence_*.csv'))) == 1


@pytest.mark.parametrize('mode', ['complete', 'interrupt', 'start_failure', 'stop_failure'])
def test_recording_lifecycle_surrounds_spontaneous_and_always_stops(
    spontaneous_display, monkeypatch, tmp_path, mode
):
    from session_info import make_session_info
    from task_protocol.mmn_task.mmn_protocol import MMNConfig

    clock, calls = spontaneous_display
    if mode == 'interrupt':
        clock.interrupt = 'keyboard'

    class Recorders:
        workers = []

        def __init__(self, settings, directory):
            self.report = {'stopped': False}

        def start(self):
            calls.append(('recording_start', clock.now))
            if mode == 'start_failure':
                raise RuntimeError('camera startup failed')

        def check_health(self):
            pass

        def stop(self):
            calls.append(('recording_stop', clock.now))
            self.report['stopped'] = True
            return ['camera transfer failed'] if mode == 'stop_failure' else []

    monkeypatch.setattr(runner, 'SessionAcquisition', Recorders)
    config = MMNConfig(block_count=1, trials_per_block=1, standard_count_options=(4,))
    result = runner.run_protocol(config, tmp_path, session_info=make_session_info())
    assert result == {'complete': 0, 'interrupt': 130, 'start_failure': 1, 'stop_failure': 1}[mode]
    assert calls[0][0] == 'recording_start'
    assert calls[-2][0] == 'recording_stop'
    assert calls[-1][0] == 'close'
    assert len([call for call in calls if call[0] == 'recording_stop']) == 1
    if mode in ('interrupt', 'start_failure'):
        assert not any(call[0] == 'present' for call in calls)
    metadata = json.loads(next(tmp_path.glob('mmn_metadata_*.json')).read_text())
    assert metadata['acquisition']['stopped'] is True
    assert metadata['status'] == {'complete': 'complete', 'interrupt': 'aborted', 'start_failure': 'failed', 'stop_failure': 'failed'}[mode]


def test_recording_failure_after_grating_still_logs_presented_stimulus(
    spontaneous_display, monkeypatch, tmp_path
):
    from session_info import make_session_info
    from task_protocol.mmn_task.mmn_protocol import MMNConfig

    _, calls = spontaneous_display

    class Recorders:
        workers = [object()]

        def __init__(self, settings, directory):
            self.report = {}

        def start(self):
            pass

        def check_health(self):
            if any(call[0] == 'present' for call in calls):
                raise RuntimeError('camera exited during stimulus')

        def stop(self):
            return []

    monkeypatch.setattr(runner, 'SessionAcquisition', Recorders)
    config = MMNConfig(
        block_count=1, trials_per_block=1, standard_count_options=(4,), spontaneous_duration_s=0,
    )
    assert runner.run_protocol(config, tmp_path, session_info=make_session_info()) == 1
    with next(tmp_path.glob('mmn_events_*.csv')).open() as output:
        rows = list(csv.DictReader(output))
    assert len(rows) == 1
    assert rows[0]['status'] == 'failed_during_stimulus'
    assert float(rows[0]['actual_duration_s']) == 0.5
    assert rows[0]['onset_wall_time']
    assert calls[-1][0] == 'close'


def test_no_recording_cli_overrides_enabled_settings(monkeypatch, tmp_path):
    from session_info import make_session_info

    settings = make_session_info()
    settings.update(camera_enabled=True, treadmill=True)
    captured = {}

    def run(config, output_dir, **kwargs):
        captured.update(kwargs['session_info'])
        return 0

    monkeypatch.setattr(runner, 'make_session_info', lambda: settings)
    monkeypatch.setattr(runner, 'run_protocol', run)
    monkeypatch.setattr(sys, 'argv', ['main.py', '--test-mode', '--no-recording', '--output-dir', str(tmp_path)])
    assert runner.main() == 0
    assert captured['camera_enabled'] is False
    assert captured['treadmill'] is False
