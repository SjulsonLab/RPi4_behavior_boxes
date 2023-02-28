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
from go_nogo_task import go_nogo_phase0

# define the plotting function here
def plot_trial_progress(current_trial, trial_list, combine_trial_outcome, hit_count, miss_count,lick_times):
    ########################################################################
    # initialize the figure
    ########################################################################
    fig = plt.figure(figsize=(14, 9))
    ax1 = fig.add_subplot(231)  # outcome
    ax2 = fig.add_subplot(212)  # eventplot
    ax3 = fig.add_subplot(232)
    ax4 = fig.add_subplot(233)

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
    plot_period = 17

    # set different colors for each set of positions
    colors1 = ['C{}'.format(c) for c in range(2)]
    # set different line properties for each set of positions
    lineoffsets1 = np.array([3, 2])
    linelengths1 = [0.8, 0.8]
    ax2.eventplot(events_to_plot, colors=colors1, lineoffsets=lineoffsets1, linelengths=linelengths1)
    ax2.set_xlim([-0.5, plot_period])
    ax2.set_xlabel('Time since trial start (s)', fontsize=9)
    ax2.set_yticks((2, 3))
    ax2.set_yticklabels(('reward', 'lick'))

    ########################################################################
    # create cumulative outcome plot
    ########################################################################
    # Get data to plot for current trial
    outcome_xvalue = np.linspace(0, current_trial, num=current_trial + 1)
    outcome_hit_count_yvalue = hit_count[0:current_trial + 1]
    outcome_miss_count_yvalue = miss_count[0:current_trial + 1]

    # Plot
    ax3.plot(outcome_xvalue, outcome_hit_count_yvalue, 'r-')
    ax3.lines[-1].set_label('Hit')
    ax3.plot(outcome_xvalue, outcome_miss_count_yvalue, 'b-')
    ax3.lines[-1].set_label('Miss')

    ax3.set_title('Cummulative outcome', fontsize=11)
    ax3.set_xlim([0, current_trial + 1])
    ax3.set_xlabel('Current trial', fontsize=9)
    ax3.set_ylabel('Number of trials', fontsize=9)
    ax3.legend()

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
    time.sleep(4)  # sleep for 3 seconds for pygame to remain displayed
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
        animal_ID = input("Enter animal ID (ex DT000):\n")
        session_info['mouse_name'] = animal_ID
        animal_weight = input("Enter animal weight (ex 19.5):\n")
        session_info['weight'] = animal_weight
        session_info['training_phase'] = "phase0"
        training_phase = session_info['training_phase']

        session_info['date'] = datestr
        session_info['time'] = timestr
        session_info['datetime'] = session_info['date'] + '_' + session_info['time']
        session_info['basename'] = session_info['mouse_name'] + '_' + session_info['datetime']
        session_info['dir_name'] = session_info['basedir'] + "/" + session_info['mouse_name'] + "_" + session_info['datetime']

        if session_info['manual_date'] != session_info['date']:  # check if file is updated
            print('wrong date!!')
            raise RuntimeError('Manual_date field in session_info file is not updated')

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
        task = go_nogo_phase0(name="go_nogo_phase0", session_info=session_info)
        phase0_trial_list = list(range(0, session_info["number_of_phase0_trials"]))
        phase0_trial_outcome = ["" for o in range(session_info['number_of_phase0_trials'])]
        phase0_hit_count = [0 for o in range(session_info['number_of_phase0_trials'])]
        phase0_miss_count = [0 for o in range(session_info['number_of_phase0_trials'])]

        # Start session
        task.start_session()
        scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info' : session_info})
        pickle.dump(session_info, open( session_info['file_basename'] + '_session_info.pkl', "wb" ) )

        if training_phase == "phase0":
            # phase 0 is the first day of training (random reward phase, after habituation)
            while training_phase == "phase0":
                task.bait_phase0()
                if task.deliver_reward == "":  # start phase0 of training
                    for w in range(session_info['number_of_phase0_trials']):
                        logging.info(str(time.time()) + ", ##############################")
                        logging.info(str(time.time()) + ", starting trial " + str(w))
                        logging.info(str(time.time()) + ", ##############################")

                        task.start_random_reward()

                        #  Run trial in loop
                        while task.trial_running:
                            task.run_random_reward()

                        # assess trial outcome
                        trial_outcome = task.trial_outcome
                        phase0_trial_outcome[w] = trial_outcome
                        if trial_outcome == 1:
                            phase0_trial_outcome[w] = "Hit!"
                        elif trial_outcome == 2:
                            phase0_trial_outcome[w] = "Miss !!!"
                        phase0_hit_count[w] = phase0_trial_outcome.count("Hit!")
                        phase0_miss_count[w] = phase0_trial_outcome.count("Miss !!!")
                        lick_times = task.lick_times
                        reward_time = task.time_at_reward

                        # Starting a new process for plotting
                        plot_process = Process(target=plot_trial_progress,
                                               args=(w, phase0_trial_list, phase0_trial_outcome,
                                                     phase0_hit_count, phase0_miss_count, lick_times))
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

