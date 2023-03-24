#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# python3: self_admin_task_context.py
"""
author: Mitch Farrell
date: 2023-03-24
name: self_admin_task_context.py
goal: expand self-admin task to include contextual/probabilistic components
description:
    6 blocks; BCAC (5 min for B and A; 2.5 min for C); x% probability of reward in A, y% probability of reward in B
"""
import importlib
from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
import pysistence, collections
from icecream import ic
import logging
import time
from datetime import datetime
import os
from gpiozero import PWMLED, LED, Button
from colorama import Fore, Style
import logging.config
from time import sleep
import random
import threading
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.figure as fg
import numpy as np

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
    }
)
# all modules above this line will have logging disabled

import behavbox

# adding timing capability to the state machine
@add_state_features(Timeout)
class TimedStateMachine(Machine):
    pass

class SelfAdminTaskContext(object):
    # Define states. States where the animals is waited to make their decision

    def __init__(self, **kwargs):  # name and session_info should be provided as kwargs

        # if no name or session, make fake ones (for testing purposes)
        if kwargs.get("name", None) is None:
            self.name = "name"
            print(
                Fore.RED
                + Style.BRIGHT
                + "Warning: no name supplied; making fake one"
                + Style.RESET_ALL
            )
        else:
            self.name = kwargs.get("name", None)

        if kwargs.get("session_info", None) is None:
            print(
                Fore.RED
                + Style.BRIGHT
                + "Warning: no session_info supplied; making fake one"
                + Style.RESET_ALL
            )
            from fake_session_info import fake_session_info

            self.session_info = fake_session_info
        else:
            self.session_info = kwargs.get("session_info_self_admin", None)
        ic(self.session_info)

        # initialize the state machine
        self.states = [
            State(name='standby',
                  on_exit=["exit_standby"]),
            Timeout(name="Context_A",
                    on_enter=["enter_ContextA"],
                    on_exit=["exit_ContextA"],
                    timeout=self.session_info["ContextA_time"], #5 min; In self_admin_task program, this is just a restart signal that counts the trials doesn't really do anything. So I can update this to switch to standby
                    on_timeout=["switch_to_ContextC_from_ContextA"]),
            Timeout(name="Context_B",
                    on_enter=["enter_ContextB"],
                    on_exit=["exit_ContextB"],
                    timeout=self.session_info["ContextB_time"],
                    on_timeout=["switch_to_ContextC_from_ContextB"]),
            Timeout(name="ContextC_from_ContextA",
                    on_enter=["enter_ContextC_from_ContextA"],
                    on_exit=["exit_ContextC_from_ContextA"],
                    timeout=self.session_info["ContextC_time"],
                    on_timeout=["switch_to_ContextB"]),
            Timeout(name="ContextC_from_ContextB",
                    on_enter=["enter_ContextC_from_ContextB"],
                    on_exit=["exit_ContextC_from_ContextB"],
                    timeout=self.session_info["ContextC_time"],
                    on_timeout=["switch_to_ContextA"])
        ]

        self.transitions = [
            ['start_trial_logic', 'standby', 'ContextB'], # format: ['trigger', 'origin', 'destination']
            ['switch_to_ContextC_from_ContextA', 'ContextA', 'ContextC'],
            ['switch_to_ContextC_from_ContextB', 'ContextB', 'ContextC'],
            ['switch_to_ContextB', 'ContextC', 'ContextB'],
            ['switch_to_ContextA', 'ContextC', 'ContextA']
        ]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='standby'  #STARTS IN STANDBY MODE
        )
        self.trial_running = False

        # trial statistics
        self.innocent = True
        self.trial_number = 0
        self.error_count = 0
        self.error_list = []
        self.error_repeat = False
        self.lever_pressed_time = 0.0
        self.lever_press_interval = self.session_info["lever_press_interval"]
        # self.reward_time_start = None # for reward_available state time keeping purpose
        self.reward_time = 10 # sec. could be incorporate into the session_info; available time for reward
        self.reward_times_up = False
        self.reward_pump = self.session_info["reward_pump"]
        self.reward_size = self.session_info["reward_size"]

        self.active_press = 0
        self.inactive_press = 0
        self.timeline_active_press = []
        self.active_press_count_list = []
        self.timeline_inactive_press = []
        self.inactive_press_count_list = []

        self.left_poke_count = 0
        self.right_poke_count = 0
        self.timeline_left_poke = []
        self.left_poke_count_list = []
        self.timeline_right_poke = []
        self.right_poke_count_list = []
        self.event_name = ""
        # initialize behavior box
        self.box = behavbox.BehavBox(self.session_info)
        self.pump = self.box.pump
        self.treadmill = self.box.treadmill

        # self.distance_initiation = self.session_info['treadmill_setup']['distance_initiation']
        # self.distance_cue = self.session_info['treadmill_setup']['distance_cue']
        # self.distance_buffer = None
        # self.distance_diff = 0

        # for refining the lick detection
        self.lick_count = 0
        self.side_mice_buffer = None
        self.LED_blink = False
        try:
            self.lick_threshold = self.session_info["lick_threshold"]
        except:
            print("No lick_threshold defined in session_info. Therefore, default defined as 2 \n")
            self.lick_threshold = 1

        # session_statistics
        self.total_reward = 0

    ########################################################################
    # functions called when state transitions occur
    ########################################################################
    def run(self):
        if self.box.event_list:
            self.event_name = self.box.event_list.popleft()
        else:
            self.event_name = ""
        if self.state == "standby":
            pass
        elif self.state == "ContextA":
            if self.event_name == "reserved_rx1_pressed":
                lever_pressed_time_temp = time.time()  # assign the lever_pressed_time_temp to the current time
                lever_pressed_dt = lever_pressed_time_temp - self.lever_pressed_time  # lever_pressed_dt subtracts the current lever press time from the previous lever press time
                if lever_pressed_dt >= self.lever_press_interval:  # if the time elapsed between lever presses is more than self.lever_press_interval, then administer a reward; note that this lever_press_interval is modifiable in session_info
                    if random.random() <= self.session_info['ContextA_reward_probability']:
                        print('ContextA_reward_delivered')
                        self.pump.reward(self.reward_pump, self.reward_size)
                        self.lever_pressed_time = lever_pressed_time_temp  # this is used for subsequent lever presses
                        self.total_reward += 1
        elif self.state == 'ContextB':
            if self.event_name == "reserved_rx1_pressed":
                lever_pressed_time_temp = time.time()
                lever_pressed_dt = lever_pressed_time_temp - self.lever_pressed_time
                if lever_pressed_dt >= self.lever_press_interval:
                    if random.random() <= self.session_info['ContextB_reward_probability']:
                        print('ContextB_reward_delivered')
                        self.pump.reward(self.reward_pump, self.reward_size)
                        self.lever_pressed_time = lever_pressed_time_temp  # this is used for subsequent lever presses
                        self.total_reward += 1
        elif self.state == 'ContextC_from_ContextA':
            if self.event_name == "reserved_rx1_pressed":
                print('ContextC_from_ContextA_active_press')
        elif self.state == 'ContextC_from_ContextB':
            if self.event_name == "reserved_rx1_pressed":
                print('ContextC_from_ContextB_active_press')
        self.box.check_keybd()

    # def start_trial_logic_funct(self):
    #     self.start_trial_logic()
    #     logging.info(";" + str(time.time()) + ";[transition];start_trial_called;" + str(self.error_repeat))

    def exit_standby(self):
        # self.error_repeat = False
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(self.error_repeat))
        self.box.event_list.clear()
        self.trial_running = False

    def enter_ConextA(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextA;" + str(self.error_repeat))
        self.trial_running = True
        self.box.sound1.on() #ACTIVATE SOUND CUE#
        
    def exit_ContextA(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextA;" + str(self.error_repeat))
        # self.pump.reward("vaccum", 0)
        self.trial_running = False
        self.box.sound1.off()  # INACTIVATE SOUND CUE#
        self.box.event_list.clear()
    def enter_ContextB(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextB;" + str(self.error_repeat))
        self.trial_running = True
        self.box.sound2.on()
    def exit_ContextB(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextB;" + str(self.error_repeat))
        self.trial_running = False
        self.box.sound2.off()  # INACTIVATE SOUND CUE#
        self.box.event_list.clear()
    def enter_ContextC_from_ContextA(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextC_from_ContextA;" + str(self.error_repeat))
        self.trial_running = True
    def exit_ContextC_from_ContextA(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextC_from_ContextA;" + str(self.error_repeat))
        self.trial_running = False
        self.box.event_list.clear()
    def enter_ContextC_from_ContextB(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextC_from_ContextB;" + str(self.error_repeat))
        self.trial_running = True
    def exit_ContextC_from_ContextB(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextC_from_ContextB;" + str(self.error_repeat))
        self.trial_running = False
        self.box.event_list.clear()

    def update_plot(self):
        fig, axes = plt.subplots(1, 1, )
        axes.plot([1, 2], [1, 2], color='green', label='test')
        self.box.check_plot(fig)

    def update_plot_error(self):
        error_event = self.error_list
        labels, counts = np.unique(error_event, return_counts=True)
        ticks = range(len(counts))
        fig, ax = plt.subplots(1, 1, )
        ax.bar(ticks, counts, align='center', tick_label=labels)
        # plt.xticks(ticks, labels)
        # plt.title(session_name)
        ax = plt.gca()
        ax.set_xticks(ticks, labels)
        ax.set_xticklabels(labels=labels, rotation=70)

        self.box.check_plot(fig)

    def update_plot_choice(self, save_fig=False):
        trajectory_active = self.left_poke_count_list
        time_active = self.timeline_left_poke
        trajectory_inactive = self.right_poke_count_list
        time_inactive = self.timeline_right_poke
        fig, ax = plt.subplots(1, 1, )
        print(type(fig))

        ax.plot(time_active, trajectory_active, color='b', marker="o", label='active_trajectory')
        ax.plot(time_inactive, trajectory_inactive, color='r', marker="o", label='inactive_trajectory')
        if save_fig:
            plt.savefig(self.session_info['basedir'] + "/" + self.session_info['basename'] + "/" +                         self.session_info['basename'] + "_lever_choice_plot" + '.png')
        self.box.check_plot(fig)

    def integrate_plot(self, save_fig=False):

        fig, ax = plt.subplots(2, 1)

        trajectory_left = self.active_press
        time_active_press = self.timeline_active_press
        trajectory_right = self.right_poke_count_list
        time_inactive_press = self.timeline_inactive_press
        print(type(fig))

        ax[0].plot(time_active_press, trajectory_left, color='b', marker="o", label='left_lick_trajectory')
        ax[0].plot(time_inactive_press, trajectory_right, color='r', marker="o", label='right_lick_trajectory')

        error_event = self.error_list
        labels, counts = np.unique(error_event, return_counts=True)
        ticks = range(len(counts))
        ax[1].bar(ticks, counts, align='center', tick_label=labels)
        # plt.xticks(ticks, labels)
        # plt.title(session_name)
        ax[1] = plt.gca()
        ax[1].set_xticks(ticks, labels)
        ax[1].set_xticklabels(labels=labels, rotation=70)

        if save_fig:
            plt.savefig(self.session_info['basedir'] + "/" + self.session_info['basename'] + "/" +                         self.session_info['basename'] + "_summery" + '.png')
        self.box.check_plot(fig)

    ########################################################################
    # methods to start and end the behavioral session
    ########################################################################

    def start_session(self):
        ic("TODO: start video")
        self.box.video_start()

    def end_session(self):
        ic("TODO: stop video")
        self.update_plot_choice(save_fig=True)
        self.box.video_stop()

