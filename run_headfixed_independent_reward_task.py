#!/usr/bin/env -S ipython3 -i
# run_headfixed2FC_task.py
"""
author: tian qiu & Soyoun Kim
date: 2023-02-16
name: run_headfixed2FC_task.py
goal: model_free reinforcement learning behavioral training run task file
description:
    an updated test version of run_headfixed_task.py

"""
import random
import numpy as np
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
from headfixed_independent_reward_task import HeadfixedIndependentRewardTask

try:
    # load in session_info file, check that dates are correct, put in automatic
    # time and date stamps for when the experiment was run

    datestr = datetime.now().strftime("%Y-%m-%d")
    timestr = datetime.now().strftime('%H%M%S')
    full_module_name = 'session_info_' + datestr
    import sys

    session_info_path = '/home/pi/experiment_info/headfixed_independent_reward_task/session_info'
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

    from task_information_independent_reward import TaskInformation
    task_information = TaskInformation()
    # print("Imported task_information_headfixed: " + str(task_information.name))
    task = HeadfixedIndependentRewardTask(name="headfixed_independent_reward_task", session_info=session_info)


    def cumsum_positive(input_list):
        for index in range(len(input_list)):
            if index == 0 and input_list[index] < 0:
                input_list[index] = -input_list[index]
            elif input_list[index] + input_list[index - 1] < 0:
                input_list[index] = input_list[index] - input_list[index - 1]
            else:
                input_list[index] = input_list[index] + input_list[index - 1]
        return input_list

    def generate_reward_trajectory(scale=0.5, offset=3.0, change_point=20, ntrials=200):
        # initial reward (need to be random)
        rewards_L = [1]
        rewards_R = [1]
        for a in np.arange(np.round(ntrials / change_point)):
            temp = np.random.randn(change_point) * scale
            rewards_L.append(cumsum_positive(temp) + offset)
            temp = np.random.randn(change_point) * scale
            rewards_R.append(cumsum_positive(temp) + offset)
        rewards_L = np.hstack(rewards_L)
        rewards_R = np.hstack(rewards_R)
        # plt.plot(rewards_L,'b');plt.plot(rewards_R,'r--')
        reward_LR = [rewards_L, rewards_R]
        reward_LR = np.transpose(np.array(reward_LR))
        reward_LR = reward_LR[0:ntrials, :]
        # print(reward_LR)
        return reward_LR

    # from reward_distribution import generate_reward_trajectory
    scale = session_info['reward']['scale']
    offset = session_info['reward']['offset']
    change_point = session_info['reward']['change_point']
    ntrials = session_info['reward']['ntrials']

    reward_distribution_list = generate_reward_trajectory(scale, offset, change_point, ntrials)
    first_trial_of_the_session = True

    # # you can change various parameters if you want
    # task.machine.states['cue'].timeout = 2

    # start session
    task.start_session()
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info': session_info})
    pickle.dump(session_info, open(session_info['file_basename'] + '_session_info.pkl', "wb"))
    sleep(10)
    # loop over trials
    # Set a timer
    t_minute = int(input("Enter the time in minutes: ")) ## wll add in the session info
    t_end = time.time() + 60 * t_minute
    while time.time() < t_end: # time check
        if task.error_repeat:  # error repeat check
            task.error_repeat = False
            print("punishment_time_out: " + str(session_info["punishment_timeout"]))
            sleep(session_info["punishment_timeout"])
            print("Trial " + str(task.trial_number) + " \n")
            task.trial_number += 1
            print("*******************************\n")
            print("*error_repeat trial* \n" +
                  " - Current card condition: \n" +
                  "*******************************\n" +
                  "*reward_side: " + str(task.current_card[0]) + "\n")
            task.trial_number += 1
        else:
            if not first_trial_of_the_session:
                print("reward_time_out: " + str(session_info["reward_timeout"]))
                sleep(session_info["reward_timeout"])
            else:
                first_trial_of_the_session = False
            # setup the beginning of a new trial
            task.error_count = 0 # reset the error count if previous trial is correct
            print("Trial " + str(task.trial_number) + " \n")
            task.trial_number += 1
            print("*******************************\n")
            # acquire new reward contingency and cue association
            task.current_card = task_information.draw_card(session_info['phase'])
            task.current_reward = reward_distribution_list[task.trial_number] + float(task.reward_size_offset)
            logging.info(";" + str(time.time()) + ";[condition];current_card_" + str(task.current_card) +
                         ";current_reward_" + str(current_reward)[1:-1])
            print(" - Current card condition: \n" +
                  "*******************************\n" +
                  "*reward_side: " + str(task.current_card[0]) + "\n" +
                  "*reward_size: " + str(current_reward)[1:-1] + "\n")
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