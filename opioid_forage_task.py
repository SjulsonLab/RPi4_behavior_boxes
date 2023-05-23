#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# python3: opioid_forage_task.py
"""
author: Mitch Farrell
date: 2023-05-23
name: opioid_forage_task.py
goal: opioid_forage_task licks only, switch between left and right patches
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

class OpioidForageTask(object):
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

            State(name="remi_right_patch_active",
                  on_enter=["enter_remi_right_patch_active"],
                  on_exit=["exit_remi_right_patch_active"]),
            State(name="liquid_left_patch_active",
                  on_enter=["enter_liquid_left_patch_active"],
                  on_exit=["exit_liquid_left_patch_active"]),

            Timeout(name="travel_to_remi_right_patch_active",
                    on_enter=["enter_travel_to_remi_right_patch_active"],
                    on_exit=["exit_travel_to_remi_right_patch_active"],
                    timeout=self.session_info['travel_time'],
                    on_timeout=['switch_from_travel_to_remi_right_patch_active']),
            Timeout(name="travel_to_liquid_left_patch_active",
                    on_enter=["enter_travel_to_liquid_left_patch_active"],
                    on_exit=["exit_travel_to_liquid_left_patch_active"],
                    timeout = self.session_info['travel_time'],
                    on_timeout=['switch_from_travel_to_liquid_left_patch_active']),

            Timeout(name='remi_right_patch_timeout',
                    on_enter=['enter_remi_right_patch_timeout'],
                    on_exit=['exit_remi_right_patch_timeout'],
                    timeout= self.session_info['remi_timeout_time'],
                    on_timeout=['switch_from_timeout_to_remi_right_patch_active']),
            Timeout(name='liquid_left_patch_timeout',
                    on_enter=['enter_liquid_left_patch_timeout'],
                    on_exit=['exit_liquid_left_patch_timeout'],
                    timeout=self.session_info['liquid_timeout_time'],
                    on_timeout=['switch_from_timeout_to_liquid_left_patch_active'])]

        self.transitions = [
            #random start in remi_right or liquid_left
            ['start_in_remi_right_patch_active', 'standby', 'travel_to_remi_right_patch_active'],
            ['start_in_liquid_left_patch_active', 'standby', 'travel_to_liquid_left_patch_active'],

            #from timeout to active
            ['switch_from_timeout_to_remi_right_patch_active', 'remi_right_patch_timeout', 'remi_right_patch_active'],
            ['switch_from_timeout_to_liquid_left_patch_active', 'liquid_left_patch_timeout', 'liquid_left_patch_active'],

            #from active to timeout
            ['switch_to_remi_right_patch_timeout', 'remi_right_patch_active', 'remi_right_patch_timeout'],
            ['switch_to_liquid_left_patch_timeout', 'liquid_left_patch_active', 'liquid_left_patch_timeout'],

            #from active to travel
            ['switch_to_travel_to_remi_right_patch_active', 'liquid_left_patch_active', 'travel_to_remi_right_patch_active'],
            ['switch_to_travel_to_liquid_left_patch_active', 'remi_right_patch_active', 'travel_to_liquid_left_patch_active'],

            #from travel to active
            ['switch_from_travel_to_remi_right_patch_active', 'travel_to_remi_right_patch_active', 'remi_right_patch_active'],
            ['switch_from_travel_to_liquid_left_patch_active', 'travel_to_liquid_left_patch_active', 'liquid_left_patch_active'],

            #end from any state
            ['end_task', ['remi_right_patch_active','liquid_left_patch_active',
                          'travel_to_remi_right_patch_active','travel_to_liquid_left_patch_active',
                          'remi_right_patch_timeout', 'liquid_left_patch_timeout'], 'standby']]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='standby')


    # trial statistics
        self.in_loop_bool = False #prevents trial_running from switching to True upon switching from timeout to active
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

        self.event_name = ""
        # initialize behavior box
        self.box = behavbox.BehavBox(self.session_info)
        self.syringe_pump = LED(23)
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
        self.reward_size_var = 0
        self.reward_size_index = 0
        self.right_patch_rewards = [1, 0.8, 0.6, 0.4, 0.2, 0]
        self.left_patch_rewards = [3,2.5,2,1.5,1,0]

    def run(self):
        if self.state == "standby":
            pass
        elif self.state == 'remi_right_patch_active':
            self.trial_running = False
            self.left_licks = 0
            self.reward_size_var = 0
            self.reward_size_index = 0
            self.in_loop_bool = True
            self.box.event_list.clear()
            while self.state == 'remi_right_patch_active' or self.state == 'remi_right_patch_timeout':
                if self.state == 'remi_right_patch_timeout':
                    self.left_licks = 0
                if self.box.event_list:
                    self.event_name = self.box.event_list.popleft()
                else:
                    self.event_name = ''
                if self.event_name == "right_entry" and self.state == 'remi_right_patch_active':
                    if self.reward_size_var > 5:
                        self.reward_size_index = 5
                    infusion_duration = (self.session_info['weight'] / 30)*self.right_patch_rewards[self.reward_size_index]
                    self.syringe_pump.blink(infusion_duration, 0.1, 1)
                    self.reward_list.append(("remi_reward", infusion_duration))
                    logging.info(";" + str(time.time()) + ";[reward];syringe_pump_reward" + str(infusion_duration))
                    self.reward_size_var += 1
                    self.reward_size_index += 1
                    self.switch_to_remi_right_patch_timeout()
                elif self.event_name == 'left_entry' and self.state == 'remi_right_patch_active':
                    if self.reward_size_var != 0:
                        self.left_licks += 1
                        if self.left_licks >= self.session_info['FR_before_patch_switch']:
                            self.switch_to_travel_to_liquid_left_patch_active()
        elif self.state == 'liquid_left_patch_active':
            self.trial_running = False
            self.right_licks = 0
            self.reward_size_var = 0
            self.reward_size_index = 0
            self.in_loop_bool = True
            self.box.event_list.clear()
            while self.state == 'liquid_left_patch_active' or self.state == 'liquid_left_patch_timeout':
                if self.state == 'remi_right_patch_timeout':
                    self.right_licks = 0
                if self.box.event_list:
                    self.event_name = self.box.event_list.popleft()
                else:
                    self.event_name = ''
                if self.event_name == "left_entry" and self.state == 'liquid_left_patch_active':
                    if self.reward_size_var > 5:
                        self.reward_size_index = 5
                    self.pump.reward(self.reward_pump1, self.left_patch_rewards[self.reward_size_index])
                    self.reward_size_var +=1
                    self.reward_size_index +=1
                    self.switch_to_liquid_left_patch_timeout()
                elif self.event_name == 'right_entry' and self.state == 'liquid_left_patch_active':
                    if self.reward_size_var != 0:
                        self.right_licks += 1
                        if self.right_licks >= self.session_info['FR_before_patch_switch']:
                            self.switch_to_travel_to_remi_right_patch_active()

    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(self.error_repeat))
        self.box.event_list.clear()
    def enter_remi_right_patch_active(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_remi_right_patch_active;" + str(self.error_repeat))
        self.box.cueLED2.on()
        if not self.in_loop_bool:
            self.trial_running = True
    def exit_remi_right_patch_active(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_remi_right_patch_active;" + str(self.error_repeat))

    def enter_travel_to_remi_right_patch_active(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_travel_to_remi_right_patch_active;" + str(self.error_repeat))
        self.box.cueLED2.off()
        self.box.sound1.on()
        self.in_loop_bool = False
    def exit_travel_to_remi_right_patch_active(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_travel_to_remi_right_patch_active;" + str(self.error_repeat))
        self.box.sound1.off()

    def enter_remi_right_patch_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_remi_right_patch_timeout;" + str(self.error_repeat))
        self.box.sound2.on()
    def exit_remi_right_patch_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_remi_right_patch_timeout;" + str(self.error_repeat))
        self.box.sound2.off()

    def enter_liquid_left_patch_active(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_liquid_left_patch_active;" + str(self.error_repeat))
        self.box.cueLED1.on()
        if not self.in_loop_bool:
            self.trial_running = True
    def exit_liquid_left_patch_active(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_liquid_left_patch_active;" + str(self.error_repeat))

    def enter_travel_to_liquid_left_patch_active(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_travel_to_liquid_left_patch_active;" + str(self.error_repeat))
        self.box.cueLED1.off()
        self.box.sound1.on()
        self.in_loop_bool = False
    def exit_travel_to_liquid_left_patch_active(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_travel_to_liquid_left_patch_active;" + str(self.error_repeat))
        self.box.sound1.off()

    def enter_liquid_left_patch_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_liquid_left_patch_timeout;" + str(self.error_repeat))
        self.box.sound2.on()
    def exit_liquid_left_patch_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_liquid_left_patch_timeout;" + str(self.error_repeat))
        self.box.sound2.off()


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

