debug_enable = False

TRANSITION_FILE_VERSION = "transition_day_baseline_2026_07_09"
print("RUNNING transition-day baseline file: " + TRANSITION_FILE_VERSION)

from icecream import ic
from datetime import datetime
import os
import sys
import logging.config
import importlib
import scipy.io, pickle
import pygame
from colorama import Fore, Style
import time
import random
from scipy.stats import norm

# import packages for starting a new process and plotting trial progress in real time
# RPi4 does not have a graphical interface, we use pygame with backends for plotting
import matplotlib
matplotlib.use("Agg")
import matplotlib.backends.backend_agg as agg
import matplotlib.pyplot as plt
import pygame
from pygame.locals import *
import numpy as np
from multiprocessing import Process, Value

# all modules above this line will have logging disabled
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
})

if debug_enable:
    # enabling debugger
    from IPython import get_ipython
    ipython = get_ipython()
    ipython.magic("pdb on")
    ipython.magic("xmode Verbose")

# Start with the first-rule task object. The transition-day task reverses the
# cue objects in-place when first-rule criterion is reached, so the behavior
# box, video object, and session object stay open across the phase boundary.
from go_nogo_firstrule_2p import go_nogo_firstrule
import go_nogo_manual_baseline as manual_baseline

FIRST_RULE_PHASE = "first_rule"
REVERSAL_PHASE = "reversal"

MAX_FIRST_RULE_TRIALS = 500
MAX_REVERSAL_TRIALS = 500
TOTAL_MAX_TRIALS = MAX_FIRST_RULE_TRIALS + MAX_REVERSAL_TRIALS

DPRIME_BINSIZE = 30
DPRIME_THRESHOLD = 2.5
DPRIME_MIN_CONSECUTIVE = 30
DPRIME_IGNORE_FIRST = 30

LICK_DISENGAGE_THRESHOLD = 2
LICK_DISENGAGE_MIN_CONSECUTIVE = 100


def check_consecutive_dprime(dprime_values, threshold=2.5, min_consecutive=30, ignore_first=30):
    """Check for consecutive trials above the d-prime learning threshold.

    Inputs
    ------
    dprime_values : sequence of float, shape (n_trials,)
        Per-trial d-prime values. Values may include ``numpy.nan`` for trials
        that have not been run; non-finite values are treated as not meeting
        criterion.
    threshold : float, unitless
        Criterion d-prime threshold. Default is 2.5.
    min_consecutive : int, trials
        Number of consecutive trials that must be at or above ``threshold``.
    ignore_first : int, trials
        Number of initial trials ignored before checking the criterion.

    Returns
    -------
    tuple
        ``(found, indices)`` where ``found`` is bool. ``indices`` is either
        ``None`` or ``(start_index, end_index)`` in zero-based global trial
        coordinates.
    """
    if ignore_first >= len(dprime_values):
        return False, None

    consecutive_count = 0
    start_index = -1

    for i in range(ignore_first, len(dprime_values)):
        value = dprime_values[i]
        if np.isfinite(value) and value >= threshold:
            consecutive_count += 1
            if consecutive_count == 1:
                start_index = i
            if consecutive_count >= min_consecutive:
                return True, (start_index, i)
        else:
            consecutive_count = 0
            start_index = -1

    return False, None


def check_consecutive_lick_counts(lick_count_values, threshold=2, min_consecutive=100, ignore_first=0):
    """Check for consecutive low-lick trials indicating possible disengagement.

    Inputs
    ------
    lick_count_values : sequence of float or int, shape (n_trials,)
        Number of licks in each trial. Values may include ``numpy.nan`` for
        trials that have not been run; non-finite values are treated as engaged
        so future/unfilled trials do not create false disengagement alarms.
    threshold : float, licks/trial
        Trials with lick counts below this threshold count toward disengagement.
    min_consecutive : int, trials
        Number of consecutive below-threshold trials required.
    ignore_first : int, trials
        Number of initial entries in ``lick_count_values`` ignored.

    Returns
    -------
    tuple
        ``(found, indices)`` where ``found`` is bool. ``indices`` is either
        ``None`` or ``(start_index, end_index)`` relative to ``lick_count_values``.
    """
    if ignore_first >= len(lick_count_values):
        return False, None

    consecutive_count = 0
    start_index = -1

    for i in range(ignore_first, len(lick_count_values)):
        value = lick_count_values[i]
        if np.isfinite(value) and value < threshold:
            consecutive_count += 1
            if consecutive_count == 1:
                start_index = i
            if consecutive_count >= min_consecutive:
                return True, (start_index, i)
        else:
            consecutive_count = 0
            start_index = -1

    return False, None


def find_phase_disengagement(lick_count_values, phase_start_index, current_trial_index,
                             threshold=LICK_DISENGAGE_THRESHOLD,
                             min_consecutive=LICK_DISENGAGE_MIN_CONSECUTIVE):
    """Find low-lick disengagement within the current phase only.

    Inputs
    ------
    lick_count_values : sequence of float or int, shape (n_trials,)
        Per-trial lick counts in global trial coordinates.
    phase_start_index : int, trials
        Zero-based global index of the first trial in the current phase.
    current_trial_index : int, trials
        Zero-based global index of the latest completed trial.
    threshold : float, licks/trial
        Trials with lick counts below this threshold count toward disengagement.
    min_consecutive : int, trials
        Number of consecutive below-threshold trials required.

    Returns
    -------
    tuple
        ``(found, indices)`` where ``indices`` is either ``None`` or
        ``(start_index, end_index)`` in zero-based global trial coordinates.

    Notes
    -----
    This helper intentionally starts the search from ``phase_start_index`` so
    first-rule low-lick trials cannot summate with reversal low-lick trials.
    """
    if current_trial_index < phase_start_index:
        return False, None

    phase_values = lick_count_values[phase_start_index:current_trial_index + 1]
    found, relative_indices = check_consecutive_lick_counts(
        phase_values,
        threshold=threshold,
        min_consecutive=min_consecutive,
        ignore_first=0,
    )
    if not found:
        return False, None

    return True, (
        phase_start_index + relative_indices[0],
        phase_start_index + relative_indices[1],
    )


def should_leave_first_rule(first_rule_trials_completed, dprime_values,
                            max_first_rule_trials=MAX_FIRST_RULE_TRIALS,
                            threshold=DPRIME_THRESHOLD,
                            min_consecutive=DPRIME_MIN_CONSECUTIVE,
                            ignore_first=DPRIME_IGNORE_FIRST):
    """Decide whether the first-rule phase should end after the current trial.

    Inputs
    ------
    first_rule_trials_completed : int, trials
        Number of first-rule trials completed so far.
    dprime_values : sequence of float, shape (n_trials_completed,)
        Per-trial d-prime values through the current global trial.
    max_first_rule_trials : int, trials
        Maximum number of first-rule trials allowed.
    threshold : float, unitless
        D-prime criterion threshold.
    min_consecutive : int, trials
        Number of consecutive d-prime values required at/above threshold.
    ignore_first : int, trials
        Number of initial d-prime values ignored for criterion detection.

    Returns
    -------
    tuple
        ``(should_leave, reason, indices)``. ``reason`` is one of
        ``"criterion"``, ``"max_first_rule_trials"``, or ``"continue"``.
        ``indices`` is the criterion index tuple when reason is ``"criterion"``.
    """
    criterion_met, criterion_indices = check_consecutive_dprime(
        dprime_values,
        threshold=threshold,
        min_consecutive=min_consecutive,
        ignore_first=ignore_first,
    )
    if criterion_met:
        return True, "criterion", criterion_indices

    if first_rule_trials_completed >= max_first_rule_trials:
        return True, "max_first_rule_trials", None

    return False, "continue", None


