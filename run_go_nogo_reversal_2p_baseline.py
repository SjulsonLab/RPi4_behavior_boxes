debug_enable = False

from icecream import ic
from datetime import datetime
import os
import sys
import copy
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

# import the go_nogo_task task class here
from go_nogo_reversal_2p import go_nogo_reversal
import go_nogo_manual_baseline as manual_baseline

# define dprime processing function for criterion
# default is dprime>2.5 for at least 30 consecutive trials
def check_consecutive_dprime(dprime_values, threshold=2.5, min_consecutive=30, ignore_first=30):
    """
    Check if there are at least min_consecutive trials with d' > threshold,
    ignoring the first ignore_first trials.
    
    Parameters:
    - dprime_values: List or array of d' values
    - threshold: Threshold value for d' (default 2.5)
    - min_consecutive: Minimum number of consecutive trials required (default 30)
    - ignore_first: Number of initial trials to ignore (default 40)
    
    Returns:
    - True if condition is met, False otherwise
    - Also returns the indices where this occurs (if found)
    """
    if ignore_first >= len(dprime_values):
        return False, None
    
    consecutive_count = 0
    start_index = -1
    
    for i in range(ignore_first, len(dprime_values)):
        value = dprime_values[i]
        if value >= threshold:
            consecutive_count += 1
            if consecutive_count == 1:  # First in potential sequence
                start_index = i
            if consecutive_count >= min_consecutive:
                return True, (start_index, i)
        else:
            consecutive_count = 0
            start_index = -1
    
    return False, None

def check_consecutive_lick_counts(lick_count_values, threshold=2, min_consecutive=100, ignore_first=0):
    """
    Same as the above function, but for lick counts
    """
    if ignore_first >= len(lick_count_values):
        return False, None
    
    consecutive_count = 0
    start_index = -1
    
    for i in range(ignore_first, len(lick_count_values)):
        value = lick_count_values[i]
        if value < threshold:
            consecutive_count += 1
            if consecutive_count == 1:  # First in potential sequence
                start_index = i
            if consecutive_count >= min_consecutive:
                return True, (start_index, i)
        else:
            consecutive_count = 0
            start_index = -1
    
    return False, None

