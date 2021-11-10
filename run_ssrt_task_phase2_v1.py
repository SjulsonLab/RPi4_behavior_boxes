debug_enable = False

from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
from icecream import ic
import logging
from datetime import datetime
import os
from gpiozero import PWMLED, LED, Button
import logging.config
import pysistence, collections
import socket
import importlib
import colorama
import warnings
import scipy.io, pickle
import pygame
from colorama import Fore, Style
import time
import timeit
import numpy as np
import random


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

# import the SSRT task class here
from ssrt_task_phase2_v1 import ssrt_task

try:
    # load in session_info file, check that dates are correct, put in automatic
    # time and date stamps for when the experiment was run
    datestr = datetime.now().strftime("%Y-%m-%d")
    timestr = datetime.now().strftime('%H%M%S')
    full_module_name = 'ssrt_session_info_' + datestr
    import sys
    task_info_path = '/home/pi/experiment_info/ssrt_task/session_info'
    sys.path.insert(0, task_info_path)
    tempmod = importlib.import_module(full_module_name)
    session_info = tempmod.session_info
    mouse_info = tempmod.mouse_info

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
    session_info['file_basename'] = session_info['mouse_name'] + "_" + session_info['datetime']
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
    task = ssrt_task(name="phase2_ssrt_training", session_info=session_info)
    # we can change various parameters if needed
    # task.machine.states['initiation'].timeout = 2

    # start session
    task.start_session()
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info' : session_info})
    pickle.dump(session_info, open( session_info['file_basename'] + '_session_info.pkl', "wb" ) )

    # Loops over trials for phase 2 training
    avoid_go = 0
    avoid_stop_signal = 0
    go_nums = 0
    stop_signal_nums = 0

    for i in range(session_info['number_of_trials']):
        ident_random = (round(random.uniform(0, 1) * 100)) % 2

        #  Determine trial identity
        if i < 2:
            trial_ident = "go_trial"
            print("go_trial")
            go_nums = go_nums + 1
            avoid_go = avoid_go + 1
        elif avoid_go == 3:
            trial_ident = "stop_signal_trial"
            print("stop_signal_trial")
            stop_signal_nums = stop_signal_nums + 1
            avoid_go = 0
            avoid_stop_signal = avoid_stop_signal + 1
        elif avoid_stop_signal == 3:
            trial_ident = "go_trial"
            print("go_trial")
            go_nums = go_nums + 1
            avoid_stop_signal = 0
            avoid_go = avoid_go + 1
        elif go_nums > stop_signal_nums + 2:
            trial_ident = "stop_signal_trial"
            print("stop_signal_trial")
            stop_signal_nums = stop_signal_nums + 1
        elif stop_signal_nums > go_nums + 2:
            trial_ident = "go_trial"
            print("go_trial")
            go_nums = go_nums + 1
        elif ident_random == 1:
            trial_ident = "go_trial"
            go_nums = go_nums + 1
            avoid_go = avoid_go + 1
            print("go_trial")
        elif ident_random == 0:
            trial_ident = "stop_signal_trial"
            stop_signal_nums = stop_signal_nums + 1
            avoid_stop_signal = avoid_stop_signal + 1
            print("stop_signal_trial")

        #  Logging info of trial
        logging.info(str("##############################\n" +
                     str(time.time())) + ", starting_trial, " + str(i) +
                     str("\n##############################"))
        task.trial_start()

        #  Run trial in loop
        while task.trial_running:
            if trial_ident == "go_trial":
                task.run_go_trial()
                start_t = time.time()
                task.plot_ssrt_phase2(i)
                end_t = time.time()
                print('Elapsed time for plotting (in seconds) = ' + str(end_t - start_t))
            else:
                task.run_stop_signal_trial()
                start_t = time.time()
                task.plot_ssrt_phase2(i)
                end_t = time.time()
                print('Elapsed time for plotting (in seconds) = ' + str(end_t - start_t))
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
