#!/usr/bin/env -S ipython3 -i

debug_enable = False

from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
import threading
import sys
import time
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

from time import sleep

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

# import your task class here
from soyoun_task import SoyounTask


def _terminate():
    print('terminating the session')
    sys.exit()


try:
    # load in session_info file, check that dates are correct, put in automatic
    # time and date stamps for when the experiment was run

    datestr = datetime.now().strftime("%Y-%m-%d")
    timestr = datetime.now().strftime('%H%M%S')
    full_module_name = 'session_info_' + datestr
    session_info_path = '/home/pi/experiment_info/headfixed_task/session_info'
    sys.path.insert(0, session_info_path)
    tempmod = importlib.import_module(full_module_name)
    session_info = tempmod.session_info
    mouse_info = tempmod.mouse_info

    session_info['date'] = datestr
    session_info['time'] = timestr
    session_info['datetime'] = session_info['date'] + '_' + session_info['time']
    session_info['basename'] = session_info['mouse_name'] + '_' + session_info['datetime']
    session_info['dir_name'] = session_info['basedir'] + "/" + session_info['basename']

    if session_info['manual_date'] != session_info['date']:  # check if file is updated
        print('wrong date!!')
        raise RuntimeError('manual_date field in session_info file is not updated')

    # make data directory and initialize logfile
    os.makedirs(session_info['dir_name'])
    os.chdir(session_info['dir_name'])
    session_info['file_basename'] = session_info['dir_name'] + '/' + session_info['basename']

    # session_info['file_basename'] = session_info['mouse_name'] + "_" + session_info['datetime']
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
        datefmt=('%H:%M:%S'),
        handlers=[
            logging.FileHandler(session_info['file_basename'] + '.log'),
            logging.StreamHandler()  # sends copy of log output to screen
        ]
    )

    # initiate task object\
    try:
        logging.info(str(time.time()) + ", trying to retrieve task_information from the ~/experiment_info/*")
        full_module_name = 'task_information_headfixed'
        import sys

        task_info_path = '/home/pi/experiment_info/headfixed_task/task_information/'
        sys.path.insert(0, task_info_path)
        tempmod = importlib.import_module(full_module_name)
        task_information = tempmod.task_information
    except:
        logging.info(str(time.time()) + ", failed to retrieve task_information from the default path.\n" +
                     "Now, try to load the task_information from the local directory ...")
        from task_information_phase_1 import task_information

        # self.task_information = task_information
    task = SoyounTask(name="headfixed_task", session_info=session_info, task_information=task_information)

    # def run_soyoun_task():
    session_length = int(input("Enter the duration of session (in seconds): "))
    terminate_timer = threading.Timer(session_length, _terminate)
    while True:
        terminate_timer.start()
        task.start_session()
        scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info': session_info})
        pickle.dump(session_info, open(session_info['file_basename'] + '_session_info.pkl', "wb"))

        block_deck = task.generate_deck(current_block, block_duration, consecutive control)

    raise SystemExit

# graceful exit
except (KeyboardInterrupt, SystemExit):
    print(Fore.RED + Style.BRIGHT + 'Exiting now...' + Style.RESET_ALL)
    ic('about to call end_session()')
    task.end_session()
    ic('just called end_session()')
    # save dicts to disk
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info': session_info})
    pickle.dump(session_info, open(session_info['file_basename'] + '_session_info.pkl', "wb"))
    pygame.quit()

# # exit because of error
# except (RuntimeError) as ex:
#     print(Fore.RED + Style.BRIGHT + 'ERROR: Exiting now' + Style.RESET_ALL)
#     # save dicts to disk
#     scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info' : session_info})
#     pickle.dump( session_info, open( session_info['file_basename'] + '_session_info.pkl', "wb" ) )