# define the plotting function here
def plot_trial_progress(current_trial, trial_list, combine_trial_outcome, hit_count, miss_count,
                        cr_count, fa_count, lick_times, vstimON_time, plot_dprime, dprimebinp, lick_per_trial_count):
    ########################################################################
    # initialize the figure
    ########################################################################
    fig = plt.figure(figsize=(14, 9))
    ax1 = fig.add_subplot(241)  # outcome
    ax2 = fig.add_subplot(212)  # eventplot
    ax3 = fig.add_subplot(242) # outcomes
    ax4 = fig.add_subplot(243) # dprime
    ax5 = fig.add_subplot(244) # lick count

    ########################################################################
    # create an outcome plot
    ########################################################################
    if current_trial < 14:
        textstr = '\n'.join((
            f"trial {trial_list[0]} : {combine_trial_outcome[0]}",
            f"trial {trial_list[1]} : {combine_trial_outcome[1]}",
            f"trial {trial_list[2]} : {combine_trial_outcome[2]}",
            f"trial {trial_list[3]} : {combine_trial_outcome[3]}",
            f"trial {trial_list[4]} : {combine_trial_outcome[4]}",
            f"trial {trial_list[5]} : {combine_trial_outcome[5]}",
            f"trial {trial_list[6]} : {combine_trial_outcome[6]}",
            f"trial {trial_list[7]} : {combine_trial_outcome[7]}",
            f"trial {trial_list[8]} : {combine_trial_outcome[8]}",
            f"trial {trial_list[9]} : {combine_trial_outcome[9]}",
            f"trial {trial_list[10]} : {combine_trial_outcome[10]}",
            f"trial {trial_list[11]} : {combine_trial_outcome[11]}",
            f"trial {trial_list[12]} : {combine_trial_outcome[12]}",
            f"trial {trial_list[13]} : {combine_trial_outcome[13]}",
            f" ",
            f"percent hit : {round(((hit_count[current_trial]/(hit_count[current_trial] + miss_count[current_trial]))*100), 1)}%",
            f" "))

    elif current_trial >= 14:
        textstr = '\n'.join((
            f"trial {trial_list[0 + (current_trial - 13)]} : {combine_trial_outcome[0 + (current_trial - 13)]}",
            f"trial {trial_list[1 + (current_trial - 13)]} : {combine_trial_outcome[1 + (current_trial - 13)]}",
            f"trial {trial_list[2 + (current_trial - 13)]} : {combine_trial_outcome[2 + (current_trial - 13)]}",
            f"trial {trial_list[3 + (current_trial - 13)]} : {combine_trial_outcome[3 + (current_trial - 13)]}",
            f"trial {trial_list[4 + (current_trial - 13)]} : {combine_trial_outcome[4 + (current_trial - 13)]}",
            f"trial {trial_list[5 + (current_trial - 13)]} : {combine_trial_outcome[5 + (current_trial - 13)]}",
            f"trial {trial_list[6 + (current_trial - 13)]} : {combine_trial_outcome[6 + (current_trial - 13)]}",
            f"trial {trial_list[7 + (current_trial - 13)]} : {combine_trial_outcome[7 + (current_trial - 13)]}",
            f"trial {trial_list[8 + (current_trial - 13)]} : {combine_trial_outcome[8 + (current_trial - 13)]}",
            f"trial {trial_list[9 + (current_trial - 13)]} : {combine_trial_outcome[9 + (current_trial - 13)]}",
            f"trial {trial_list[10 + (current_trial - 13)]} : {combine_trial_outcome[10 + (current_trial - 13)]}",
            f"trial {trial_list[11 + (current_trial - 13)]} : {combine_trial_outcome[11 + (current_trial - 13)]}",
            f"trial {trial_list[12 + (current_trial - 13)]} : {combine_trial_outcome[12 + (current_trial - 13)]}",
            f"trial {trial_list[13 + (current_trial - 13)]} : {combine_trial_outcome[13 + (current_trial - 13)]}",
            f" ",
            f"percent hit : {round(((hit_count[current_trial] / (hit_count[current_trial] + miss_count[current_trial]))*100), 1)}%",
            f" "))

    ax1.set_title('Trial Outcome', fontsize=11)
    ax1.text(0.05, 0.95, textstr, fontsize=11, verticalalignment='top')
    ax1.set_xticklabels([])
    ax1.set_xticks([])
    ax1.set_yticks([])
    ax1.set_yticklabels([])

    ########################################################################
    # create eventplot (vertical)
    ########################################################################
    # create a 2D array for eventplot
    events_to_plot = [lick_times, [reward_time]]
    if combine_trial_outcome[current_trial] == "FA !!!":
        plot_period = 7  # in seconds, how long to plot since the start of trial
        plot_bin_number = 800
    else:
        plot_period = 7
        plot_bin_number = 800

    # create vstim time data
    vstim_duration = 3  # in seconds, pre-generated
    vstim_bins = plot_bin_number  # number of bins
    time_vstim_on = vstimON_time
    time_vstim_index_on = int(round(time_vstim_on * vstim_bins / plot_period))
    time_vstim_index_off = int(time_vstim_index_on + round(vstim_duration * (vstim_bins / plot_period)))
    vstim_plot_data_x = np.linspace(0, plot_period, num=vstim_bins)
    vstim_plot_data_y = np.zeros(vstim_bins) - 1
    range_of_vstim_on = int(time_vstim_index_off - time_vstim_index_on)
    vstim_plot_data_y[time_vstim_index_on:time_vstim_index_off] = np.zeros(range_of_vstim_on) - 0.2

    # set different colors for each set of positions
    colors1 = ['C{}'.format(c) for c in range(2)]
    # set different line properties for each set of positions
    lineoffsets1 = np.array([3, 2])
    linelengths1 = [0.8, 0.8]
    ax2.eventplot(events_to_plot, colors=colors1, lineoffsets=lineoffsets1, linelengths=linelengths1)
    ax2.plot(vstim_plot_data_x, vstim_plot_data_y)
    ax2.set_xlim([-0.5, 7])  # 8s total to show (trial duration)
    ax2.set_xlabel('Time since trial start (s)', fontsize=9)
    ax2.set_yticks((-1, 2, 3))
    ax2.set_yticklabels(('vstim', 'reward', 'lick'))

    ########################################################################
    # create cumulative outcome plot
    ########################################################################
    # Get data to plot for current trial
    outcome_xvalue = np.linspace(0, current_trial, num=current_trial + 1)
    outcome_hit_count_yvalue = hit_count[0:current_trial + 1]
    outcome_miss_count_yvalue = miss_count[0:current_trial + 1]
    outcome_cr_count_yvalue = cr_count[0:current_trial + 1]
    outcome_fa_count_yvalue = fa_count[0:current_trial + 1]
    outcome_lick_count_yvalue = lick_per_trial_count[0:current_trial + 1]

    # Plot
    ax3.plot(outcome_xvalue, outcome_hit_count_yvalue, 'r-')
    ax3.lines[-1].set_label('Hit')
    ax3.plot(outcome_xvalue, outcome_miss_count_yvalue, 'b-')
    ax3.lines[-1].set_label('Miss')
    ax3.plot(outcome_xvalue, outcome_cr_count_yvalue, 'c-')
    ax3.lines[-1].set_label('CR')
    ax3.plot(outcome_xvalue, outcome_fa_count_yvalue, 'm-')
    ax3.lines[-1].set_label('FA')

    ax3.set_title('Cummulative outcome', fontsize=11)
    ax3.set_xlim([0, current_trial + 1])
    ax3.set_xlabel('Current trial', fontsize=9)
    ax3.set_ylabel('Number of trials', fontsize=9)
    ax3.legend()

    ax5.plot(outcome_xvalue,outcome_lick_count_yvalue,'g-')
    ax5.lines[-1].set_label('Lick Count')
    ax5.plot([0, current_trial],[2, 2], 'k--')
    ax5.set_xlim([0, current_trial+1])
    ax5.set_xlabel('Current trial', fontsize=9)
    ax5.set_ylabel('Number of licks', fontsize=9)
    #ax5.legend()

    found_lick_count, indices_lick_count = check_consecutive_lick_counts(lick_per_trial_count)
    if found_lick_count:
        ax5.set_title('ANIMAL DISENGAGED !!!', fontsize=13)
        ax5.scatter(np.arange(indices_lick_count[0],indices_lick_count[1]+1), lick_per_trial_count[indices_lick_count[0]:indices_lick_count[1]+1], marker='o', color='orange')
        textstr_disengagement = f"Found {indices_lick_count[1] - indices_lick_count[0] + 1} consecutive trials with licks < 2\nStarting at trial {indices_lick_count[0]}, ending at trial {indices_lick_count[1]}"
        ax5.text(0.05, 1, textstr_disengagement, fontsize=11, verticalalignment='bottom')
    else:
        ax5.set_title('Lick Count', fontsize=11)
        textstr_disengagement = f"Still Engaged"
        ax5.text(0.05, 1, textstr_disengagement, fontsize=11, verticalalignment='bottom')

    ########################################################################
    # create the d' figure
    ########################################################################

    if plot_dprime == True:
        ax4_x_values = np.linspace(0, current_trial, num=current_trial + 1)
        ax4_y_values = dprimebinp[0:current_trial+1]
        ax4.plot(ax4_x_values, ax4_y_values, 'r-')
        ax4.plot([0, current_trial],[2.5, 2.5], 'k--')
        # ax4.set_title('D-prime', fontsize=11)
        ax4.set_xlim([0, current_trial + 1])
        ax4.set_xlabel('Current trial', fontsize=9)
        
        found, indices = check_consecutive_dprime(dprimebinp)
        if found:
            ax4.set_title('CRITERION REACHED!!!', fontsize=13)
            ax4.scatter(np.arange(indices[0],indices[1]+1), dprimebinp[indices[0]:indices[1]+1], marker='o', color='orange')
            textstr_dprime = f"Found {indices[1] - indices[0] + 1} consecutive trials with d' > 2.5\nStarting at trial {indices[0]}, ending at trial {indices[1]}"
            ax4.text(0.05, 2.5, textstr_dprime, fontsize=11, verticalalignment='bottom')
        else:
            ax4.set_title('D-prime', fontsize=11)
            textstr_dprime = f"Not learned"
            ax4.text(0.05, 2.5, textstr_dprime, fontsize=11, verticalalignment='bottom')

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
    time.sleep(3)  # sleep for 3 seconds for pygame to remain displayed
    pygame.quit()


