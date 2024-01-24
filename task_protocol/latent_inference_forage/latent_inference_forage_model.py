#!/usr/bin/env python
# coding: utf-8

# python3: latent_inference_forage_task_three_states.py
"""
author: Mitch Farrell; edited Matthew Chin
last updated: 2024-01-24
name: latent_inference_forage_task_three_states.py
"""
from transitions import State, Machine
from transitions.extensions.states import add_state_features, Timeout

from icecream import ic
import logging
import time

import random
import numpy as np

import logging.config
from collections import deque
from typing import Protocol, List, Tuple, Union
from collections import defaultdict


import importlib
import pysistence, collections
from datetime import datetime
import os
from gpiozero import PWMLED, LED, Button
from colorama import Fore, Style
import logging.config
from time import sleep
import threading
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.figure as fg

rng = np.random.default_rng(12345)


# adding timing capability to the state machine
@add_state_features(Timeout)
class TimedStateMachine(Machine):
    pass

class LatentInferenceForageTaskThreeStates(object):

    def __init__(self, session_info: dict):
        # TASK + BEHAVIOR STATUS
        self.right_active = True
        self.trial_running = False
        self.trial_number = 0  # I don't think stopping at max trials is implemented - do that

        self.last_choice_time = 0.0
        self.rewards_earned_in_block = 0
        self.rewards_available_in_block = random.randint(1, 4)

        # Lick detection
        self.lick_side_buffer = np.zeros(2)

        ### TRAINING REWARDS PARAMETERS ###
        self.automate_training_rewards = False  # keep here, use in controller
        self.give_training_reward = False  # keep here, use in controller
        self.error_count = 0
        self.errors_to_reward = 5

        # These can't be refactored, session parameters needed for behavbox
        # maybe move them into a parameters class
        self.choice_interval = session_info['entry_interval']
        self.lick_threshold = session_info['lick_threshold']
        self.machine = self.make_state_machine()
        self.last_state_fxn = self.switch_to_standby
        self.block_type_counter = np.zeros(2)

        # revise these later to make sure you need them
        self.trial_choice_list: list = []
        self.trial_correct_list: list = []
        self.trial_choice_times: list = []
        self.trial_reward_given: list = []
        self.event_list = deque()
        self.t_session = time.time()

    def make_state_machine(self):
        states = [
            State(name='standby',
                  on_exit=['exit_standby']),
            State(name='right_patch',
                  on_enter=['enter_right_patch'],
                  on_exit=['exit_right_patch']),
            State(name='left_patch',
                  on_enter=['enter_left_patch'],
                  on_exit=['exit_left_patch']),
            State(name='dark_period',
                  on_enter=['enter_dark_period'],
                  on_exit=['exit_dark_period'])
        ]

        # all of these transition functions are created automatically
        transitions = [
            ['start_in_right_patch', 'standby', 'right_patch'],
            ['start_in_left_patch', 'standby', 'left_patch'],

            ['switch_to_right_patch', ['dark_period', 'left_patch'], 'right_patch'],
            ['switch_to_left_patch', ['dark_period', 'right_patch'], 'left_patch'],

            ['switch_to_dark_period', ['left_patch', 'right_patch'], 'dark_period'],

            ['switch_to_standby', '*', 'standby']]

        machine = TimedStateMachine(
            model=self,
            states=states,
            transitions=transitions,
            initial='standby'
        )
        return machine

    # trial statistics
        self.dark_period_times = [10]
        self.end_dark_time = 0
        self.next_dark_time = 0
        self.trial_running = False
        self.innocent = True
        self.trial_number = 0
        self.error_count = 0
        self.error_list = []
        self.error_repeat = False
        self.lick_time = 0.0
        self.lick_interval = self.session_info["lick_interval"]
        # self.reward_time_start = None # for reward_available state time keeping purpose
        self.reward_time = 10
        self.reward_times_up = False
        self.reward_pump1 = self.session_info["reward_pump1"]
        self.reward_pump2 = self.session_info['reward_pump2']
        self.reward_size1 = self.session_info['reward_size1']
        self.reward_size2 = self.session_info['reward_size2']
        self.reward_size3 = self.session_info['reward_size3']
        self.reward_size4 = self.session_info['reward_size4']
        self.ITI = self.session_info['ITI']
        self.p_switch = self.session_info['p_switch']
        self.p_reward = self.session_info['p_reward']
        self.reward_earned = False

        self.ContextA_time = 0
        self.ContextB_time = 0
        self.LED_on_time_plus_LED_duration = 0

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
        self.right_entry_error = False
        self.left_entry_error = False
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
        self.right_licks = 0
        self.left_licks = 0

    def run(self):
        if self.state == 'standby' or self.state == 'dark_period':
            pass
        elif self.state == 'right_patch':
            self.trial_running = False
            self.LED_bool = False
            self.prior_choice_time = 0
            self.reward_earned = False
            self.box.event_list.clear()
            while self.state == 'right_patch' and self.next_dark_time > time.time():
                if not self.LED_bool:
                    if self.prior_choice_time == 0 or time.time() - self.prior_choice_time > self.ITI:
                        self.box.cueLED1.on()
                        self.box.cueLED2.on()
                        self.LED_on_time = time.time()
                        self.LED_bool = True
                        self.box.event_list.clear()
                    while self.LED_bool and self.next_dark_time > time.time():
                        if self.box.event_list:
                            self.event_name = self.box.event_list.popleft()
                        else:
                            self.event_name = ''
                        if self.event_name == 'right_entry':
                            self.prior_choice_time = time.time()
                            self.box.cueLED1.off()
                            self.box.cueLED2.off()
                            self.LED_bool = False
                            if self.p_reward >= random.random():
                                self.pump.reward(self.reward_pump1, self.reward_size1) #1 reward
                                if self.p_switch >= random.random():
                                    self.LED_bool = False
                                    time.sleep(1)
                                    self.switch_to_left_patch()
                            else:
                                self.pump.reward(self.reward_pump1, self.reward_size2) #0 reward
                        if self.event_name == 'left_entry':
                            self.prior_choice_time = time.time()
                            self.box.cueLED1.off()
                            self.box.cueLED2.off()
                            self.LED_bool = False
                            logging.info(";" + str(time.time()) + ";[transition];wrong_choice_right_patch;" + str(self.error_repeat))
        if self.next_dark_time < time.time():
            self.switch_to_dark_period()
        elif self.state == 'left_patch':
            self.trial_running = False
            self.LED_bool = False
            self.prior_choice_time = 0
            self.reward_earned = False
            self.box.event_list.clear()
            while self.state == 'left_patch' and self.next_dark_time > time.time():
                if not self.LED_bool:
                    if self.prior_choice_time == 0 or time.time() - self.prior_choice_time > self.ITI:
                        self.box.cueLED1.on()
                        self.box.cueLED2.on()
                        self.LED_on_time = time.time()
                        self.LED_bool = True
                        self.box.event_list.clear()
                    while self.LED_bool and self.next_dark_time > time.time():
                        if self.box.event_list:
                            self.event_name = self.box.event_list.popleft()
                        else:
                            self.event_name = ''
                        if self.event_name == 'left_entry':
                            self.prior_choice_time = time.time()
                            self.box.cueLED1.off()
                            self.box.cueLED2.off()
                            self.LED_bool = False
                            if self.p_reward >= random.random():
                                self.pump.reward(self.reward_pump2, self.reward_size1)  # 1 reward
                                if self.p_switch >= random.random():
                                    self.LED_bool = False
                                    time.sleep(1)
                                    self.switch_to_right_patch()
                            else:
                                self.pump.reward(self.reward_pump2, self.reward_size2)  # 0 reward
                        if self.event_name == 'right_entry':
                            self.prior_choice_time = time.time()
                            self.box.cueLED1.off()
                            self.box.cueLED2.off()
                            self.LED_bool = False
                            logging.info(";" + str(time.time()) + ";[transition];wrong_choice_left_patch;" + str(self.error_repeat))
            if self.next_dark_time < time.time():
                self.switch_to_dark_period()

    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(self.error_repeat))
        self.end_dark_time = time.time()
        self.next_dark_time = self.end_dark_time + 120

    def enter_right_patch(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_right_patch;" + str(self.error_repeat))
        self.trial_running = True
    def exit_right_patch(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_right_patch;" + str(self.error_repeat))

    def enter_left_patch(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_left_patch;" + str(self.error_repeat))
        self.trial_running = True
    def exit_left_patch(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_left_patch;" + str(self.error_repeat))

    def enter_dark_period(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_dark_period;" + str(self.error_repeat))
        self.trial_running = False
        self.box.cueLED1.off()
        self.box.cueLED2.off()
        time.sleep(random.choice(self.dark_period_times))
        self.end_dark_time = time.time()
        self.next_dark_time = self.end_dark_time + 120
        if random.random() > 0.5:
            self.switch_to_left_patch()
        else:
            self.switch_to_right_patch()

    def exit_dark_period(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_dark_period;" + str(self.error_repeat))

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
