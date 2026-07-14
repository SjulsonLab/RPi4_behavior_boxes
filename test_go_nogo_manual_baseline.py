import collections
import logging

from go_nogo_manual_baseline import (
    _log_due_baseline_minute_markers,
    format_elapsed_seconds,
    print_baseline_timer,
    run_countup_baseline,
)


class FakeClock:
    """Deterministic clock for baseline timer tests."""

    def __init__(self, start_time, stop_after_sleeps):
        self.now = float(start_time)
        self.sleep_count = 0
        self.stop_after_sleeps = stop_after_sleeps

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += 2.0
        self.sleep_count += 1
        if self.sleep_count >= self.stop_after_sleeps:
            raise KeyboardInterrupt


class FakeBox:
    """Minimal behavior-box stand-in with event queue and frame flushing."""

    def __init__(self):
        self.event_list = collections.deque(["left_entry", "ignored_event"])
        self.flush_count = 0

    def flush_frame_events(self):
        self.flush_count += 1


class FakeTask:
    """Minimal go/no-go task stand-in used by baseline helper tests."""

    def __init__(self):
        self.box = FakeBox()
        self.trial_running = True
        self.cues_stopped = False

    def emergency_stop_all_cues(self):
        self.trial_running = False
        self.cues_stopped = True


def test_format_elapsed_seconds_uses_minute_second_text():
    assert format_elapsed_seconds(0) == "0 sec"
    assert format_elapsed_seconds(62) == "1 min 2 sec"
    assert format_elapsed_seconds(3665) == "1 hr 1 min 5 sec"


def test_print_baseline_timer_writes_one_message():
    printed_messages = []

    print_baseline_timer(64, print_fn=printed_messages.append)

    assert printed_messages == [
        "Baseline elapsed: 1 min 4 sec | Ctrl+C to end baseline"
    ]


def test_log_due_baseline_minute_markers_logs_each_due_marker(caplog):
    caplog.set_level(logging.INFO)

    next_marker = _log_due_baseline_minute_markers(
        elapsed_seconds=125.0,
        next_minute_marker=1,
        baseline_start_time=1000.0,
    )

    assert next_marker == 3
    assert "1060.0, baseline_elapsed_minute_1" in caplog.text
    assert "1120.0, baseline_elapsed_minute_2" in caplog.text


def test_run_countup_baseline_returns_manual_metadata_and_two_second_prints(caplog):
    caplog.set_level(logging.INFO)
    clock = FakeClock(start_time=1000.0, stop_after_sleeps=3)
    task = FakeTask()
    printed_messages = []

    metadata = run_countup_baseline(
        task,
        time_fn=clock.time,
        sleep_fn=clock.sleep,
        print_fn=printed_messages.append,
        status_interval_seconds=2.0,
    )

    assert task.cues_stopped is True
    assert task.trial_running is False
    assert task.box.flush_count >= 1
    assert metadata["baseline_manual"] is True
    assert metadata["baseline_req_dur_s"] == -1.0
    assert metadata["baseline_stop_reason"] == "manual_ctrl_c"
    assert metadata["baseline_actual_dur_s"] == 6.0
    assert metadata["baseline_lick_times"] == [0.0]
    assert "Baseline elapsed: 2 sec | Ctrl+C to end baseline" in printed_messages
    assert "1000.0, baseline_start" in caplog.text
    assert "baseline_elapsed, 2 sec, 2.000 s" in caplog.text
    assert "baseline_note, ignore any late task timer messages after baseline_start" in caplog.text
    assert "1006.0, baseline_manual_stop" in caplog.text
    assert "1006.0, baseline_end" in caplog.text
    assert "1006.0, baseline_actual_duration, 6 sec, 6.000 s" in caplog.text