def _find_session_info_dates(task_info_path):
    """Find available date-stamped go/no-go session-info files.

    Inputs
    ------
    task_info_path : str
        Directory containing files named
        ``go_nogo_session_info_YYYY-MM-DD.py``.

    Returns
    -------
    list of str
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
        Python module name, for example
        ``go_nogo_session_info_2026-07-07``.
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


def load_session_info_for_date(datestr, task_info_path, input_fn=input):
    """Load the date-specific session-info dictionary for this run.

    Inputs
    ------
    datestr : str
        Current run date in ``YYYY-MM-DD`` format.
    task_info_path : str
        Directory containing files named
        ``go_nogo_session_info_YYYY-MM-DD.py``.
    input_fn : callable, optional
        Function used for interactive prompts. It must accept one prompt
        string and return one user-entered string. This argument is primarily
        for tests.

    Returns
    -------
    tuple
        ``(session_info, mouse_info)`` where ``session_info`` is a dict and
        ``mouse_info`` is the module's mouse metadata object, or an empty dict
        if the selected module does not define ``mouse_info``.

    Notes
    -----
    The original run script requires a daily session-info module. If today's
    module is missing, this helper prompts before using the most recent
    available file as a template for today. The template choice is recorded in
    short MATLAB-safe keys in ``session_info``.
    """
    target_module_name = "go_nogo_session_info_" + datestr

    try:
        tempmod = _import_session_info_module(target_module_name, task_info_path)
        session_info = copy.deepcopy(tempmod.session_info)
        mouse_info = copy.deepcopy(getattr(tempmod, "mouse_info", {}))
        return session_info, mouse_info
    except ModuleNotFoundError as exc:
        # Re-raise missing dependencies inside a session-info module. Only
        # handle the common case where today's session-info module itself is
        # absent.
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
    session_info = copy.deepcopy(tempmod.session_info)
    mouse_info = copy.deepcopy(getattr(tempmod, "mouse_info", {}))

    # Treat the selected file as a template for today's run. Do not write the
    # module back to disk; just make the in-memory session_info pass the
    # existing date sanity check below.
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

    Notes
    -----
    The PKL save is attempted even if the MAT save fails. This keeps cleanup
    from crashing if MATLAB rejects a metadata field name.
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



if __name__ == "__main__":
    task = None
    session_info = {}
    baseline_metadata = None
    behavior_session_started = False
    behavior_phase_started = False
    try:
        # load in session_info file, check that dates are correct, put in automatic
        # time and date stamps for when the experiment was run
        datestr = datetime.now().strftime("%Y-%m-%d")
        timestr = datetime.now().strftime('%H%M%S')
        task_info_path = '/home/pi/experiment_info/go_nogo_task/session_info'
        session_info, mouse_info = load_session_info_for_date(datestr, task_info_path)

        # ask user for task parameters
        # training_date_time = input("Enter date (ex 2022-11-22):\n")
        # session_info['manual_date'] = training_date_time
        animal_ID = input("Enter animal ID (ex DT000):\n")
        session_info['mouse_name'] = animal_ID
        animal_weight = input("Enter animal weight (ex 19.5):\n")
        session_info['weight'] = animal_weight
        training_phase = input("Enter training_phase (calibrate or allgo or reversal):\n")
        session_info['training_phase'] = training_phase

        session_info['date'] = datestr
        session_info['time'] = timestr
        session_info['datetime'] = session_info['date'] + '_' + session_info['time']
        session_info['basename'] = session_info['mouse_name'] + '_' + session_info['datetime']
        session_info['dir_name'] = session_info['basedir'] + "/" + session_info['mouse_name'] + "_" + session_info['datetime']
        ## new edit 2026.04.03 add the sync pin number 16
        session_info['frame_sync_pin'] = session_info.get('frame_sync_pin', 16) 

        if session_info['manual_date'] != session_info['date']:  # check if file is updated
            print('wrong date!!')
            raise RuntimeError('manual_date field in session_info file is not updated')

        # make data directory and initialize logfile
        os.makedirs( session_info['dir_name'] )
        os.chdir( session_info['dir_name'] )
        session_info['file_basename'] = session_info['mouse_name'] + "_" + training_phase + "_" + session_info['datetime']
        session_info['log_file_path'] = os.path.abspath(session_info['file_basename'] + '.log')
        session_info['baseline_req_dur_s'] = -1.0
        session_info['baseline_req_dur_min'] = -1.0
        session_info['baseline_manual'] = True
        manual_baseline.configure_session_logging(session_info['log_file_path'])
        manual_baseline.log_session_event('session_log_start', session_info=session_info)

        # initiate task object
        task = go_nogo_reversal(name="go_nogo_reversal", session_info=session_info)
        trial_list = list(range(0, session_info["number_of_trials"]))
        combine_trial_outcome = ["" for o in range(session_info["number_of_trials"])]
        hit_count = [0 for o in range(session_info["number_of_trials"])]
        miss_count = [0 for o in range(session_info["number_of_trials"])]
        cr_count = [0 for o in range(session_info["number_of_trials"])]
        fa_count = [0 for o in range(session_info["number_of_trials"])]
        dprimebinp = [0 for o in range(session_info["number_of_trials"])]
        lick_per_trial_count = np.full(session_info["number_of_trials"],np.nan)

        # start session
        task.start_session()
        behavior_session_started = True
        save_session_info_files(session_info)

        # Loops over trials for phase 2 training
        avoid_go = 0
        avoid_nogo = 0
        go_nums = 0
        nogo_nums = 0

        if training_phase == "calibrate":
            weight_tube = float(input("weight_tube: "))
            print("Delivering reward 100 times")
            task.calibrate()
            weight_total = float(input("weight_total: "))
            print("Fluid volume per drop = " + str((weight_total-weight_tube)/100) + " ml")
            raise SystemExit
        
        elif training_phase == "allgo":
            # phase 0 is the first day of training (after habituation)
            while training_phase == "allgo":
                task.bait_reversal()
                
                if task.deliver_reward == "y":  # start allgo of training
                    behavior_phase_started = True

                    for w in range(session_info['number_of_trials']):
                        trial_ident = "go_trial"
                        logging.info(str(time.time()) + ", ##############################")
                        logging.info(str(time.time()) + ", starting trial " + str(w))
                        logging.info(str(time.time()) + ", " + trial_ident)
                        logging.info(str(time.time()) + ", ##############################")

                        task.go_trial_start()

                        #  Run trial in loop
                        while task.trial_running:
                            task.run_go()
                            ## new edits 2026.04.03, add frame sync flush                       
                            task.box.flush_frame_events()

                        task.box.flush_frame_events()
                        
                        

                        # assess trial outcome
                        trial_outcome = task.trial_outcome
                        if trial_outcome == 1:
                            combine_trial_outcome[w] = "Hit!"
                        elif trial_outcome == 2:
                            combine_trial_outcome[w] = "Miss !!!"
                        hit_count[w] = combine_trial_outcome.count("Hit!")
                        miss_count[w] = combine_trial_outcome.count("Miss !!!")
                        cr_count[w] = 0
                        fa_count[w] = 0
                        lick_times = task.lick_times
                        lick_per_trial_count[w] = len(lick_times)
                        reward_time = task.time_at_reward
                        vstimON_time = task.time_at_vstim_ON
                        logging.info(str(time.time()) + ", amount water received " + str(hit_count[w] * session_info["calibrated_drop"]))
                        
                        # Starting a new process for plotting
                        plot_dprime = False
                        plot_process = Process(target=plot_trial_progress,
                                               args=(w, trial_list, combine_trial_outcome,
                                                     hit_count, miss_count, cr_count,
                                                     fa_count, lick_times, vstimON_time, plot_dprime,
                                                     dprimebinp, lick_per_trial_count))
                        plot_process.start()  # no join because we do not want to wait until the plotting is finished

                        # Determine if Hit criterion is achieved and automatically exit
                        # if w == 0:
                        #     phase1_hit_rate = 0
                        # else:
                        #     phase1_hit_rate = (phase1_hit_count[w]) / w
                        #
                        # if w > 50 and phase1_hit_rate > session_info['hit_criterion']:
                        #     print("Hit criterion is achieved!!!")
                        #     raise SystemExit

        elif training_phase == "reversal":
            while True:
                task.deliver_reward = input("Hit enter to deliver reward, or type y then enter to start reversal:\n")
                if task.deliver_reward == "":
                    task.pump.reward("1", session_info["solenoid_blink_duration"], 0.01, 6)
                    continue
                if task.deliver_reward == "y":
                    behavior_phase_started = True
                    break

            for i in range(session_info['number_of_trials']):
                ident_random = (round(random.uniform(0, 1) * 100)) % 2

                #  Determine trial identity
                # The first 2 trials are always go_trials
                if i < 3:
                    trial_ident = "go_trial"
                    print("go_trial")
                    go_nums = go_nums + 1
                    avoid_go = avoid_go + 1
                elif avoid_go == 3:
                    trial_ident = "nogo_trial"
                    print("nogo_trial")
                    nogo_nums = nogo_nums + 1
                    avoid_go = 0
                    avoid_nogo = avoid_nogo + 1
                elif avoid_nogo == 3:
                    trial_ident = "go_trial"
                    print("go_trial")
                    go_nums = go_nums + 1
                    avoid_nogo = 0
                    avoid_go = avoid_go + 1
                elif go_nums > nogo_nums + 2:
                    trial_ident = "nogo_trial"
                    print("nogo_trial")
                    nogo_nums = nogo_nums + 1
                elif nogo_nums > go_nums + 2:
                    trial_ident = "go_trial"
                    print("go_trial")
                    go_nums = go_nums + 1
                elif ident_random == 1:
                    trial_ident = "go_trial"
                    go_nums = go_nums + 1
                    avoid_go = avoid_go + 1
                    print("go_trial")
                elif ident_random == 0:
                    trial_ident = "nogo_trial"
                    nogo_nums = nogo_nums + 1
                    avoid_nogo = avoid_nogo + 1
                    print("nogo_trial")

                #  Logging info of trial
                logging.info(str(time.time()) + ", ##############################")
                logging.info(str(time.time()) + ", starting trial " + str(i))
                logging.info(str(time.time()) + ", " + trial_ident)
                logging.info(str(time.time()) + ", ##############################")

                if trial_ident == "go_trial":
                    task.go_trial_start()
                    #  Run trial in loop
                    while task.trial_running:
                        task.run_go()
                        task.box.flush_frame_events() # new edit 2026.04.03
                    task.box.flush_frame_events()     # new edit 2026.04.03
                elif trial_ident == "nogo_trial":
                    task.nogo_trial_start()
                    while task.trial_running:
                        task.run_nogo()
                        task.box.flush_frame_events()
                    task.box.flush_frame_events()

                # get task variables from the task object
                # print to make sure that it works
                trial_outcome = task.trial_outcome

                # Covert number trial_outcome into strings
                if trial_outcome == 1:
                    combine_trial_outcome[i] = "Hit!"
                elif trial_outcome == 2:
                    combine_trial_outcome[i] = "Miss !!!"
                elif trial_outcome == 3:
                    combine_trial_outcome[i] = "CR!"
                elif trial_outcome == 4:
                    combine_trial_outcome[i] = "FA !!!"

                # Count the number of each trial outcome
                # Establish other parameters for plotting
                hit_count[i] = combine_trial_outcome.count("Hit!")
                miss_count[i] = combine_trial_outcome.count("Miss !!!")
                cr_count[i] = combine_trial_outcome.count("CR!")
                fa_count[i] = combine_trial_outcome.count("FA !!!")
                lick_times = task.lick_times
                lick_per_trial_count[i] = len(lick_times)
                reward_time = task.time_at_reward
                vstimON_time = task.time_at_vstim_ON
                logging.info(str(time.time()) + ", amount water received " + str(hit_count[i] * session_info["calibrated_drop"]))

                # Calculate dprime
                binsize = 30

                if i > (binsize-1):
                    hitbin = hit_count[i] - hit_count[i-binsize]
                    missbin = miss_count[i] - miss_count[i-binsize]
                    crs = cr_count[i] - cr_count[i-binsize]
                    fas = fa_count[i] - fa_count[i-binsize]
                    crsp = (crs/(crs+fas))*100
                    hitsp = (hitbin/(hitbin+missbin))*100
                    dhit = hitsp/100
                    dfa = (100-crsp)/100

                    if dhit == 1:
                        dhit = 0.99
                    elif dhit == 0:
                        dhit = 0.01

                    if dfa == 0:
                        dfa = 0.01
                    elif dfa == 1:
                        dfa = 0.99

                    # get the inverse of the standard normal cumulative distribution function (cdf)
                    dprimebinp[i] = norm.ppf(dhit) - norm.ppf(dfa)

                else:
                    hitp = (hit_count[i]/(hit_count[i]+miss_count[i]))*100
                    if i < 3 and trial_ident == "go_trial":
                        fap = 0
                    else:
                        fap = (fa_count[i]/(fa_count[i]+cr_count[i]))*100
                    dhit = hitp/100
                    dfa = fap/100

                    if dhit == 1:
                        dhit = 0.99
                    elif dhit == 0:
                        dhit = 0.01

                    if dfa == 0:
                        dfa = 0.01
                    elif dfa == 1:
                        dfa = 0.99

                    # get the inverse of the standard normal cumulative distribution function (cdf)
                    dprimebinp[i] = norm.ppf(dhit) - norm.ppf(dfa)

                # Starting a new process for plotting
                plot_dprime = True
                plot_process = Process(target=plot_trial_progress, args=(i, trial_list, combine_trial_outcome,
                                                                         hit_count, miss_count, cr_count, fa_count,
                                                                         lick_times, vstimON_time, plot_dprime,
                                                                         dprimebinp, lick_per_trial_count))
                plot_process.start()  # no join because we do not want to wait until the plotting is finished
                
            raise SystemExit

    # graceful exit
    except (KeyboardInterrupt, SystemExit) as exit_reason:
        print(Fore.RED + Style.BRIGHT + 'Exiting behavior phase...' + Style.RESET_ALL)

        training_phase_for_exit = session_info.get('training_phase', None)
        should_run_baseline = (
            task is not None
            and behavior_session_started
            and behavior_phase_started
            and training_phase_for_exit in {'allgo', 'reversal'}
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

        criterion_met = False
        try:
            criterion_met, _ = check_consecutive_dprime(dprimebinp)
        except Exception:
            criterion_met = False

        criterion_message = 'criterion met' if criterion_met else 'criterion not met'

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
        logging.info(criterion_message)

        # save dicts to disk
        save_session_info_files(session_info)
        pygame.quit()
