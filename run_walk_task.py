#run_self_admin.task

#!/usr/bin/env -S ipython3 -i
# run_self_admin_task.py
"""
author: tian qiu
date: 2023-01-25
name: run_walk_task.py
goal: a simplified headfixed task
description:
    adapted from Mitch's run_self_admin_task.py

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
from walk_task import WalkTask

try:
    # load in session_info file, check that dates are correct, put in automatic
    # time and date stamps for when the experiment was run

    datestr = datetime.now().strftime("%Y-%m-%d")
    timestr = datetime.now().strftime('%H%M%S')
    full_module_name = 'session_info_' + datestr
    import sys

    session_info_path = '/home/pi/experiment_info/walk_task/session_info'
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


    task = WalkTask(name="walk_task", session_info=session_info)

    # # you can change various parameters if you want
    # task.machine.states['cue'].timeout = 2

    # start session
    task.start_session()
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info': session_info})
    pickle.dump(session_info, open(session_info['file_basename'] + '_session_info.pkl', "wb"))
    sleep(10)
    # loop over trials
    # Set a timer
    t_minute = int(input("Enter the time in minutes: "))
    t_end = time.time() + 60 * t_minute

    while time.time() < t_end:
        # session_info["block_duration"] indicate how many successful trials
        # does it take to the session to finish
        # first_card = True
        task.error_count = 0
        random_cue = random.randint(0,1)
        if random_cue:
            task.current_cue = "left"
        else:
            task.current_cue = "right"

        print("*******************************\n")
        print("Trial " + str(task.trial_number) + "; Side" + task.current_cue + "\n")
        task.trial_number += 1
        print("*******************************\n")

        logging.info(";" + str(time.time()) + ";[condition];" + str(task.current_cue) + "_LED")
        while task.innocent or (session_info["error_repeat"] and task.error_repeat and task.error_count < session_info[
            "error_max"]):
            if time.time() >= t_end:
                print("Times up, finishing up")
                break
            if not task.innocent:
                task.innocent = True
            if task.error_repeat:
                task.error_repeat = False
                print("punishment_time_out: " + str(session_info["punishment_timeout"]))
                sleep(session_info["punishment_timeout"])
                task.trial_number += 1
            # first_card = False
            logging.info(";" + str(time.time()) + ";[transition];start_trial()")
            task.start_trial()  # initiate the time state machine, start_trial() is a trigger
            while task.trial_running:
                task.run()  # run command trigger additional functions outside of the state machine
            print("error_count: " + str(task.error_count))
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