def should_stop_reversal(reversal_trials_completed, max_reversal_trials=MAX_REVERSAL_TRIALS):
    """Decide whether the reversal phase has reached its trial limit.

    Inputs
    ------
    reversal_trials_completed : int, trials
        Number of reversal trials completed so far.
    max_reversal_trials : int, trials
        Maximum number of reversal trials allowed.

    Returns
    -------
    bool
        True when the reversal phase should stop and enter manual baseline.
    """
    return reversal_trials_completed >= max_reversal_trials


def init_trial_balance_state():
    """Create fresh go/no-go balancing state for one phase.

    Inputs
    ------
    None

    Returns
    -------
    dict
        Mutable state with cumulative go/no-go counts and consecutive-run
        counters. The state is in units of trials and should be reset at the
        first-rule to reversal boundary.
    """
    return {
        "go_nums": 0,
        "nogo_nums": 0,
        "consecutive_go": 0,
        "consecutive_nogo": 0,
    }


def _record_trial_identity_in_balance_state(trial_ident, balance_state):
    """Update go/no-go balancing counters after choosing one trial identity.

    Inputs
    ------
    trial_ident : str
        Either ``"go_trial"`` or ``"nogo_trial"``.
    balance_state : dict
        Mutable balancing state produced by ``init_trial_balance_state``.

    Returns
    -------
    dict
        The same ``balance_state`` object after in-place updates.
    """
    if trial_ident == "go_trial":
        balance_state["go_nums"] += 1
        balance_state["consecutive_go"] += 1
        balance_state["consecutive_nogo"] = 0
    elif trial_ident == "nogo_trial":
        balance_state["nogo_nums"] += 1
        balance_state["consecutive_nogo"] += 1
        balance_state["consecutive_go"] = 0
    else:
        raise ValueError("Unknown trial identity: " + str(trial_ident))
    return balance_state


def choose_balanced_trial_identity(phase_trial_index, balance_state, random_fn=None):
    """Choose the next trial identity with the same intent as the original scripts.

    Inputs
    ------
    phase_trial_index : int, trials
        Zero-based trial index within the current phase. This resets to zero at
        reversal start.
    balance_state : dict
        Mutable state from ``init_trial_balance_state``.
    random_fn : callable, optional
        Function returning a float in [0, 1). Defaults to ``random.random``.

    Returns
    -------
    str
        ``"go_trial"`` or ``"nogo_trial"``.

    Notes
    -----
    The first three trials of each phase are go trials, matching the existing
    first-rule and reversal launchers. After that, this helper prevents more
    than three consecutive trials of the same type and keeps cumulative go/no-go
    counts within approximately two trials.
    """
    if random_fn is None:
        random_fn = random.random

    if phase_trial_index < 3:
        trial_ident = "go_trial"
    elif balance_state["consecutive_go"] >= 3:
        trial_ident = "nogo_trial"
    elif balance_state["consecutive_nogo"] >= 3:
        trial_ident = "go_trial"
    elif balance_state["go_nums"] > balance_state["nogo_nums"] + 2:
        trial_ident = "nogo_trial"
    elif balance_state["nogo_nums"] > balance_state["go_nums"] + 2:
        trial_ident = "go_trial"
    else:
        ident_random = (round(float(random_fn()) * 100)) % 2
        if ident_random == 1:
            trial_ident = "go_trial"
        else:
            trial_ident = "nogo_trial"

    _record_trial_identity_in_balance_state(trial_ident, balance_state)
    return trial_ident


def _safe_rate(numerator, denominator, default=0.0):
    """Return a safe rate for d-prime calculations.

    Inputs
    ------
    numerator : float, trials
        Number of trials in the response category of interest.
    denominator : float, trials
        Number of possible trials for that response category.
    default : float
        Rate returned when ``denominator`` is zero.

    Returns
    -------
    float
        Rate in [0, 1].
    """
    if denominator <= 0:
        return float(default)
    return float(numerator) / float(denominator)


def _clip_rate_for_norm_ppf(rate):
    """Clip hit and false-alarm rates away from exactly 0 and exactly 1.

    Inputs
    ------
    rate : float
        Hit rate or false-alarm rate in [0, 1].

    Returns
    -------
    float
        Rate clipped to the interval [0.01, 0.99].
    """
    if rate >= 1:
        return 0.99
    if rate <= 0:
        return 0.01
    return rate


def calculate_dprime_for_trial(current_trial, hit_count, miss_count, cr_count, fa_count,
                               binsize=DPRIME_BINSIZE):
    """Calculate d-prime for the current global trial.

    Inputs
    ------
    current_trial : int, trials
        Zero-based global trial index.
    hit_count, miss_count, cr_count, fa_count : sequence of int, shape (n_trials,)
        Cumulative outcome counts in global trial coordinates.
    binsize : int, trials
        Rolling window size. After at least ``binsize`` trials, d-prime is
        computed from the most recent ``binsize`` trials. Before that, it is
        computed from all trials completed so far.

    Returns
    -------
    float
        Unitless d-prime value for ``current_trial``.

    Notes
    -----
    The rolling window is intentionally in global trial coordinates and is not
    reset at reversal. This preserves the continuous d-prime trace across the
    first-rule to reversal transition.
    """
    if current_trial > (binsize - 1):
        hitbin = hit_count[current_trial] - hit_count[current_trial - binsize]
        missbin = miss_count[current_trial] - miss_count[current_trial - binsize]
        crs = cr_count[current_trial] - cr_count[current_trial - binsize]
        fas = fa_count[current_trial] - fa_count[current_trial - binsize]
    else:
        hitbin = hit_count[current_trial]
        missbin = miss_count[current_trial]
        crs = cr_count[current_trial]
        fas = fa_count[current_trial]

    hit_rate = _safe_rate(hitbin, hitbin + missbin, default=0.0)
    false_alarm_rate = _safe_rate(fas, fas + crs, default=0.0)

    dhit = _clip_rate_for_norm_ppf(hit_rate)
    dfa = _clip_rate_for_norm_ppf(false_alarm_rate)
    return norm.ppf(dhit) - norm.ppf(dfa)


def outcome_to_text(trial_outcome):
    """Convert numeric task outcome codes into the strings used by the plotter.

    Inputs
    ------
    trial_outcome : int
        Task outcome code: 1 hit, 2 miss, 3 correct rejection, 4 false alarm.

    Returns
    -------
    str
        Human-readable outcome label.
    """
    if trial_outcome == 1:
        return "Hit!"
    if trial_outcome == 2:
        return "Miss !!!"
    if trial_outcome == 3:
        return "CR!"
    if trial_outcome == 4:
        return "FA !!!"
    return "Unknown"


