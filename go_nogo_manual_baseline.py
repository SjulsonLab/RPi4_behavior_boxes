"""Manual count-up baseline helpers for go/no-go behavior sessions."""

import logging
import time


BASELINE_LOOP_SLEEP_SECONDS = 0.01
BASELINE_STATUS_INTERVAL_SECONDS = 2.0
BASELINE_MINUTE_MARK_INTERVAL_SECONDS = 60.0
BASELINE_LICK_EVENTS = {"left_entry", "center_entry", "right_entry"}


def flush_logging_handlers():
    """Flush all active root logging handlers.

    Inputs
    ------
    None

    Returns
    -------
    None
        Flushes handlers in-place. Any handler-specific flush errors are
        ignored so logging cleanup cannot interrupt the behavior session.
    """
    for handler in logging.getLogger().handlers:
        try:
            handler.flush()
        except Exception:
            pass


def configure_session_logging(log_file_path):
    """Configure one root logger for the current behavior session.

    Inputs
    ------
    log_file_path : str
        Absolute or relative path to the session ``.log`` file.

    Returns
    -------
    str
        The same log-file path, returned for convenient storage in
        ``session_info``. No array shape or physical unit conventions apply.
    """
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
        datefmt="%H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    return log_file_path


def log_session_event(event_name, event_time=None, session_info=None):
    """Log one timestamped session transition marker.

    Inputs
    ------
    event_name : str
        Human-readable event marker name, such as ``baseline_start``.
    event_time : float or None, optional
        Absolute UNIX timestamp in seconds. If None, ``time.time()`` is used.
    session_info : dict or None, optional
        Accepted for compatibility with older launcher code. This helper does
        not mutate it and does not create sidecar files.

    Returns
    -------
    float
        Absolute UNIX timestamp in seconds used for the marker.
    """
    if event_time is None:
        event_time = time.time()

    logging.info(str(event_time) + ", " + event_name)
    flush_logging_handlers()
    return event_time


def _call_noarg_if_present(owner, attribute_name):
    """Call a no-argument method when it exists.

    Inputs
    ------
    owner : object
        Object that may contain the named attribute. No shape or unit
        conventions apply.
    attribute_name : str
        Name of a no-argument method that should be called if present.

    Returns
    -------
    bool
        True when the attribute existed and was callable, False otherwise.
    """
    method = getattr(owner, attribute_name, None)
    if not callable(method):
        return False
    try:
        method()
    except Exception as exc:
        logging.warning(
            str(time.time()) + ", baseline cleanup warning: " + attribute_name + " failed: " + str(exc)
        )
    return True


def clear_behavior_cues_for_baseline(task):
    """Stop behavioral cues while keeping session acquisition open.

    Inputs
    ------
    task : object
        Active go/no-go task object. It should expose ``trial_running`` and may
        expose ``emergency_stop_all_cues`` or a ``box`` with sound and visual
        stimulus attributes. No array shape conventions apply.

    Returns
    -------
    None
        The function modifies hardware state in-place. It does not stop video,
        treadmill logging, frame-sync logging, or the behavior-box session.
    """
    task.trial_running = False

    emergency_stop = getattr(task, "emergency_stop_all_cues", None)
    if callable(emergency_stop):
        try:
            emergency_stop()
            return
        except Exception as exc:
            logging.warning(str(time.time()) + ", emergency cue stop failed: " + str(exc))

    box = getattr(task, "box", None)
    if box is None:
        return

    for sound_name in ("sound1", "sound2"):
        sound = getattr(box, sound_name, None)
        if sound is not None:
            _call_noarg_if_present(sound, "off")

    closed_screen_ids = set()
    for visualstim_name in ("visualstim_go", "visualstim_nogo"):
        visualstim = getattr(box, visualstim_name, None)
        screen = getattr(visualstim, "myscreen", None)
        if screen is None:
            continue
        screen_id = id(screen)
        if screen_id in closed_screen_ids:
            continue
        closed_screen_ids.add(screen_id)
        _call_noarg_if_present(screen, "close")


