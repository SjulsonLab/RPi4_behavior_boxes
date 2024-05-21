#!/usr/bin/env python
# coding: utf-8

"""
author: Mitch Farrell
date: 2024-05-1
name: opioid_forage_task_phase_1.py
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

class OpioidForageTaskPhase1(object):
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
            State(name="reward_available",
                  on_enter=["enter_reward_available"],
                  on_exit=["exit_reward_available"]),
            Timeout(name='timeout',
                    on_enter=['enter_timeout', 'update_plot'],
                    on_exit=['exit_timeout'],
                    timeout=self.session_info['timeout_time'],  # session_info
                    on_timeout=['switch_to_reward_available'])]

        self.transitions = [
            ['start_trial_logic', 'standby', 'reward_available'],  # format: ['trigger', 'origin', 'destination']

            ['switch_to_standby', 'reward_available', 'standby'],
            ['switch_to_reward_available', ['standby', 'timeout'], 'reward_available'],

            ['switch_to_timeout', 'reward_available', 'timeout'],
            ['end_task', ['reward_available', 'timeout'], 'standby']]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='standby'  # STARTS IN STANDBY MODE
        )

        # trial statistics
        self.trial_running = False
        self.innocent = True
        self.trial_number = 0
        self.error_count = 0
        self.error_list = []
        self.error_repeat = False
        self.previous_reward_time = 0.0
        self.entry_interval = self.session_info["entry_interval"]  # update lever_press_interval to entry_interval--make this 3s instead of 1s
        self.reward_time = 10
        self.reward_times_up = False
        self.reward_pump1 = self.session_info["reward_pump1"]
        self.reward_pump2 = self.session_info['reward_pump2']

        self.reward_size1 = self.session_info["reward_size1"]  # right
        self.reward_size2 = self.session_info['reward_size2']  # small, left

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

        # Event counters for plotting
        self.right_entry_count = 0
        self.left_entry_count = 0
        self.reward_event_count = 0
        self.timeline_right_entry = []
        self.timeline_left_entry = []
        self.timeline_reward_event = []
        self.event_times = []

    def run(self):
        current_time = time.time()
        if self.state == "standby" or self.state == 'timeout':
            if self.box.event_list:
                self.event_name = self.box.event_list.popleft()
            else:
                self.event_name = ''
            if self.event_name == 'right_entry':
                self.right_entry_count += 1
                self.timeline_right_entry.append(current_time)
            if self.event_name == 'left_entry':
                self.left_entry_count += 1
                self.timeline_left_entry.append(current_time)
        elif self.state == 'reward_available':
            if self.box.event_list:
                self.event_name = self.box.event_list.popleft()
            else:
                self.event_name = ''
            if self.event_name == 'right_entry':
                self.right_entry_count += 1
                self.timeline_right_entry.append(current_time)
                self.pump.reward(self.reward_pump2, self.reward_size2)
                self.reward_event_count += 1
                self.timeline_reward_event.append(current_time)
                self.switch_to_timeout()
            if self.event_name == 'left_entry':
                self.left_entry_count += 1
                self.timeline_left_entry.append(current_time)
                self.pump.reward(self.reward_pump1, self.reward_size1)
                self.reward_event_count += 1
                self.timeline_reward_event.append(current_time)
                self.switch_to_timeout()
        self.box.check_keybd()

    def enter_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_standby;" + str(self.error_repeat))
        self.trial_running = False
        self.box.event_list.clear()
        self.box.cueLED1.off()
        self.box.cueLED2.off()

    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(self.error_repeat))
        self.box.event_list.clear()
        self.box.cueLED1.on()
        self.box.cueLED2.on()

    def enter_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_reward_available;" + str(self.error_repeat))
        self.trial_running = True

    def exit_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_reward_available;" + str(self.error_repeat))
        self.box.event_list.clear()

    def enter_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_timeout;" + str(self.error_repeat))
        self.trial_running = True
        self.box.event_list.clear()

    def exit_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_timeout;" + str(self.error_repeat))
        self.box.event_list.clear()

    def update_plot(self):
        current_time = time.time()
        self.event_times.append(current_time)

        fig, ax = plt.subplots(3, 1, figsize=(10, 8))
        ax[0].plot(self.timeline_right_entry, np.arange(1, len(self.timeline_right_entry) + 1), 'r-', label='Right Entry')
        ax[0].set_title('Right Entry Events Over Time')
        ax[0].set_xlabel('Time (s)')
        ax[0].set_ylabel('Count')
        ax[0].legend()

        ax[1].plot(self.timeline_left_entry, np.arange(1, len(self.timeline_left_entry) + 1), 'b-', label='Left Entry')
        ax[1].set_title('Left Entry Events Over Time')
        ax[1].set_xlabel('Time (s)')
        ax[1].set_ylabel('Count')
        ax[1].legend()

        ax[2].plot(self.timeline_reward_event, np.arange(1, len(self.timeline_reward_event) + 1), 'g-', label='Reward Events')
        ax[2].set_title('Reward Events Over Time')
        ax[2].set_xlabel('Time (s)')
        ax[2].set_ylabel('Count')
        ax[2].legend()

        plt.tight_layout()
        plt.savefig(self.session_info['basedir'] + "/" + self.session_info['basename'] + "/" + self.session_info['basename'] + "_event_counts.png")
        self.box.check_plot(fig)
        plt.close(fig)

    def update_plot_error(self):
        error_event = self.error_list
        labels, counts = np.unique(error_event, return_counts=True)
        ticks = range(len(counts))
        fig, ax = plt.subplots(1, 1, )
        ax.bar(ticks, counts, align='center', tick_label=labels)
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels=labels, rotation=70)
        self.box.check_plot(fig)
        plt.close(fig)

    def update_plot_choice(self, save_fig=False):
        trajectory_active = self.left_poke_count_list
        time_active = self.timeline_left_poke
        trajectory_inactive = self.right_poke_count_list
        time_inactive = self.timeline_right_poke
        fig, ax = plt.subplots(1, 1, )

        ax.plot(time_active, trajectory_active, color='b', marker="o", label='active_trajectory')
        ax.plot(time_inactive, trajectory_inactive, color='r', marker="o", label='inactive_trajectory')
        if save_fig:
            plt.savefig(self.session_info['basedir'] + "/" + self.session_info['basename'] + "/" + self.session_info[
                'basename'] + "_lever_choice_plot" + '.png')
        self.box.check_plot(fig)
        plt.close(fig)

    def integrate_plot(self, save_fig=False):

        fig, ax = plt.subplots(2, 1)

        trajectory_left = self.active_press
        time_active_press = self.timeline_active_press
        trajectory_right = self.right_poke_count_list
        time_inactive_press = self.timeline_inactive_press

        ax[0].plot(time_active_press, trajectory_left, color='b', marker="o", label='left_lick_trajectory')
        ax[0].plot(time_inactive_press, trajectory_right, color='r', marker="o", label='right_lick_trajectory')

        error_event = self.error_list
        labels, counts = np.unique(error_event, return_counts=True)
        ticks = range(len(counts))
        ax[1].bar(ticks, counts, align='center', tick_label=labels)
        ax[1].set_xticks(ticks)
        ax[1].set_xticklabels(labels=labels, rotation=70)

        if save_fig:
            plt.savefig(self.session_info['basedir'] + "/" + self.session_info['basename'] + "/" + self.session_info[
                'basename'] + "_summery" + '.png')
        self.box.check_plot(fig)
        plt.close(fig)

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
