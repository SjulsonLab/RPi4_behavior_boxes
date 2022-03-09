debug_enable = False

from icecream import ic
from datetime import datetime
import os
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
from go_nogo_v2 import go_nogo_task

# define the plotting function here
def plot_trial_progress(current_trial, trial_list, combine_trial_outcome, hit_count, miss_count,
                        cr_count, fa_count, lick_times, vstimON_time, plot_dprime, dprimebinp):
    ########################################################################
    # initialize the figure
    ########################################################################
    fig = plt.figure(figsize=(11, 7))
    ax1 = fig.add_subplot(231)  # outcome
    ax2 = fig.add_subplot(212)  # eventplot
    ax3 = fig.add_subplot(232)
    ax4 = fig.add_subplot(233)

    ########################################################################
    # create an outcome plot
    ########################################################################
    if current_trial < 15:
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
            f"trial {trial_list[14]} : {combine_trial_outcome[14]}",
            f"percent hit : {(hit_count[current_trial]/(hit_count[current_trial] + miss_count[current_trial]))}",
            f" "))

    elif current_trial >= 15:
        textstr = '\n'.join((
            f"trial {trial_list[0 + (current_trial - 14)]} : {combine_trial_outcome[0 + (current_trial - 14)]}",
            f"trial {trial_list[1 + (current_trial - 14)]} : {combine_trial_outcome[1 + (current_trial - 14)]}",
            f"trial {trial_list[2 + (current_trial - 14)]} : {combine_trial_outcome[2 + (current_trial - 14)]}",
            f"trial {trial_list[3 + (current_trial - 14)]} : {combine_trial_outcome[3 + (current_trial - 14)]}",
            f"trial {trial_list[4 + (current_trial - 14)]} : {combine_trial_outcome[4 + (current_trial - 14)]}",
            f"trial {trial_list[5 + (current_trial - 14)]} : {combine_trial_outcome[5 + (current_trial - 14)]}",
            f"trial {trial_list[6 + (current_trial - 14)]} : {combine_trial_outcome[6 + (current_trial - 14)]}",
            f"trial {trial_list[7 + (current_trial - 14)]} : {combine_trial_outcome[7 + (current_trial - 14)]}",
            f"trial {trial_list[8 + (current_trial - 14)]} : {combine_trial_outcome[8 + (current_trial - 14)]}",
            f"trial {trial_list[9 + (current_trial - 14)]} : {combine_trial_outcome[9 + (current_trial - 14)]}",
            f"trial {trial_list[10 + (current_trial - 14)]} : {combine_trial_outcome[10 + (current_trial - 14)]}",
            f"trial {trial_list[11 + (current_trial - 14)]} : {combine_trial_outcome[11 + (current_trial - 14)]}",
            f"trial {trial_list[12 + (current_trial - 14)]} : {combine_trial_outcome[12 + (current_trial - 14)]}",
            f"trial {trial_list[13 + (current_trial - 14)]} : {combine_trial_outcome[13 + (current_trial - 14)]}",
            f"trial {trial_list[14 + (current_trial - 14)]} : {combine_trial_outcome[14 + (current_trial - 14)]}",
            f"percent hit : {(hit_count[current_trial] / (hit_count[current_trial] + miss_count[current_trial]))}",
            f" "))

    ax1.set_title('Trial Outcome', fontsize=11)
    ax1.text(0.05, 0.95, textstr, fontsize=9, verticalalignment='top')
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
        plot_period = 11.5  # in seconds, how long to plot since the start of trial
        plot_bin_number = 1150
    else:
        plot_period = 8
        plot_bin_number = 800

    # create vstim time data
    vstim_duration = 4  # in seconds, pre-generated
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
    ax2.set_xlim([-0.5, 8.5])  # 8s total to show (trial duration)
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

    ########################################################################
    # create the d' figure
    ########################################################################

    if plot_dprime == True:
        ax4_x_values = np.linspace(0, current_trial, num=current_trial + 1)
        ax4_y_values = dprimebinp[0:current_trial+1]
        ax4.plot(ax4_x_values, ax4_y_values, 'r-')
        ax4.set_title('D-prime', fontsize=11)
        ax4.set_xlim([0, current_trial + 1])
        ax4.set_xlabel('Current trial', fontsize=9)

    ########################################################################
    # draw on canvas to display via pygame
    ########################################################################
    canvas = agg.FigureCanvasAgg(fig)
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()
    pygame.init()
    window = pygame.display.set_mode((1100, 700), DOUBLEBUF)
    screen = pygame.display.get_surface()
    size = canvas.get_width_height()
    surf = pygame.image.fromstring(raw_data, size, "RGB")
    screen.blit(surf, (0, 0))
    pygame.display.flip()
    plt.close(fig)
    time.sleep(3)  # sleep for 3 seconds for pygame to remain displayed
    pygame.quit()


