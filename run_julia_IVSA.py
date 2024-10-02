#!/usr/bin/env python
# coding: utf-8

#run_julia_task_self_admin.py

#!/usr/bin/env -S ipython3 -i
# run_julia_task_self_admin.py
"""
author: Julia Benville
date: 2024-09-26
name: run_julia_task_self_admin.py
"""

import random
from transitions import Machine
from transitions import State
from icecream import ic
import logging
from datetime import datetime
import os
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
from time import sleep

debug_enable = False

# All modules above this line will have logging disabled
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
})

if debug_enable:
    # Enabling debugger
    from IPython import get_ipython
    ipython = get_ipython()
    ipython.magic("pdb on")
    ipython.magic("xmode Verbose")

# Import your task class here
import julia_DCL_self_admin
from julia_DCL_self_admin import CocaineSelfAdminLeverTask

try:
    # Load in session_info file, check that dates are correct, put in automatic
    # time and date stamps for when the experiment was run

    datestr = datetime.now().strftime("%Y-%m-%d")
    timestr = datetime.now().strftime('%H%M%S')
    full_module_name = 'session_info_' + datestr
    import sys

    # Update file paths to match your setup
    session_info_path = '/home/pi/experiment_info/julia_DCL_self_admin/session_info/'
    sys.path.insert(0, session_info_path)
    tempmod = importlib.import_module(full_module_name)
    session_info = tempmod.session_info
    mouse_info = tempmod.mouse_info

    session_info['date'] = datestr
    session_info['time'] = timestr
    session_info['datetime'] = session_info['date'] + '_' + session_info['time']
    session_info['basename'] = session_info['mouse_name'] + '_' + session_info['datetime']
    session_info['dir_name'] = session_info['basedir'] + "/" + session_info['basename']

    if session_info['manual_date'] != session_info['date']:  # Check if file is updated
        print('wrong date!!')
        raise RuntimeError('manual_date field in session_info file is not updated')

    # Make data directory and initialize logfile
    os.makedirs(session_info['dir_name'])
    os.chdir(session_info['dir_name'])
    session_info['file_basename'] = session_info['dir_name'] + '/' + session_info['basename']

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
        datefmt=('%H:%M:%S'),
        handlers=[
            logging.FileHandler(session_info['file_basename'] + '.log'),
            logging.StreamHandler()  # Sends copy of log output to screen
        ]
    )

    # Initialize task
    task = CocaineSelfAdminLeverTask(name="julia_DCL_self_admin", session_info=session_info)

    # Start session
    task.start_session()
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info': session_info})
    pickle.dump(session_info, open(session_info['file_basename'] + '_session_info.pkl', "wb"))
    sleep(10)

    # Loop over trials
    # Set a timer for the experiment duration
    t_minute = int(input("Enter the time in minutes: "))
    t_end = time.time() + 60 * t_minute

    i = True
    task.start_trial_logic()
    while i:
        if t_end < time.time():
            i = False
            task.end_task()
            print("Times up, finishing up")
        while task.trial_running and t_end < time.time():  # Trial running in both standby and reward_available
            task.run()  # This breaks out of the loop during transitions between blocks
                        # and permits checking the t_end clock in this loop
    raise SystemExit

# Graceful exit
except (KeyboardInterrupt, SystemExit):
    print(Fore.RED + Style.BRIGHT + 'Exiting now...' + Style.RESET_ALL)
    ic('about to call end_session()')
    task.end_session()
    ic('just called end_session()')
    # Save session information to disk
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info': session_info})
    pickle.dump(session_info, open(session_info['file_basename'] + '_session_info.pkl', "wb"))
    pygame.quit()

# Exit due to error
except RuntimeError as ex:
    print(Fore.RED + Style.BRIGHT + 'ERROR: Exiting now' + Style.RESET_ALL)
    # Save session information to disk in case of an error
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info': session_info})
    pickle.dump(session_info, open(session_info['file_basename'] + '_session_info.pkl', "wb"))
    task.end_session()