def drain_baseline_events(task, baseline_start_time, baseline_lick_times, time_fn=time.time):
    """Drain behavior-box events during baseline and record lick times.

    Inputs
    ------
    task : object
        Active task object with ``task.box.event_list`` as a deque-like queue.
    baseline_start_time : float
        Absolute UNIX timestamp in seconds marking baseline start.
    baseline_lick_times : list[float]
        Mutable list updated in-place with lick timestamps, in seconds relative
        to ``baseline_start_time``.
    time_fn : callable, optional
        Function returning current absolute UNIX time in seconds. Defaults to
        ``time.time``; injectable for tests.

    Returns
    -------
    list[str]
        Event names drained from the behavior-box event queue during this call.
    """
    drained_events = []
    event_queue = getattr(getattr(task, "box", None), "event_list", None)
    if event_queue is None:
        return drained_events

    while event_queue:
        event_name = event_queue.popleft()
        drained_events.append(event_name)
        if event_name in BASELINE_LICK_EVENTS:
            baseline_lick_times.append(time_fn() - baseline_start_time)
    return drained_events


def format_elapsed_seconds(seconds):
    """Format elapsed seconds as compact human-readable text.

    Inputs
    ------
    seconds : float
        Elapsed time in seconds. Negative values are clamped to zero.

    Returns
    -------
    str
        Elapsed time text such as ``1 min 2 sec``. Units are seconds, minutes,
        and hours.
    """
    total_seconds = int(max(0.0, float(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if hours:
        hour_unit = "hr" if hours == 1 else "hrs"
        parts.append(str(hours) + " " + hour_unit)
    if minutes:
        parts.append(str(minutes) + " min")
    if secs or not parts:
        parts.append(str(secs) + " sec")
    return " ".join(parts)


def print_baseline_timer(elapsed_seconds, print_fn=print):
    """Print the current manual baseline timer.

    Inputs
    ------
    elapsed_seconds : float
        Elapsed baseline time in seconds.
    print_fn : callable, optional
        Print-like function used for output. It must accept one string
        argument. Defaults to ``print``.

    Returns
    -------
    None
        Writes one timer message to stdout.
    """
    elapsed_text = format_elapsed_seconds(elapsed_seconds)
    print_fn("Baseline elapsed: " + elapsed_text + " | Ctrl+C to end baseline")


def _log_due_baseline_minute_markers(
    elapsed_seconds,
    next_minute_marker,
    baseline_start_time,
    session_info=None,
):
    """Write elapsed-minute baseline markers that are due.

    Inputs
    ------
    elapsed_seconds : float
        Elapsed baseline time in seconds.
    next_minute_marker : int
        Next 1-based elapsed minute marker to write.
    baseline_start_time : float
        Absolute UNIX timestamp in seconds marking baseline start.
    session_info : dict or None, optional
        Accepted for compatibility. It is not mutated.

    Returns
    -------
    int
        The next 1-based elapsed minute marker that remains unwritten.
    """
    while elapsed_seconds >= next_minute_marker * BASELINE_MINUTE_MARK_INTERVAL_SECONDS:
        event_time = baseline_start_time + next_minute_marker * BASELINE_MINUTE_MARK_INTERVAL_SECONDS
        log_session_event(
            "baseline_elapsed_minute_" + str(next_minute_marker),
            event_time,
            session_info,
        )
        next_minute_marker += 1
    return next_minute_marker


def _flush_frame_events(task, event_time):
    """Flush frame events from a task's behavior box when available.

    Inputs
    ------
    task : object
        Active task object that may expose ``task.box.flush_frame_events``.
    event_time : float
        Absolute UNIX timestamp in seconds used for warning logs.

    Returns
    -------
    None
        Calls the hardware flush method for side effects only.
    """
    flush_method = getattr(getattr(task, "box", None), "flush_frame_events", None)
    if not callable(flush_method):
        return
    try:
        flush_method()
    except Exception as exc:
        logging.warning(str(event_time) + ", baseline frame flush warning: " + str(exc))


def run_countup_baseline(
    task,
    time_fn=time.time,
    sleep_fn=time.sleep,
    session_info=None,
    print_fn=print,
    status_interval_seconds=BASELINE_STATUS_INTERVAL_SECONDS,
):
    """Run a manual no-cue baseline period inside the open behavior session.

    Inputs
    ------
    task : object
        Active task object whose session/video/treadmill acquisition should
        remain open during baseline. The object is expected to expose a ``box``
        attribute with optional ``event_list`` and ``flush_frame_events``.
    time_fn : callable, optional
        Function returning current absolute UNIX time in seconds. Defaults to
        ``time.time``; injectable for tests.
    sleep_fn : callable, optional
        Function accepting sleep duration in seconds. Defaults to
        ``time.sleep``; injectable for tests.
    session_info : dict or None, optional
        Session metadata dictionary accepted for compatibility. It is not
        mutated by this helper.
    print_fn : callable, optional
        Function used for timer/status messages. Defaults to ``print`` and is
        injectable for tests.
    status_interval_seconds : float, optional
        Minimum elapsed-time interval between timer status prints, in seconds.

    Returns
    -------
    dict
        Baseline metadata with UNIX start/end times, manual-mode fields, actual
        duration in seconds/minutes, stop reason, and lick times in seconds
        relative to baseline start. All keys are 31 characters or shorter so
        MATLAB ``savemat`` can store them as struct fields.
    """
    clear_behavior_cues_for_baseline(task)

    baseline_start_time = time_fn()
    baseline_lick_times = []
    next_minute_marker = 1
    next_status_elapsed = 0.0
    status_interval_seconds = max(0.1, float(status_interval_seconds))

    log_session_event("baseline_start", baseline_start_time, session_info)
    logging.info(str(baseline_start_time) + ", baseline_target, manual count-up")
    flush_logging_handlers()

    print_fn("Starting baseline count-up timer. Press Ctrl+C to end baseline.")

    try:
        while True:
            current_time = time_fn()
            elapsed_seconds = max(0.0, current_time - baseline_start_time)
            if elapsed_seconds >= next_status_elapsed:
                print_baseline_timer(elapsed_seconds, print_fn=print_fn)
                next_status_elapsed += status_interval_seconds

            next_minute_marker = _log_due_baseline_minute_markers(
                elapsed_seconds,
                next_minute_marker,
                baseline_start_time,
                session_info=session_info,
            )
            drain_baseline_events(task, baseline_start_time, baseline_lick_times, time_fn=time_fn)
            _flush_frame_events(task, time_fn())
            sleep_fn(BASELINE_LOOP_SLEEP_SECONDS)
    except KeyboardInterrupt:
        manual_stop_time = time_fn()
        elapsed_seconds = max(0.0, manual_stop_time - baseline_start_time)
        _log_due_baseline_minute_markers(
            elapsed_seconds,
            next_minute_marker,
            baseline_start_time,
            session_info=session_info,
        )
        log_session_event("baseline_manual_stop", manual_stop_time, session_info)
        print_fn("Baseline stopped by user. Exiting cleanly.")

    baseline_end_time = time_fn()
    drain_baseline_events(task, baseline_start_time, baseline_lick_times, time_fn=time_fn)
    _flush_frame_events(task, baseline_end_time)

    log_session_event("baseline_completed_manual", baseline_end_time, session_info)
    log_session_event("baseline_end", baseline_end_time, session_info)

    actual_duration = float(baseline_end_time - baseline_start_time)
    return {
        "baseline_requested": True,
        "baseline_req_dur_s": -1.0,
        "baseline_req_dur_min": -1.0,
        "baseline_manual": True,
        "baseline_start_unix": float(baseline_start_time),
        "baseline_end_unix": float(baseline_end_time),
        "baseline_actual_dur_s": actual_duration,
        "baseline_actual_dur_min": float(actual_duration / 60.0),
        "baseline_completed": True,
        "baseline_interrupted": False,
        "baseline_stop_reason": "manual_ctrl_c",
        "baseline_lick_times": baseline_lick_times,
    }


def run_timed_baseline(*args, **kwargs):
    """Backward-compatible wrapper for the manual count-up baseline.

    Inputs
    ------
    *args : tuple
        Positional arguments forwarded to ``run_countup_baseline``.
    **kwargs : dict
        Keyword arguments forwarded to ``run_countup_baseline``. The deprecated
        ``duration_seconds`` keyword is ignored when present so older launchers
        still use manual count-up behavior.

    Returns
    -------
    dict
        Metadata returned by ``run_countup_baseline``.
    """
    kwargs.pop("duration_seconds", None)
    return run_countup_baseline(*args, **kwargs)