if __name__ == "__main__":
    try:
        # load in session_info file, check that dates are correct, put in automatic
        # time and date stamps for when the experiment was run
        datestr = datetime.now().strftime("%Y-%m-%d")
        timestr = datetime.now().strftime('%H%M%S')
        full_module_name = 'go_nogo_session_info_' + datestr
        import sys
        task_info_path = '/home/pi/experiment_info/go_nogo_task/session_info'
        sys.path.insert(0, task_info_path)
        tempmod = importlib.import_module(full_module_name)
        session_info = tempmod.session_info
        mouse_info = tempmod.mouse_info

        # ask user for task parameters
        training_date_time = input("Enter date (ex 2022-11-22):\n")
        session_info['manual_date'] = training_date_time
        animal_ID = input("Enter animal ID (ex DT000):\n")
        session_info['mouse_name'] = animal_ID
        animal_weight = input("Enter animal weight (ex 19.5):\n")
        session_info['weight'] = animal_weight
        training_phase = input("Enter training phase (ex phase1):\n")
        session_info['training_phase'] = training_phase

        session_info['date'] = datestr
        session_info['time'] = timestr
        session_info['datetime'] = session_info['date'] + '_' + session_info['time']
        session_info['basename'] = session_info['mouse_name'] + '_' + session_info['datetime']
        session_info['dir_name'] = session_info['basedir'] + "/" + session_info['mouse_name'] + "_" + session_info['datetime']

        if session_info['manual_date'] != session_info['date']:  # check if file is updated
            print('wrong date!!')
            raise RuntimeError('manual_date field in session_info file is not updated')

        # make data directory and initialize logfile
        os.makedirs( session_info['dir_name'] )
        os.chdir( session_info['dir_name'] )
        session_info['file_basename'] = session_info['mouse_name'] + "_" + training_phase + "_" + session_info['datetime']
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
            datefmt=('%H:%M:%S'),
            handlers=[
                logging.FileHandler(session_info['file_basename'] + '.log'),
                logging.StreamHandler() # sends copy of log output to screen
            ]
        )

        # initiate task object
        task = go_nogo_task(name="go_nogo_task", session_info=session_info)
        trial_list = list(range(0, session_info["number_of_trials"]))
        combine_trial_outcome = ["" for o in range(session_info["number_of_trials"])]
        hit_count = [0 for o in range(session_info["number_of_trials"])]
        miss_count = [0 for o in range(session_info["number_of_trials"])]
        cr_count = [0 for o in range(session_info["number_of_trials"])]
        fa_count = [0 for o in range(session_info["number_of_trials"])]
        dprimebinp = [0 for o in range(session_info["number_of_trials"])]

        phase1_trial_list = list(range(0, session_info["number_of_phase1_trials"]))
        phase1_trial_outcome = ["" for o in range(session_info['number_of_phase1_trials'])]
        phase1_hit_count = [0 for o in range(session_info['number_of_phase1_trials'])]
        phase1_miss_count = [0 for o in range(session_info['number_of_phase1_trials'])]
        phase1_cr_count = [0 for o in range(session_info['number_of_phase1_trials'])]
        phase1_fa_count = [0 for o in range(session_info['number_of_phase1_trials'])]

        # start session
        task.start_session()
        scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info' : session_info})
        pickle.dump(session_info, open( session_info['file_basename'] + '_session_info.pkl', "wb" ) )

        # Loops over trials for phase 2 training
        avoid_go = 0
        avoid_nogo = 0
        go_nums = 0
        nogo_nums = 0

        if training_phase == "phase0":
            # phase 0 is the first day of training (after habituation)
            while training_phase == "phase0":
                task.bait_phase0()
                if task.deliver_reward == "p":  # start phase1 of training
                    for w in range(session_info['number_of_phase1_trials']):
                        trial_ident = "go_trial"
                        logging.info(str(time.time()) + ", ##############################")
                        logging.info(str(time.time()) + ", starting trial " + str(w))
                        logging.info(str(time.time()) + ", " + trial_ident)
                        logging.info(str(time.time()) + ", ##############################")

                        task.go_trial_start()

                        #  Run trial in loop
                        while task.trial_running:
                            task.run_go()

                        # assess trial outcome
                        trial_outcome = task.trial_outcome
                        phase1_trial_outcome[w] = trial_outcome
                        if trial_outcome == 1:
                            phase1_trial_outcome[w] = "Hit!"
                        elif trial_outcome == 2:
                            phase1_trial_outcome[w] = "Miss !!!"
                        phase1_hit_count[w] = phase1_trial_outcome.count("Hit!")
                        phase1_miss_count[w] = phase1_trial_outcome.count("Miss !!!")
                        phase1_cr_count[w] = 0
                        phase1_fa_count[w] = 0
                        lick_times = task.lick_times
                        reward_time = task.time_at_reward
                        vstimON_time = task.time_at_vstim_ON

                        # Starting a new process for plotting
                        plot_dprime = False
                        plot_process = Process(target=plot_trial_progress,
                                               args=(w, phase1_trial_list, phase1_trial_outcome,
                                                     phase1_hit_count, phase1_miss_count, phase1_cr_count,
                                                     phase1_fa_count, lick_times, vstimON_time, plot_dprime,
                                                     dprimebinp))
                        plot_process.start()  # no join because we do not want to wait until the plotting is finished

                        # Determine if Hit criterion is achieved and automatically exit
                        if w == 0:
                            phase1_hit_rate = 0
                        else:
                            phase1_hit_rate = (phase1_hit_count[w]) / w

                        if w > 50 and phase1_hit_rate > session_info['hit_criterion']:
                            print("Hit criterion is achieved!!!")
                            raise SystemExit

        elif training_phase == "phase1":
            # phase 1 of training is all go trials
            # print if hit_criterion is achieved
            for w in range(session_info['number_of_phase1_trials']):
                trial_ident = "go_trial"
                logging.info(str(time.time()) + ", ##############################")
                logging.info(str(time.time()) + ", starting trial " + str(w))
                logging.info(str(time.time()) + ", " + trial_ident)
                logging.info(str(time.time()) + ", ##############################")

                task.go_trial_start()

                #  Run trial in loop
                while task.trial_running:
                    task.run_go()

                # assess trial outcome
                trial_outcome = task.trial_outcome
                phase1_trial_outcome[w] = trial_outcome
                if trial_outcome == 1:
                    phase1_trial_outcome[w] = "Hit!"
                elif trial_outcome == 2:
                    phase1_trial_outcome[w] = "Miss !!!"
                phase1_hit_count[w] = phase1_trial_outcome.count("Hit!")
                phase1_miss_count[w] = phase1_trial_outcome.count("Miss !!!")
                phase1_cr_count[w] = 0
                phase1_fa_count[w] = 0
                lick_times = task.lick_times
                reward_time = task.time_at_reward
                vstimON_time = task.time_at_vstim_ON

                # Starting a new process for plotting
                plot_dprime = False
                plot_process = Process(target=plot_trial_progress, args=(w, phase1_trial_list, phase1_trial_outcome,
                                                                         phase1_hit_count, phase1_miss_count, phase1_cr_count,
                                                                         phase1_fa_count, lick_times, vstimON_time, plot_dprime,
                                                                         dprimebinp))
                plot_process.start()  # no join because we do not want to wait until the plotting is finished

                # Determine if Hit criterion is achieved and automatically exit
                if w == 0:
                    phase1_hit_rate = 0
                else:
                    phase1_hit_rate = (phase1_hit_count[w])/w

                if w > 50 and phase1_hit_rate > session_info['hit_criterion']:
                    print("Hit criterion is achieved!!!")
                    raise SystemExit

        elif training_phase == "phase2":
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
                elif trial_ident == "nogo_trial":
                    task.nogo_trial_start()
                    while task.trial_running:
                        task.run_nogo()

                # get task variables from the task object
                # print to make sure that it works
                trial_outcome = task.trial_outcome
                print(trial_outcome)

                # Covert number trial_outcome into strings
                if trial_outcome == 1:
                    combine_trial_outcome[i] = "Hit!"
                elif trial_outcome == 2:
                    combine_trial_outcome[i] = "Miss !!!"
                elif trial_outcome == 3:
                    combine_trial_outcome[i] = "CR!"
                elif trial_outcome == 4:
                    combine_trial_outcome[i] = "FA !!!"
                print(combine_trial_outcome[i])

                # Count the number of each trial outcome
                # Establish other parameters for plotting
                hit_count[i] = combine_trial_outcome.count("Hit!")
                miss_count[i] = combine_trial_outcome.count("Miss !!!")
                cr_count[i] = combine_trial_outcome.count("CR!")
                fa_count[i] = combine_trial_outcome.count("FA !!!")
                lick_times = task.lick_times
                reward_time = task.time_at_reward
                vstimON_time = task.time_at_vstim_ON

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
                                                                         dprimebinp,))
                plot_process.start()  # no join because we do not want to wait until the plotting is finished

            raise SystemExit

    # graceful exit
    except (KeyboardInterrupt, SystemExit):
        print(Fore.RED + Style.BRIGHT + 'Exiting now...' + Style.RESET_ALL)
        ic('about to call end_session()')
        task.end_session()
        ic('just called end_session()')
        # save dicts to disk
        scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info' : session_info})
        pickle.dump( session_info, open( session_info['file_basename'] + '_session_info.pkl', "wb" ) )
        pygame.quit()

