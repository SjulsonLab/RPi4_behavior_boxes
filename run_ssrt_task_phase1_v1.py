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
from matplotlib import pyplot as plt
import matplotlib.animation as animation


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
from ssrt_task_phase1_v1 import ssrt_task

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
    task = ssrt_task(name="phase1_ssrt_training", session_info=session_info)
    # we can change various parameters if needed
    # task.machine.states['initiation'].timeout = 2

    # start session
    task.start_session()
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info' : session_info})
    pickle.dump(session_info, open( session_info['file_basename'] + '_session_info.pkl', "wb" ) )

    # Plot animation
    task.plot_animation()

    # Whether to run bait or not
    what_to_run = input("What is the task: bait or phase1?:\n")
    print(f'You entered {what_to_run}')

    while what_to_run == "bait":
        task.bait()
        if task.value == "stop":
            break

    if what_to_run == "phase1":
        # Loops over trials for phase 1 training
        for i in range(2):
            logging.info(str("##############################\n" +
                         str(time.time())) + ", starting_trial, " + str(i) +
                         str("\n##############################"))
            task.trial_start()

            while task.trial_running:
                task.run()
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
