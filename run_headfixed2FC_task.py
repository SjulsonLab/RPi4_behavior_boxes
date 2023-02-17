#!/usr/bin/env -S ipython3 -i
# run_headfixed_task.py
"""
author: tian qiu & Soyoun Kim
date: 2023-02-16
name: run_headfixed2FC_task.py
goal: model_free reinforcement learning behavioral training run task file
description:
    an updated test version of run_headfixed_task.py

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
from headfixed2FC_task import Headfixed2FCTask

try:
    # load in session_info file, check that dates are correct, put in automatic
    # time and date stamps for when the experiment was run

    datestr = datetime.now().strftime("%Y-%m-%d")
    timestr = datetime.now().strftime('%H%M%S')
    full_module_name = 'session_info_' + datestr
    import sys

    session_info_path = '/home/pi/experiment_info/headfixed2FC_task/session_info'
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

    from task_information_headfixed2FC import TaskInformation

    task_information = TaskInformation()
    # print("Imported task_information_headfixed: " + str(task_information.name))

    task = Headfixed2FCTask(name="headfixed2FC_task", session_info=session_info)

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
    block_count = 0 ## can be replaced with task.block_count
    while time.time() < t_end:
        if block_count==0:
            block_number = session_info["block_number"] #random.randint(1, session_info["block_variety"])
        else:
            block_number = 3-block_number
            block_count = block_count+1
            #task.block_number = block_number

        if ((block_number != 1 ) || (block_number != 2) ):
            print('check_block number!!!!')
            block_number = 1

        for block in range(session_info["block_duration"]):
            if time.time() >= t_end:
                print("Times up, finishing up")
                break
            first_card = True
            task.error_count = 0
            print("Trial " + str(block) + " \n")
            task.trial_number += 1
            print("*******************************\n")
            task.current_card = task_information.draw_card(block_number, session_info['phase'])
            logging.info(";" + str(time.time()) + ";[condition];" + str(task.current_card))
            print("Block " + str(block_number) +
                  " - Current card condition: \n" +
                  "*******************************\n" +
                  "*Cue: " + str(task.current_card[0]) + "\n" +
                  "*Choice: " + str(task.current_card[1]) + "\n" +
                  "*Reward: " + str(task.current_card[2]) + "\n")
            while first_card or (session_info["error_repeat"] and task.error_repeat and task.error_count < session_info[
                "error_max"]):
                if time.time() >= t_end:
                    print("Times up, finishing up")
                    break
                if task.error_repeat:
                    task.error_repeat = False
                    print("punishment_time_out: " + str(session_info["punishment_timeout"]))
                    sleep(session_info["punishment_timeout"])
                    print("*error_repeat trial* \n" + "Block " + str(block_number) +
                          " - Current card condition: \n" +
                          "*******************************\n" +
                          "*Cue: " + str(task.current_card[0]) + "\n" +
                          #"*State: " + str(task.current_card[1]) + "\n" +
                          "*Choice: " + str(task.current_card[1]) + "\n" +
                          "*Reward: " + str(task.current_card[2]) + "\n")
                    task.trial_number += 1
                first_card = False
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
