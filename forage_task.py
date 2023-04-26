#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# python3: self_admin_task_context.py
"""
author: Mitch Farrell
date: 2023-04-26
name: forage_task.py
goal: forage_task licks only, switch between left and right patches
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


class ForageTask(object):
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
                  on_exit=["exit_standby"]),
            State(name="right_patch",
                  on_enter=["enter_right_patch"],
                  on_exit=["exit_right_patch"]),
            State(name="left_patch",
                  on_enter=["enter_left_patch"],
                  on_exit=["exit_left_patch"]),
            Timeout(name="travel_to_right_patch",
                    on_enter=["enter_travel_to_right_patch"],
                    on_exit=["exit_travel_to_right_patch"],
                    timeout=self.session_info['travel_time'],
                    on_timeout=['switch_to_right_patch']),
            Timeout(name="travel_to_left_patch",
                    on_enter=["enter_travel_to_left_patch"],
                    on_exit=["exit_travel_to_left_patch"],
                    timeout = self.session_info['travel_time'],
                    on_timeout=['switch_to_left_patch']),
            State(name="left_reward_available",
                    on_enter=["enter_left_reward_available"],
                    on_exit=["exit_left_reward_available"]),
            State(name="right_reward_available",
                    on_enter=["enter_right_reward_available"],
                    on_exit=["exit_right_reward_available"])
                ]

        # create a while loop that runs if State == ContextB or lick_LED_ContextB
        # create a different while loop that runs if State == ContextA or lick_LED_ContextB
        # this whole while loop lasts as long as
        self.transitions = [
            ['start_in_right_patch', 'standby', 'travel_to_right_patch'],  # format: ['trigger', 'origin', 'destination']
            ['start_in_left_patch', 'standby', 'travel_to_left_patch'],

            ['switch_to_right_patch', 'travel_to_right_patch', 'right_patch'],
            ['switch_to_left_patch', 'travel_to_left_patch', 'left_patch'],

            ['switch_to_travel_to_right_patch', 'left_patch', 'travel_to_right_patch'],
            ['switch_to_travel_to_left_patch', 'right_patch', 'travel_to_left_patch'],

            ['end_task', ['left_patch','right_patch','travel_to_right_patch','travel_to_left_patch'], 'standby']]

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
        self.lick_time = 0.0
        self.lick_interval = self.session_info["lick_interval"]
        # self.reward_time_start = None # for reward_available state time keeping purpose
        self.reward_time = 10  # sec. could be incorporate into the session_info; available time for reward
        self.reward_times_up = False
        self.reward_pump1 = self.session_info["reward_pump1"]  # update this in session_info
        self.reward_pump2 = self.session_info['reward_pump2']  # update this in session_info
        self.reward_size1 = self.session_info["reward_size1"]  # update this in session_info
        self.reward_size2 = self.session_info['reward_size2']  # update this in session_info

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
        self.reward_size_var = 0
        self.reward_size_index = 0
        self.right_patch_rewards = [5,4,3,2,1,0]
        self.left_patch_rewards = [5,4,3,2,1,0]

    def run(self):
        if self.state == "standby":
            pass
        elif self.state == 'right_patch':  # if in ContextA
            self.right_licks = 0
            self.left_licks = 0
            self.reward_size_var = 0
            self.reward_size_index = 0
            while self.state == 'right_patch':  # need to be able to jump out of this loop even in a below while loop; runs when ContextB_duration hasn't elapsed
                if self.box.event_list:
                    self.event_name = self.box.event_list.popleft()
                else:
                    self.event_name = ''
                if self.event_name == "right_entry":  # if an active lever press detected
                    lick_time_temp = time.time()  # assign the current lever press to the current time; used to prevent repeated presses
                    lick_dt = lick_time_temp - self.lick_time  # used to check previous rewarded lever time
                    if lick_dt >= self.lick_interval:  # if the last rewarded press occurred more than 1s ago, then turn LED on
                        if self.reward_size_var > 5:
                            self.reward_size_index = 5
                        self.pump.reward(self.reward_pump1, self.right_patch_rewards[self.reward_size_index])  # reward delivery based on pump number and reward size
                        self.reward_size_var +=1
                        self.reward_size_index +=1
                        self.lick_time = lick_time_temp  # this is used for subsequent lever presses
                elif self.event_name == 'left_entry':
                    self.left_licks += 1
                    if self.left_licks >= self.session_info['FR_before_patch_switch']:
                        self.switch_to_travel_to_left_patch() #initiates travel
                    else:
                        pass
        elif self.state == 'left_patch':  # if in ContextA
            self.right_licks = 0
            self.left_licks = 0
            self.reward_size_var = 0
            self.reward_size_index = 0
            while self.state == 'left_patch':  # need to be able to jump out of this loop even in a below while loop; runs when ContextB_duration hasn't elapsed
                if self.box.event_list:
                    self.event_name = self.box.event_list.popleft()
                else:
                    self.event_name = ''
                if self.event_name == "left_entry":  # if an active lever press detected
                    lick_time_temp = time.time()  # assign the current lever press to the current time; used to prevent repeated presses
                    lick_dt = lick_time_temp - self.lick_time  # used to check previous rewarded lever time
                    if lick_dt >= self.lick_time:  # if the last rewarded press occurred more than 1s ago, then turn LED on
                        if self.reward_size_var > 5:
                            self.reward_size_index = 5
                        self.pump.reward(self.reward_pump1, self.right_patch_rewards[self.reward_size_index])  # reward delivery based on pump number and reward size
                        self.reward_size_var +=1
                        self.reward_size_index +=1
                        self.lick_time = lick_time_temp  # this is used for subsequent lever presses
                elif self.event_name == 'right_entry':
                    self.right_licks += 1
                    if self.left_licks >= self.session_info['FR_before_patch_switch']:
                        self.switch_to_travel_to_right_patch() #initiates travel
                    else:
                        pass

    def exit_standy(self):

    def enter_right_patch(self):
    def exit_right_patch(self):

    def enter_left_patch(self):
    def exit_left_patch(self):


    def enter_travel_to_right_patch(self):
    def enter_travel_to_right_patch(self):

    def enter_ContextA(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextA;" + str(self.error_repeat))
        self.box.sound2.on()  # ACTIVATE SOUND CUE#
        self.trial_running = True

    def exit_ContextA(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextA;" + str(self.error_repeat))
        # self.pump.reward("vaccum", 0)
        self.box.event_list.clear()

    def enter_ContextB(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextB;" + str(self.error_repeat))
        self.box.sound1.on()
        self.trial_running = True

    def exit_ContextB(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextB;" + str(self.error_repeat))
        self.box.event_list.clear()

    def enter_ContextC_from_ContextA(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextC_from_ContextA;" + str(self.error_repeat))
        self.box.sound2.off()  # INACTIVATE SOUND CUE#
        self.trial_running = False

    def exit_ContextC_from_ContextA(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextC_from_ContextA;" + str(self.error_repeat))
        self.box.event_list.clear()

    def enter_ContextC_from_ContextB(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextC_from_ContextB;" + str(self.error_repeat))
        self.box.sound1.off()  # INACTIVATE SOUND CUE#
        self.trial_running = False

    def exit_ContextC_from_ContextB(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextC_from_ContextB;" + str(self.error_repeat))
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