def update_trial_arrays(current_trial, trial_outcome, combine_trial_outcome,
                        hit_count, miss_count, cr_count, fa_count):
    """Update cumulative outcome arrays after one completed trial.

    Inputs
    ------
    current_trial : int, trials
        Zero-based global trial index of the completed trial.
    trial_outcome : int
        Task outcome code: 1 hit, 2 miss, 3 correct rejection, 4 false alarm.
    combine_trial_outcome : list[str], shape (n_trials,)
        Per-trial outcome labels, modified in place.
    hit_count, miss_count, cr_count, fa_count : list[int], shape (n_trials,)
        Cumulative outcome counts, modified in place.

    Returns
    -------
    str
        Human-readable outcome label stored at ``combine_trial_outcome[current_trial]``.
    """
    outcome_text = outcome_to_text(trial_outcome)
    combine_trial_outcome[current_trial] = outcome_text

    completed_outcomes = combine_trial_outcome[0:current_trial + 1]
    hit_count[current_trial] = completed_outcomes.count("Hit!")
    miss_count[current_trial] = completed_outcomes.count("Miss !!!")
    cr_count[current_trial] = completed_outcomes.count("CR!")
    fa_count[current_trial] = completed_outcomes.count("FA !!!")
    return outcome_text


def _safe_percent(numerator, denominator):
    """Return a safe percentage value.

    Inputs
    ------
    numerator : float
        Numerator count.
    denominator : float
        Denominator count.

    Returns
    -------
    float
        Percentage in [0, 100], or 0 when denominator is zero.
    """
    if denominator <= 0:
        return 0.0
    return (float(numerator) / float(denominator)) * 100.0


def _event_list_or_empty(event_time):
    """Return a one-item event list unless the event time is missing.

    Inputs
    ------
    event_time : float or None, seconds
        Event time relative to trial start.

    Returns
    -------
    list[float]
        Empty list for missing/non-finite values, otherwise ``[event_time]``.
    """
    if event_time is None:
        return []
    try:
        if not np.isfinite(event_time):
            return []
    except TypeError:
        return []
    return [event_time]


def reverse_task_cue_mapping_in_place(task):
    """Reverse go/no-go cue objects on an already-open task object.

    Inputs
    ------
    task : object
        Running first-rule task object. It is expected to have a ``box`` object
        containing visual and auditory cue attributes.

    Returns
    -------
    list[str]
        Names of hooks or attribute pairs used for reversal.

    Raises
    ------
    RuntimeError
        If no explicit reversal hook or known cue-attribute pair can be found.

    Notes
    -----
    This function does not instantiate a new task object. It first honors common
    explicit task hooks if they exist, then falls back to swapping known cue
    attributes such as ``box.visualstim_go``/``box.visualstim_nogo`` and
    ``box.sound1``/``box.sound2``.
    """
    explicit_hook_names = [
        "set_reversal_rule",
        "set_rule_reversal",
        "reverse_rule",
        "reverse_cue_mapping",
        "switch_rule_to_reversal",
    ]

    for hook_name in explicit_hook_names:
        hook = getattr(task, hook_name, None)
        if callable(hook):
            hook()
            return ["hook:" + hook_name]

    swapped_pairs = []
    containers = [("task", task)]
    box = getattr(task, "box", None)
    if box is not None:
        containers.insert(0, ("box", box))

    candidate_pairs = [
        ("visualstim_go", "visualstim_nogo"),
        ("go_visualstim", "nogo_visualstim"),
        ("vstim_go", "vstim_nogo"),
        ("go_vstim", "nogo_vstim"),
        ("sound_go", "sound_nogo"),
        ("go_sound", "nogo_sound"),
        ("sound1", "sound2"),
        ("tone_go", "tone_nogo"),
        ("go_tone", "nogo_tone"),
    ]

    for container_name, container in containers:
        for go_attr, nogo_attr in candidate_pairs:
            if hasattr(container, go_attr) and hasattr(container, nogo_attr):
                go_value = getattr(container, go_attr)
                nogo_value = getattr(container, nogo_attr)
                setattr(container, go_attr, nogo_value)
                setattr(container, nogo_attr, go_value)
                swapped_pairs.append(container_name + "." + go_attr + "<->" + container_name + "." + nogo_attr)

    if not swapped_pairs:
        raise RuntimeError(
            "Could not reverse cue mapping in-place. Add a set_reversal_rule(), "
            "reverse_rule(), or reverse_cue_mapping() method to the task class, "
            "or expose go/no-go cue attributes on task.box."
        )

    return swapped_pairs


