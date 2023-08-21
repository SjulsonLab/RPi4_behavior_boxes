#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# python3: choice_motivation_task.py
"""
author: Mitch Farrell
date: 2023-08-17
name: choice_motivation_task.py
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

# from IPython.display import display, HTML
#
# display(HTML("<style>.container { width:100% !important; }</style>"))

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

class ChoiceMotivationTask(object):
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
            self.session_info = kwargs.get("session_info", None)
        ic(self.session_info)

        # initialize the state machine
        self.states = [
            State(name='standby',
                  on_enter=['switch_to_reward_available'],
                  on_exit=["exit_standby"]),
            State(name="choice_phase",
                  on_enter=["enter_choice_phase"],
                  on_exit=["exit_choice_phase"]),
            State(name='right_motivation_phase',
                  on_enter=['enter_right_motivation_phase'],
                  on_exit=['exit_right_motivation_phase']),
            State(name='left_motivation_phase',
                  on_enter=['enter_left_motivation_phase'],
                  on_exit=['exit_left_motivation_phase']),
            Timeout(name='timeout',
                    on_enter=['enter_timeout'],
                    on_exit=['exit_timeout'],
                    timeout = self.session_info['timeout_time'], #session_info
                    on_timeout = ['switch_to_choice_phase'])]

        self.transitions = [
            ['start_trial_logic', 'standby', 'choice_phase'],  # format: ['trigger', 'origin', 'destination']

            ['switch_to_choice_phase', 'timeout', 'choice_phase'],

            ['switch_to_right_motivation_phase', 'choice_phase', 'right_motivation_phase'],
            ['switch_to_left_motivation_phase', 'choice_phase', 'left_motivation_phase'],

            ['switch_to_timeout', ['choice_phase', 'right_motivation_phase', 'left_motivation_phase'], 'timeout'],
            ['end_task', ['choice_phase','right_motivation_phase','left_motivation_phase', 'timeout'], 'standby']]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='standby'
            )

    # trial statistics
        self.right_motivation_phase_FR = self.session_info['right_motivation_phase_FR']
        self.left_motivation_phase_FR = self.session_info['left_motivation_phase_FR']
        self.rewards_earned_in_bout = 0
        self.reward_bout_number = random.randint(2,4)
        self.right_active = True
        self.trial_running = False
        self.innocent = True
        self.trial_number = 0
        self.error_count = 0
        self.error_list = []
        self.error_repeat = False
        self.entry_time = 0.0
        self.entry_interval = self.session_info["entry_interval"]
        self.reward_time = 10
        self.reward_times_up = False
        self.reward_pump1 = self.session_info["reward_pump1"]
        self.reward_pump2 = self.session_info['reward_pump2']

        self.reward_size1 = 5
        self.reward_size2 = 5
        self.reward_size3 = self.session_info['reward_size3'] #large, left
        self.reward_size4 = self.session_info['reward_size4'] #small, right

        self.ContextA_time = 0
        self.ContextB_time = 0

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

    def run(self):
        if self.state == "standby" or self.state == 'timeout':
            pass
        elif self.state == 'choice_phase':
            self.right_entry_count = 0
            self.left_entry_count = 0
            self.counts_list = []
            self.choice_phase_start = time.time()
            self.choice_phase_end = self.choice_phase_start + 10
            self.trial_running = False
            while self.choice_phase_end > self.choice_phase_start and self.state == 'choice_phase':
                if self.box.event_list:
                    self.event_name = self.box.event_list.popleft()
                else:
                    self.event_name = ''
                if self.event_name == "right_entry":
                    self.right_entry_count += 1
                    self.counts_list.append('right_entry')
                if self.event_name == "left_entry":
                    self.left_entry_count += 1
                    self.counts_list.append('left_entry')
            if self.right_entry_count > self.left_entry_count:
                self.switch_to_right_motivation_phase()
            elif self.left_entry_count > self.right_entry_count:
                self.switch_to_left_motivation_phase()
            elif self.right_entry_count == 0 and self.left_entry_count == 0:
                self.switch_to_timeout()
            elif self.left_entry_count == self.right_entry_count:
                if self.counts_list[-1] == 'right_entry':
                    self.switch_to_right_motivation_phase()
                else:
                    self.switch_to_left_motivation_phase()
        elif self.state == 'right_motivation_phase':
            self.motivation_phase_start = time.time()
            self.motivation_phase_end = self.motivation_phase_start + 10
            self.right_entry_count = 0
            self.trial_running = False
            while self.motivation_phase_end > self.motivation_phase_start and self.state == 'right_motivation_phase':
                if self.box.event_list:
                    self.event_name = self.box.event_list.popleft()
                else:
                    self.event_name = ''
                if self.event_name == "right_entry":
                    self.right_entry_count += 1
                if self.right_entry_count >= self.right_motivation_phase_FR:
                    self.pump.reward(self.reward_pump1, self.reward_size1)
                    if self.reward_size1 > 0:
                        self.reward_size1 = self.reward_size1 - 1
                    if self.reward_size2 < 5:
                        self.reward_size2 = self.reward_size2 + 1
                    self.switch_to_timeout()
            self.switch_to_timeout()
        elif self.state == 'left_motivation_phase':
            self.motivation_phase_start = time.time()
            self.motivation_phase_end = self.motivation_phase_start + 10
            self.left_entry_count = 0
            self.trial_running = False
            while self.motivation_phase_end > self.motivation_phase_start and self.state == 'right_motivation_phase':
                if self.box.event_list:
                    self.event_name = self.box.event_list.popleft()
                else:
                    self.event_name = ''
                if self.event_name == "right_entry":
                    self.right_entry_count += 1
                if self.right_entry_count >= self.right_motivation_phase_FR:
                    self.pump.reward(self.reward_pump2, self.reward_size2)
                    if self.reward_size2 > 0:
                        self.reward_size2 = self.reward_size2 - 1
                    if self.reward_size1 < 5:
                        self.reward_size1 = self.reward_size1 + 1
                    self.switch_to_timeout()
            self.switch_to_timeout()

    def enter_standby(self):
        # self.error_repeat = False
        logging.info(";" + str(time.time()) + ";[transition];enter_standby;" + str(self.error_repeat))
        self.trial_running = False
        self.box.event_list.clear()
    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(self.error_repeat))
        self.box.event_list.clear()

    def enter_choice_phase(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_choice_phase;" + str(self.error_repeat))
        self.trial_running = True
        self.box.cueLED1.on()
        self.box.cueLED2.on()
    def exit_choice_phase(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_choice_phase;" + str(self.error_repeat))
        self.box.event_list.clear()

    def enter_right_motivation_phase(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_right_motivation_phase;" + str(self.error_repeat))
        self.trial_running = True
        self.box.cueLED2.off()
        self.box.sound1.on()
    def exit_right_motivation_phase(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_right_motivation_phase;" + str(self.error_repeat))
        self.box.event_list.clear()
        self.box.cueLED1.off()
        self.box.sound1.off()

    def enter_left_motivation_phase(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_left_motivation_phase;" + str(self.error_repeat))
        self.trial_running = True
        self.box.cueLED1.off()
        self.box.sound1.on()
    def exit_left_motivation_phase(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_left_motivation_phase;" + str(self.error_repeat))
        self.box.event_list.clear()
        self.box.cueLED2.off()
        self.box.sound1.off()

    def enter_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_timeout;" + str(self.error_repeat))
        self.box.event_list.clear()
        self.trial_running = False
    def exit_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_timeout;" + str(self.error_repeat))
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
            plt.savefig(self.session_info['basedir'] + "/" + self.session_info['basename'] + "/" + self.session_info[
                'basename'] + "_lever_choice_plot" + '.png')
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
            plt.savefig(self.session_info['basedir'] + "/" + self.session_info['basename'] + "/" + self.session_info[
                'basename'] + "_summery" + '.png')
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
        # self.box.cueLED2.off()

