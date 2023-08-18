#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#run_choice_motivation_task.task

#!/usr/bin/env -S ipython3 -i
# run_choice_motivation_task.py
"""
author: Mitch Farrell
date: 2023-08-18
name: run_choice_motivation_task.py
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
from choice_motivation_task import ChoiceMotivationTask

try:
    # load in session_info file, check that dates are correct, put in automatic
    # time and date stamps for when the experiment was run

    datestr = datetime.now().strftime("%Y-%m-%d")
    timestr = datetime.now().strftime('%H%M%S')
    full_module_name = 'session_info_' + datestr
    import sys

    session_info_path = '/home/pi/experiment_info/choice_motivation_task/session_info/'
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

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
        datefmt=('%H:%M:%S'),
        handlers=[
            logging.FileHandler(session_info['file_basename'] + '.log'),
            logging.StreamHandler()  # sends copy of log output to screen
        ]
    )

    task = ChoiceMotivationTask(name="choice_motivation_task", session_info=session_info)

    # start session
    task.start_session()
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info': session_info})
    pickle.dump(session_info, open(session_info['file_basename'] + '_session_info.pkl', "wb"))
    sleep(10)
    # loop over trials
    # Set a timer
    t_minute = int(input("Enter the time in minutes: "))
    t_end = time.time() + 60 * t_minute

    i = True
    task.start_trial_logic()
    while i:
        if time.time() >= t_end:
            i = False
            print("Times up, finishing up")
            task.end_task()
        while task.trial_running: #trial running in both standby and reward_available
            if time.time() < t_end:
                task.run() #breaks out of this while loop during transitions between blocks; this will permit checking the t_end clock in this loop
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

# exit because of error
except RuntimeError as ex:
    print(Fore.RED + Style.BRIGHT + 'ERROR: Exiting now' + Style.RESET_ALL)
    # save dicts to disk
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info': session_info})
    pickle.dump(session_info, open(session_info['file_basename'] + '_session_info.pkl', "wb"))
    task.end_session()