class go_nogo_transition_day(go_nogo_firstrule):
    """Go/no-go transition-day task wrapper around one first-rule task object.

    Inputs
    ------
    *args, **kwargs
        Passed directly to ``go_nogo_firstrule``. The parent class is expected
        to initialize hardware, cue objects, and the behavior box in the same
        way as the existing first-rule launcher.

    Attributes
    ----------
    rule_phase : str
        ``"first_rule"`` before the switch and ``"reversal"`` after cue
        mapping is reversed in-place.
    reversal_switch_method : list[str]
        Hooks or attribute pairs used to reverse the cue mapping.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rule_phase = FIRST_RULE_PHASE
        self.reversal_switch_method = []

    def switch_to_reversal_rule(self):
        """Reverse the cue mapping without creating a second task/session object.

        Inputs
        ------
        None

        Returns
        -------
        list[str]
            Hooks or attribute pairs used to reverse the cue mapping.
        """
        if self.rule_phase == REVERSAL_PHASE:
            return self.reversal_switch_method
        self.reversal_switch_method = reverse_task_cue_mapping_in_place(self)
        self.rule_phase = REVERSAL_PHASE
        return self.reversal_switch_method


def plot_trial_progress(current_trial, trial_list, combine_trial_outcome, hit_count, miss_count,
                        cr_count, fa_count, lick_times, reward_time, vstimON_time,
                        plot_dprime, dprimebinp, lick_per_trial_count,
                        phase_by_trial, phase_trial_count_by_trial,
                        phase_start_index, reversal_start_index, criterion_indices):
    """Render the live trial-progress figure in a separate process.

    Inputs
    ------
    current_trial : int, trials
        Zero-based global trial index being plotted.
    trial_list : list[int], shape (n_trials,)
        Global trial labels.
    combine_trial_outcome : list[str], shape (n_trials,)
        Per-trial outcome labels.
    hit_count, miss_count, cr_count, fa_count : list[int], shape (n_trials,)
        Cumulative outcome counts in global coordinates.
    lick_times : sequence[float], seconds
        Lick times for the current trial, relative to trial start.
    reward_time : float or None, seconds
        Reward time for the current trial, relative to trial start.
    vstimON_time : float, seconds
        Visual stimulus onset time for the current trial, relative to trial start.
    plot_dprime : bool
        Whether to draw the d-prime panel.
    dprimebinp : list[float], shape (n_trials,)
        Per-trial d-prime values in global coordinates.
    lick_per_trial_count : sequence[float], shape (n_trials,)
        Per-trial lick counts in global coordinates.
    phase_by_trial : list[str], shape (n_trials,)
        Per-trial phase labels.
    phase_trial_count_by_trial : list[int], shape (n_trials,)
        One-based trial count within the phase for each global trial.
    phase_start_index : int, trials
        Zero-based global trial index of the first trial in the current phase.
    reversal_start_index : int or None, trials
        Zero-based global trial index of the first reversal trial, or None
        before reversal starts.
    criterion_indices : tuple[int, int] or None
        First-rule criterion interval in global coordinates, when detected.

    Returns
    -------
    None
        The function displays a pygame window and closes after a short delay.
    """
    ########################################################################
    # initialize the figure
    ########################################################################
    fig = plt.figure(figsize=(14, 9))
    ax1 = fig.add_subplot(241)  # outcome
    ax2 = fig.add_subplot(212)  # eventplot
    ax3 = fig.add_subplot(242)  # outcomes
    ax4 = fig.add_subplot(243)  # dprime
    ax5 = fig.add_subplot(244)  # lick count

    phase_label = phase_by_trial[current_trial]
    phase_trial_number = phase_trial_count_by_trial[current_trial]
    recent_start = max(0, current_trial - 13)
    recent_lines = []
    for trial_index in range(recent_start, current_trial + 1):
        recent_lines.append(
            "trial " + str(trial_list[trial_index])
            + " [" + str(phase_by_trial[trial_index])
            + " #" + str(phase_trial_count_by_trial[trial_index])
            + "] : " + str(combine_trial_outcome[trial_index])
        )

    hit_percent = _safe_percent(
        hit_count[current_trial],
        hit_count[current_trial] + miss_count[current_trial],
    )
    cr_percent = _safe_percent(
        cr_count[current_trial],
        cr_count[current_trial] + fa_count[current_trial],
    )

    text_lines = [
        "phase: " + str(phase_label) + " | phase trial: " + str(phase_trial_number),
        "",
    ] + recent_lines + [
        "",
        "percent hit : " + str(round(hit_percent, 1)) + "%",
        "percent CR : " + str(round(cr_percent, 1)) + "%",
    ]
    ax1.set_title('Trial Outcome', fontsize=11)
    ax1.text(0.05, 0.95, '\n'.join(text_lines), fontsize=10, verticalalignment='top')
    ax1.set_xticklabels([])
    ax1.set_xticks([])
    ax1.set_yticks([])
    ax1.set_yticklabels([])

    ########################################################################
    # create eventplot (vertical)
    ########################################################################
    events_to_plot = [lick_times, _event_list_or_empty(reward_time)]
    plot_period = 7
    plot_bin_number = 800

    vstim_duration = 3  # in seconds, pre-generated
    vstim_bins = plot_bin_number
    time_vstim_on = vstimON_time
    time_vstim_index_on = int(round(time_vstim_on * vstim_bins / plot_period))
    time_vstim_index_off = int(time_vstim_index_on + round(vstim_duration * (vstim_bins / plot_period)))
    vstim_plot_data_x = np.linspace(0, plot_period, num=vstim_bins)
    vstim_plot_data_y = np.zeros(vstim_bins) - 1
    range_of_vstim_on = int(time_vstim_index_off - time_vstim_index_on)
    vstim_plot_data_y[time_vstim_index_on:time_vstim_index_off] = np.zeros(range_of_vstim_on) - 0.2

    colors1 = ['C{}'.format(c) for c in range(2)]
    lineoffsets1 = np.array([3, 2])
    linelengths1 = [0.8, 0.8]
    ax2.eventplot(events_to_plot, colors=colors1, lineoffsets=lineoffsets1, linelengths=linelengths1)
    ax2.plot(vstim_plot_data_x, vstim_plot_data_y)
    ax2.set_xlim([-0.5, 7])
    ax2.set_xlabel('Time since trial start (s)', fontsize=9)
    ax2.set_yticks((-1, 2, 3))
    ax2.set_yticklabels(('vstim', 'reward', 'lick'))

    ########################################################################
    # create cumulative outcome plot
    ########################################################################
    outcome_xvalue = np.linspace(0, current_trial, num=current_trial + 1)
    outcome_hit_count_yvalue = hit_count[0:current_trial + 1]
    outcome_miss_count_yvalue = miss_count[0:current_trial + 1]
    outcome_cr_count_yvalue = cr_count[0:current_trial + 1]
    outcome_fa_count_yvalue = fa_count[0:current_trial + 1]
    outcome_lick_count_yvalue = lick_per_trial_count[0:current_trial + 1]

    ax3.plot(outcome_xvalue, outcome_hit_count_yvalue, 'r-')
    ax3.lines[-1].set_label('Hit')
    ax3.plot(outcome_xvalue, outcome_miss_count_yvalue, 'b-')
    ax3.lines[-1].set_label('Miss')
    ax3.plot(outcome_xvalue, outcome_cr_count_yvalue, 'c-')
    ax3.lines[-1].set_label('CR')
    ax3.plot(outcome_xvalue, outcome_fa_count_yvalue, 'm-')
    ax3.lines[-1].set_label('FA')
    if reversal_start_index is not None and reversal_start_index <= current_trial:
        ax3.axvline(reversal_start_index, linestyle='--')
        ax3.text(reversal_start_index, max(1, hit_count[current_trial]), 'reversal start', rotation=90)

    ax3.set_title('Cummulative outcome', fontsize=11)
    ax3.set_xlim([0, current_trial + 1])
    ax3.set_xlabel('Current trial', fontsize=9)
    ax3.set_ylabel('Number of trials', fontsize=9)
    ax3.legend()

    ########################################################################
    # create lick count/disengagement plot with phase reset
    ########################################################################
    ax5.plot(outcome_xvalue, outcome_lick_count_yvalue, 'g-')
    ax5.lines[-1].set_label('Lick Count')
    ax5.plot([0, current_trial], [LICK_DISENGAGE_THRESHOLD, LICK_DISENGAGE_THRESHOLD], 'k--')
    if reversal_start_index is not None and reversal_start_index <= current_trial:
        ax5.axvline(reversal_start_index, linestyle='--')
    ax5.set_xlim([0, current_trial + 1])
    ax5.set_xlabel('Current trial', fontsize=9)
    ax5.set_ylabel('Number of licks', fontsize=9)

    found_lick_count, indices_lick_count = find_phase_disengagement(
        lick_per_trial_count,
        phase_start_index=phase_start_index,
        current_trial_index=current_trial,
    )
    if found_lick_count:
        ax5.set_title('ANIMAL DISENGAGED !!!', fontsize=13)
        ax5.scatter(
            np.arange(indices_lick_count[0], indices_lick_count[1] + 1),
            lick_per_trial_count[indices_lick_count[0]:indices_lick_count[1] + 1],
            marker='o',
            color='orange',
        )
        textstr_disengagement = (
            "Found " + str(indices_lick_count[1] - indices_lick_count[0] + 1)
            + " consecutive " + str(phase_label) + " trials with licks < "
            + str(LICK_DISENGAGE_THRESHOLD)
            + "\nStarting at global trial " + str(indices_lick_count[0])
            + ", ending at global trial " + str(indices_lick_count[1])
        )
        ax5.text(0.05, 1, textstr_disengagement, fontsize=10, verticalalignment='bottom')
    else:
        ax5.set_title('Lick Count', fontsize=11)
        textstr_disengagement = "Still Engaged in current phase"
        ax5.text(0.05, 1, textstr_disengagement, fontsize=10, verticalalignment='bottom')

    ########################################################################
    # create the d' figure
    ########################################################################
    if plot_dprime:
        ax4_x_values = np.linspace(0, current_trial, num=current_trial + 1)
        ax4_y_values = dprimebinp[0:current_trial + 1]
        ax4.plot(ax4_x_values, ax4_y_values, 'r-')
        ax4.plot([0, current_trial], [DPRIME_THRESHOLD, DPRIME_THRESHOLD], 'k--')
        if reversal_start_index is not None and reversal_start_index <= current_trial:
            ax4.axvline(reversal_start_index, linestyle='--')
            ax4.text(reversal_start_index, DPRIME_THRESHOLD, 'reversal start', rotation=90)
        ax4.set_xlim([0, current_trial + 1])
        ax4.set_xlabel('Current trial', fontsize=9)
        ax4.set_ylabel("d'", fontsize=9)

        if criterion_indices is not None and current_trial == criterion_indices[1]:
            ax4.set_title('CRITERION REACHED!!! SWITCHING TO REVERSAL', fontsize=12)
            ax4.scatter(
                np.arange(criterion_indices[0], criterion_indices[1] + 1),
                dprimebinp[criterion_indices[0]:criterion_indices[1] + 1],
                marker='o',
                color='orange',
            )
            textstr_dprime = (
                "Found " + str(criterion_indices[1] - criterion_indices[0] + 1)
                + " consecutive first-rule trials with d' >= " + str(DPRIME_THRESHOLD)
                + "\nStarting at global trial " + str(criterion_indices[0])
                + ", ending at global trial " + str(criterion_indices[1])
            )
            ax4.text(0.05, DPRIME_THRESHOLD, textstr_dprime, fontsize=10, verticalalignment='bottom')
        elif reversal_start_index is not None and current_trial >= reversal_start_index:
            ax4.set_title("D-prime across reversal", fontsize=11)
            ax4.text(0.05, DPRIME_THRESHOLD, "D-prime window continues across transition", fontsize=10, verticalalignment='bottom')
        else:
            ax4.set_title('D-prime', fontsize=11)
            ax4.text(0.05, DPRIME_THRESHOLD, "Not learned", fontsize=10, verticalalignment='bottom')

    ########################################################################
    # draw on canvas to display via pygame
    ########################################################################
    canvas = agg.FigureCanvasAgg(fig)
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()
    pygame.init()
    window = pygame.display.set_mode((1400, 900), DOUBLEBUF)
    screen = pygame.display.get_surface()
    size = canvas.get_width_height()
    surf = pygame.image.fromstring(raw_data, size, "RGB")
    screen.blit(surf, (0, 0))
    pygame.display.flip()
    plt.close(fig)
    time.sleep(3)
    pygame.quit()


def _find_session_info_dates(task_info_path):
    """Find available date-stamped go/no-go session-info files.

    Inputs
    ------
    task_info_path : str
        Directory containing files named ``go_nogo_session_info_YYYY-MM-DD.py``.

    Returns
    -------
    list[str]
        Sorted date strings in ``YYYY-MM-DD`` format. The list is empty when
        the directory does not exist or no matching files are present.
    """
    if not os.path.isdir(task_info_path):
        return []

    prefix = "go_nogo_session_info_"
    suffix = ".py"
    dates = []
    for filename in os.listdir(task_info_path):
        if not filename.startswith(prefix):
            continue
        if not filename.endswith(suffix):
            continue
        date_text = filename[len(prefix):-len(suffix)]
        if len(date_text) == 10 and date_text[4] == "-" and date_text[7] == "-":
            dates.append(date_text)
    return sorted(dates)


def _import_session_info_module(module_name, task_info_path):
    """Import one session-info module from the configured directory.

    Inputs
    ------
    module_name : str
        Python module name, for example ``go_nogo_session_info_2026-07-07``.
    task_info_path : str
        Directory containing session-info modules.

    Returns
    -------
    module
        Imported Python module. It is expected to expose ``session_info`` and
        may expose ``mouse_info``.
    """
    if task_info_path not in sys.path:
        sys.path.insert(0, task_info_path)
    return importlib.import_module(module_name)


def _mutable_mapping_copy(source_mapping):
    """Return a mutable top-level dictionary copy of a session metadata mapping.

    Inputs
    ------
    source_mapping : mapping
        Mapping-like object containing session metadata keys and values. This
        may be a normal ``dict`` or an immutable ``pysistence.PDict`` from the
        Raspberry Pi session-info files.

    Returns
    -------
    dict
        Mutable top-level dictionary with the same keys and values. Nested
        values are preserved as-is; no array shapes or physical units are
        changed.
    """
    return dict(source_mapping.items())


def load_session_info_for_date(datestr, task_info_path, input_fn=input):
    """Load the date-specific session-info dictionary for this run.

    Inputs
    ------
    datestr : str
        Current run date in ``YYYY-MM-DD`` format.
    task_info_path : str
        Directory containing files named ``go_nogo_session_info_YYYY-MM-DD.py``.
    input_fn : callable, optional
        Function used for interactive prompts. It must accept one prompt string
        and return one user-entered string. This argument is primarily for
        tests.

    Returns
    -------
    tuple
        ``(session_info, mouse_info)`` where ``session_info`` is a dict and
        ``mouse_info`` is the module's mouse metadata object, or an empty dict
        if the selected module does not define ``mouse_info``.
    """
    target_module_name = "go_nogo_session_info_" + datestr

    try:
        tempmod = _import_session_info_module(target_module_name, task_info_path)
        session_info = _mutable_mapping_copy(tempmod.session_info)
        mouse_info = _mutable_mapping_copy(getattr(tempmod, "mouse_info", {}))
        return session_info, mouse_info
    except ModuleNotFoundError as exc:
        if exc.name != target_module_name:
            raise

    available_dates = _find_session_info_dates(task_info_path)
    if not available_dates:
        raise RuntimeError(
            "No session info files found in " + task_info_path
            + ". Create " + target_module_name + ".py before running."
        )

    latest_date = available_dates[-1]
    print(Fore.RED + Style.BRIGHT + "No session info file found for " + datestr + Style.RESET_ALL)
    print("Looked for module: " + target_module_name)
    print("Recent available session-info dates: " + ", ".join(available_dates[-5:]))
    prompt_text = (
        "Press Enter to use latest session-info file (" + latest_date
        + ") as today's template, type another available date YYYY-MM-DD, "
        + "or type q to quit:\n"
    )
    selected_date = input_fn(prompt_text).strip()
    if selected_date.lower() in {"q", "quit", "n", "no"}:
        raise SystemExit
    if selected_date == "":
        selected_date = latest_date
    if selected_date not in available_dates:
        raise RuntimeError(
            "Selected session-info date " + selected_date
            + " was not found in " + task_info_path
        )

    selected_module_name = "go_nogo_session_info_" + selected_date
    tempmod = _import_session_info_module(selected_module_name, task_info_path)
    session_info = _mutable_mapping_copy(tempmod.session_info)
    mouse_info = _mutable_mapping_copy(getattr(tempmod, "mouse_info", {}))

    session_info["manual_date"] = datestr
    session_info["sessinfo_source"] = selected_module_name
    session_info["sessinfo_tpl_date"] = selected_date
    session_info["sessinfo_missing"] = datestr
    print("Using " + selected_module_name + " as today's session-info template.")
    return session_info, mouse_info


def save_session_info_files(session_info):
    """Save session metadata to MAT and PKL files without crashing cleanup.

    Inputs
    ------
    session_info : dict
        Session metadata dictionary. It must contain ``file_basename``.

    Returns
    -------
    bool
        True if at least one save operation succeeds, otherwise False.
    """
    file_basename = session_info.get("file_basename", None)
    if file_basename is None:
        return False

    saved_any = False

    try:
        scipy.io.savemat(file_basename + "_session_info.mat", {"session_info": session_info})
        saved_any = True
    except Exception as exc:
        logging.error(str(time.time()) + ", session_info MAT save failed: " + str(exc))

    try:
        pickle.dump(session_info, open(file_basename + "_session_info.pkl", "wb"))
        saved_any = True
    except Exception as exc:
        logging.error(str(time.time()) + ", session_info PKL save failed: " + str(exc))

    manual_baseline.flush_logging_handlers()
    return saved_any


def prompt_and_bait_first_rule(task, session_info, input_fn=input):
    """Deliver bait rewards until the operator starts the first-rule phase.

    Inputs
    ------
    task : object
        Running task object with ``pump.reward``.
    session_info : dict
        Session metadata with ``solenoid_blink_duration``.
    input_fn : callable
        Prompt function; primarily used for tests.

    Returns
    -------
    None
        Returns only after the operator types ``y`` and presses Enter.
    """
    while True:
        task.deliver_reward = input_fn(
            "Hit enter to deliver reward, or type y then enter to start first rule:\n"
        )
        if task.deliver_reward == "":
            task.pump.reward("1", session_info["solenoid_blink_duration"], 0.01, 6)
            continue
        if task.deliver_reward == "y":
            return


def run_one_behavior_trial(task, trial_ident, global_trial_index, rule_phase, phase_trial_index):
    """Run one go or no-go trial on the existing task object.

    Inputs
    ------
    task : object
        Running go/no-go task object.
    trial_ident : str
        ``"go_trial"`` or ``"nogo_trial"``.
    global_trial_index : int, trials
        Zero-based trial index across the whole transition-day session.
    rule_phase : str
        ``"first_rule"`` or ``"reversal"``.
    phase_trial_index : int, trials
        Zero-based trial index within the current phase.

    Returns
    -------
    dict
        Trial data with keys ``trial_outcome``, ``lick_times``,
        ``reward_time``, and ``vstimON_time``. Times are in seconds relative to
        trial start.
    """
    print(rule_phase + " " + trial_ident)
    logging.info(str(time.time()) + ", ##############################")
    logging.info(str(time.time()) + ", phase " + str(rule_phase))
    logging.info(str(time.time()) + ", starting global trial " + str(global_trial_index))
    logging.info(str(time.time()) + ", starting phase trial " + str(phase_trial_index))
    logging.info(str(time.time()) + ", " + trial_ident)
    logging.info(str(time.time()) + ", ##############################")

    if trial_ident == "go_trial":
        task.go_trial_start()
        while task.trial_running:
            task.run_go()
            task.box.flush_frame_events()
        task.box.flush_frame_events()
    elif trial_ident == "nogo_trial":
        task.nogo_trial_start()
        while task.trial_running:
            task.run_nogo()
            task.box.flush_frame_events()
        task.box.flush_frame_events()
    else:
        raise ValueError("Unknown trial identity: " + str(trial_ident))

    return {
        "trial_outcome": getattr(task, "trial_outcome", None),
        "lick_times": list(getattr(task, "lick_times", [])),
        "reward_time": getattr(task, "time_at_reward", None),
        "vstimON_time": getattr(task, "time_at_vstim_ON", 0.0),
    }


def record_completed_trial(current_trial, phase_label, phase_trial_number, trial_data,
                           session_info, trial_list, combine_trial_outcome,
                           hit_count, miss_count, cr_count, fa_count,
                           dprimebinp, lick_per_trial_count,
                           phase_by_trial, phase_trial_count_by_trial):
    """Record one completed trial into the live arrays and metadata.

    Inputs
    ------
    current_trial : int, trials
        Zero-based global trial index.
    phase_label : str
        ``"first_rule"`` or ``"reversal"``.
    phase_trial_number : int, trials
        One-based trial count within the current phase.
    trial_data : dict
        Trial data returned by ``run_one_behavior_trial``.
    session_info : dict
        Session metadata containing ``calibrated_drop`` when available.
    trial_list : list[int], shape (n_trials,)
        Global trial labels.
    combine_trial_outcome : list[str], shape (n_trials,)
        Per-trial outcome labels, modified in place.
    hit_count, miss_count, cr_count, fa_count : list[int], shape (n_trials,)
        Cumulative outcome arrays, modified in place.
    dprimebinp : list[float], shape (n_trials,)
        Per-trial d-prime array, modified in place.
    lick_per_trial_count : numpy.ndarray, shape (n_trials,)
        Per-trial lick-count array, modified in place.
    phase_by_trial : list[str], shape (n_trials,)
        Phase label array, modified in place.
    phase_trial_count_by_trial : list[int], shape (n_trials,)
        Phase-trial-count array, modified in place.

    Returns
    -------
    dict
        Updated trial summary with keys used by the plot process.
    """
    update_trial_arrays(
        current_trial=current_trial,
        trial_outcome=trial_data["trial_outcome"],
        combine_trial_outcome=combine_trial_outcome,
        hit_count=hit_count,
        miss_count=miss_count,
        cr_count=cr_count,
        fa_count=fa_count,
    )
    phase_by_trial[current_trial] = phase_label
    phase_trial_count_by_trial[current_trial] = phase_trial_number
    lick_times = trial_data["lick_times"]
    lick_per_trial_count[current_trial] = len(lick_times)
    dprimebinp[current_trial] = calculate_dprime_for_trial(
        current_trial=current_trial,
        hit_count=hit_count,
        miss_count=miss_count,
        cr_count=cr_count,
        fa_count=fa_count,
    )

    calibrated_drop = float(session_info.get("calibrated_drop", 0.0))
    logging.info(str(time.time()) + ", amount water received " + str(hit_count[current_trial] * calibrated_drop))
    logging.info(str(time.time()) + ", dprime " + str(dprimebinp[current_trial]))

    return {
        "lick_times": lick_times,
        "reward_time": trial_data["reward_time"],
        "vstimON_time": trial_data["vstimON_time"],
    }


def launch_plot_process(current_trial, trial_list, combine_trial_outcome, hit_count, miss_count,
                        cr_count, fa_count, plot_payload, dprimebinp, lick_per_trial_count,
                        phase_by_trial, phase_trial_count_by_trial, phase_start_index,
                        reversal_start_index, criterion_indices):
    """Launch the non-blocking pygame plot process for one trial.

    Inputs
    ------
    current_trial : int, trials
        Zero-based global trial index.
    trial_list, combine_trial_outcome, hit_count, miss_count, cr_count, fa_count : sequences
        Plotting arrays in global trial coordinates.
    plot_payload : dict
        Contains current-trial ``lick_times``, ``reward_time``, and
        ``vstimON_time``.
    dprimebinp : list[float]
        Per-trial d-prime values in global coordinates.
    lick_per_trial_count : numpy.ndarray
        Per-trial lick counts in global coordinates.
    phase_by_trial, phase_trial_count_by_trial : sequences
        Phase labels and phase-trial counts in global coordinates.
    phase_start_index : int, trials
        Start index for current-phase disengagement checks.
    reversal_start_index : int or None, trials
        Global start index of reversal, if reached.
    criterion_indices : tuple[int, int] or None
        First-rule criterion interval, if reached.

    Returns
    -------
    multiprocessing.Process
        The started plot process. It is intentionally not joined.
    """
    plot_process = Process(
        target=plot_trial_progress,
        args=(
            current_trial,
            trial_list,
            combine_trial_outcome,
            hit_count,
            miss_count,
            cr_count,
            fa_count,
            plot_payload["lick_times"],
            plot_payload["reward_time"],
            plot_payload["vstimON_time"],
            True,
            dprimebinp,
            lick_per_trial_count,
            phase_by_trial,
            phase_trial_count_by_trial,
            phase_start_index,
            reversal_start_index,
            criterion_indices,
        ),
    )
    plot_process.start()
    return plot_process


if __name__ == "__main__":
    task = None
    session_info = {}
    baseline_metadata = None
    behavior_session_started = False
    behavior_phase_started = False

    trial_list = []
    combine_trial_outcome = []
    hit_count = []
    miss_count = []
    cr_count = []
    fa_count = []
    dprimebinp = []
    lick_per_trial_count = np.array([])
    phase_by_trial = []
    phase_trial_count_by_trial = []

    first_rule_criterion_met = False
    criterion_indices = None
    reversal_start_index = None

    try:
        # load in session_info file, check that dates are correct, put in automatic
        # time and date stamps for when the experiment was run
        datestr = datetime.now().strftime("%Y-%m-%d")
        timestr = datetime.now().strftime('%H%M%S')
        task_info_path = '/home/pi/experiment_info/go_nogo_task/session_info'
        session_info, mouse_info = load_session_info_for_date(datestr, task_info_path)

        # ask user for task parameters
        animal_ID = input("Enter animal ID (ex DT000):\n")
        session_info['mouse_name'] = animal_ID
        animal_weight = input("Enter animal weight (ex 19.5):\n")
        session_info['weight'] = animal_weight
        training_phase = input("Enter training_phase (calibrate or transition_day):\n").strip()
        if training_phase == "":
            training_phase = "transition_day"
        session_info['training_phase'] = training_phase

        session_info['date'] = datestr
        session_info['time'] = timestr
        session_info['datetime'] = session_info['date'] + '_' + session_info['time']
        session_info['basename'] = session_info['mouse_name'] + '_' + session_info['datetime']
        session_info['dir_name'] = session_info['basedir'] + "/" + session_info['mouse_name'] + "_" + session_info['datetime']
        session_info['frame_sync_pin'] = session_info.get('frame_sync_pin', 16)
        session_info['transition_version'] = TRANSITION_FILE_VERSION
        session_info['transition_day'] = True
        session_info['first_rule_max_trials'] = MAX_FIRST_RULE_TRIALS
        session_info['reversal_max_trials'] = MAX_REVERSAL_TRIALS
        session_info['orig_num_trials'] = int(session_info.get('number_of_trials', TOTAL_MAX_TRIALS))
        session_info['number_of_trials'] = max(session_info['orig_num_trials'], TOTAL_MAX_TRIALS)

        if session_info['manual_date'] != session_info['date']:
            print('wrong date!!')
            raise RuntimeError('manual_date field in session_info file is not updated')

        # make data directory and initialize logfile
        os.makedirs(session_info['dir_name'])
        os.chdir(session_info['dir_name'])
        session_info['file_basename'] = session_info['mouse_name'] + "_" + training_phase + "_" + session_info['datetime']
        session_info['log_file_path'] = os.path.abspath(session_info['file_basename'] + '.log')
        session_info['baseline_req_dur_s'] = -1.0
        session_info['baseline_req_dur_min'] = -1.0
        session_info['baseline_manual'] = True
        manual_baseline.configure_session_logging(session_info['log_file_path'])
        manual_baseline.log_session_event('session_log_start', session_info=session_info)

        # initiate one task object for the whole transition-day session
        task = go_nogo_transition_day(name="go_nogo_transition_day", session_info=session_info)
        trial_list = list(range(0, session_info["number_of_trials"]))
        combine_trial_outcome = ["" for o in range(session_info["number_of_trials"])]
        hit_count = [0 for o in range(session_info["number_of_trials"])]
        miss_count = [0 for o in range(session_info["number_of_trials"])]
        cr_count = [0 for o in range(session_info["number_of_trials"])]
        fa_count = [0 for o in range(session_info["number_of_trials"])]
        dprimebinp = [np.nan for o in range(session_info["number_of_trials"])]
        lick_per_trial_count = np.full(session_info["number_of_trials"], np.nan)
        phase_by_trial = ["" for o in range(session_info["number_of_trials"])]
        phase_trial_count_by_trial = [0 for o in range(session_info["number_of_trials"])]

        # start session
        task.start_session()
        behavior_session_started = True
        save_session_info_files(session_info)

        if training_phase == "calibrate":
            weight_tube = float(input("weight_tube: "))
            print("Delivering reward 100 times")
            task.calibrate()
            weight_total = float(input("weight_total: "))
            print("Fluid volume per drop = " + str((weight_total - weight_tube) / 100) + " ml")
            raise SystemExit

        if training_phase != "transition_day":
            raise RuntimeError("training_phase must be calibrate or transition_day")

        prompt_and_bait_first_rule(task, session_info)
        behavior_phase_started = True
        manual_baseline.log_session_event('behavior_phase_start', session_info=session_info)

        session_info['first_rule_start_trial'] = 0
        session_info['rule_switch_trial'] = -1
        session_info['rule_switch_reason'] = ''
        session_info['rule_switch_method'] = ''
        session_info['reversal_start_trial'] = -1
        session_info['behavior_stop_reason'] = ''
        save_session_info_files(session_info)

        current_global_trial = 0

        ####################################################################
        # First-rule phase: stop on criterion or 500 trials, whichever first.
        ####################################################################
        first_rule_balance_state = init_trial_balance_state()
        first_rule_trials_completed = 0
        first_rule_stop_reason = "max_first_rule_trials"

        for phase_trial_index in range(MAX_FIRST_RULE_TRIALS):
            current_trial = current_global_trial
            phase_trial_number = phase_trial_index + 1
            trial_ident = choose_balanced_trial_identity(phase_trial_index, first_rule_balance_state)

            trial_data = run_one_behavior_trial(
                task=task,
                trial_ident=trial_ident,
                global_trial_index=current_trial,
                rule_phase=FIRST_RULE_PHASE,
                phase_trial_index=phase_trial_index,
            )
            plot_payload = record_completed_trial(
                current_trial=current_trial,
                phase_label=FIRST_RULE_PHASE,
                phase_trial_number=phase_trial_number,
                trial_data=trial_data,
                session_info=session_info,
                trial_list=trial_list,
                combine_trial_outcome=combine_trial_outcome,
                hit_count=hit_count,
                miss_count=miss_count,
                cr_count=cr_count,
                fa_count=fa_count,
                dprimebinp=dprimebinp,
                lick_per_trial_count=lick_per_trial_count,
                phase_by_trial=phase_by_trial,
                phase_trial_count_by_trial=phase_trial_count_by_trial,
            )

            first_rule_trials_completed = phase_trial_number
            should_leave, first_rule_stop_reason, candidate_criterion_indices = should_leave_first_rule(
                first_rule_trials_completed=first_rule_trials_completed,
                dprime_values=dprimebinp[0:current_trial + 1],
            )
            if first_rule_stop_reason == "criterion":
                first_rule_criterion_met = True
                criterion_indices = candidate_criterion_indices

            launch_plot_process(
                current_trial=current_trial,
                trial_list=trial_list,
                combine_trial_outcome=combine_trial_outcome,
                hit_count=hit_count,
                miss_count=miss_count,
                cr_count=cr_count,
                fa_count=fa_count,
                plot_payload=plot_payload,
                dprimebinp=dprimebinp,
                lick_per_trial_count=lick_per_trial_count,
                phase_by_trial=phase_by_trial,
                phase_trial_count_by_trial=phase_trial_count_by_trial,
                phase_start_index=session_info['first_rule_start_trial'],
                reversal_start_index=reversal_start_index,
                criterion_indices=criterion_indices,
            )

            current_global_trial += 1

            if should_leave:
                break

        session_info['first_rule_trial_count'] = first_rule_trials_completed
        session_info['first_rule_stop_reason'] = first_rule_stop_reason
        session_info['first_rule_criterion'] = bool(first_rule_criterion_met)
        if criterion_indices is not None:
            session_info['criterion_start_trial'] = int(criterion_indices[0])
            session_info['criterion_end_trial'] = int(criterion_indices[1])
        else:
            session_info['criterion_start_trial'] = -1
            session_info['criterion_end_trial'] = -1

        ####################################################################
        # Switch to reversal immediately: no second task object is created.
        ####################################################################
        reversal_start_index = current_global_trial
        session_info['rule_switch_trial'] = reversal_start_index
        session_info['rule_switch_reason'] = first_rule_stop_reason
        session_info['reversal_start_trial'] = reversal_start_index

        switch_method = task.switch_to_reversal_rule()
        session_info['rule_switch_method'] = ','.join(switch_method)
        manual_baseline.log_session_event('rule_switch_to_reversal', session_info=session_info)
        logging.info(str(time.time()) + ", SWITCHING TO REVERSAL at global trial " + str(reversal_start_index))
        logging.info(str(time.time()) + ", switch reason " + str(first_rule_stop_reason))
        logging.info(str(time.time()) + ", switch method " + str(session_info['rule_switch_method']))
        print(Fore.RED + Style.BRIGHT + "Switching to reversal at global trial " + str(reversal_start_index) + Style.RESET_ALL)
        print("Switch reason: " + str(first_rule_stop_reason))
        print("Switch method: " + str(session_info['rule_switch_method']))
        save_session_info_files(session_info)

        ####################################################################
        # Reversal phase: max 500 trials, or Ctrl+C to enter baseline sooner.
        ####################################################################
        reversal_balance_state = init_trial_balance_state()
        reversal_trials_completed = 0

        for phase_trial_index in range(MAX_REVERSAL_TRIALS):
            current_trial = current_global_trial
            phase_trial_number = phase_trial_index + 1
            trial_ident = choose_balanced_trial_identity(phase_trial_index, reversal_balance_state)

            trial_data = run_one_behavior_trial(
                task=task,
                trial_ident=trial_ident,
                global_trial_index=current_trial,
                rule_phase=REVERSAL_PHASE,
                phase_trial_index=phase_trial_index,
            )
            plot_payload = record_completed_trial(
                current_trial=current_trial,
                phase_label=REVERSAL_PHASE,
                phase_trial_number=phase_trial_number,
                trial_data=trial_data,
                session_info=session_info,
                trial_list=trial_list,
                combine_trial_outcome=combine_trial_outcome,
                hit_count=hit_count,
                miss_count=miss_count,
                cr_count=cr_count,
                fa_count=fa_count,
                dprimebinp=dprimebinp,
                lick_per_trial_count=lick_per_trial_count,
                phase_by_trial=phase_by_trial,
                phase_trial_count_by_trial=phase_trial_count_by_trial,
            )

            reversal_trials_completed = phase_trial_number
            launch_plot_process(
                current_trial=current_trial,
                trial_list=trial_list,
                combine_trial_outcome=combine_trial_outcome,
                hit_count=hit_count,
                miss_count=miss_count,
                cr_count=cr_count,
                fa_count=fa_count,
                plot_payload=plot_payload,
                dprimebinp=dprimebinp,
                lick_per_trial_count=lick_per_trial_count,
                phase_by_trial=phase_by_trial,
                phase_trial_count_by_trial=phase_trial_count_by_trial,
                phase_start_index=reversal_start_index,
                reversal_start_index=reversal_start_index,
                criterion_indices=criterion_indices,
            )

            current_global_trial += 1
            if should_stop_reversal(reversal_trials_completed):
                break

        session_info['reversal_trial_count'] = reversal_trials_completed
        session_info['behavior_stop_reason'] = 'max_reversal_trials'
        session_info['total_behavior_trials'] = current_global_trial
        save_session_info_files(session_info)
        raise SystemExit

    # graceful exit from behavior into manual count-up baseline
    except (KeyboardInterrupt, SystemExit) as exit_reason:
        print(Fore.RED + Style.BRIGHT + 'Exiting behavior phase...' + Style.RESET_ALL)

        training_phase_for_exit = session_info.get('training_phase', None)
        if session_info.get('behavior_stop_reason', '') == '':
            if isinstance(exit_reason, KeyboardInterrupt):
                session_info['behavior_stop_reason'] = 'keyboard_interrupt'
            elif isinstance(exit_reason, SystemExit):
                session_info['behavior_stop_reason'] = 'system_exit'
            else:
                session_info['behavior_stop_reason'] = 'unknown_exit'

        should_run_baseline = (
            task is not None
            and behavior_session_started
            and behavior_phase_started
            and training_phase_for_exit in {'transition_day'}
        )

        if should_run_baseline:
            manual_baseline.log_session_event('behavior_phase_exit', session_info=session_info)
            baseline_metadata = manual_baseline.run_countup_baseline(
                task,
                session_info=session_info,
            )
            session_info.update(baseline_metadata)
        else:
            session_info['baseline_requested'] = False
            session_info['baseline_completed'] = False
            session_info['baseline_interrupted'] = False

        print(Fore.RED + Style.BRIGHT + 'Exiting now...' + Style.RESET_ALL)

        criterion_message = 'first-rule criterion met' if first_rule_criterion_met else 'first-rule criterion not met'
        reversal_message = 'reversal trials completed: ' + str(session_info.get('reversal_trial_count', 0))
        stop_message = 'behavior stop reason: ' + str(session_info.get('behavior_stop_reason', 'unknown'))

        ic('about to call end_session()')
        if task is not None:
            try:
                task.box.flush_frame_events()
            except Exception:
                pass
            try:
                task.end_session()
            except Exception as exc:
                logging.warning(str(time.time()) + ', end_session warning: ' + str(exc))
                try:
                    task.box.video_stop()
                except Exception:
                    pass
            try:
                task.box.flush_frame_events()
            except Exception:
                pass
        ic('just called end_session()')

        print(criterion_message)
        print(reversal_message)
        print(stop_message)
        logging.info(criterion_message)
        logging.info(reversal_message)
        logging.info(stop_message)

        # save dicts to disk
        save_session_info_files(session_info)
        pygame.quit()
