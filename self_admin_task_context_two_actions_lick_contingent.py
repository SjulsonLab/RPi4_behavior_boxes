#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# python3: self_admin_task_context.py
"""
author: Mitch Farrell
date: 2023-04-22
name: self_admin_task_context_two_actions_lick_contingent.py
goal: expand self-admin task to include contextual/probabilistic components, with two lick actions, and reward contingent on lick
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


class SelfAdminTaskContextTwoActionsLickContingent(object):
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
            State(name="ContextA",
                  on_enter=["enter_ContextA"],
                  on_exit=["exit_ContextA"]),
            State(name="ContextB",
                  on_enter=["enter_ContextB"],
                  on_exit=["exit_ContextB"]),
            Timeout(name="ContextC_from_ContextA",
                    on_enter=["enter_ContextC_from_ContextA"],
                    on_exit=["exit_ContextC_from_ContextA"],
                    timeout=self.session_info['ContextC_time'],
                    on_timeout=['switch_to_ContextB']),
            Timeout(name="ContextC_from_ContextB",
                    on_enter=["enter_ContextC_from_ContextB"],
                    on_exit=["exit_ContextC_from_ContextB"],
                    timeout = self.session_info['ContextC_time'],
                    on_timeout=['switch_to_ContextA']),
            State(name="lick_LED_ContextA",
                    on_enter=["enter_lick_LED_ContextA"],
                    on_exit=["exit_lick_LED_ContextA"]),
            State(name="lick_LED_ContextB",
                    on_enter=["enter_lick_LED_ContextB"],
                    on_exit=["exit_lick_LED_ContextB"])
                ]

        # create a while loop that runs if State == ContextB or lick_LED_ContextB
        # create a different while loop that runs if State == ContextA or lick_LED_ContextB
        # this whole while loop lasts as long as
        self.transitions = [
            ['start_trial_logic', 'standby', 'ContextB'],  # format: ['trigger', 'origin', 'destination']

            ['switch_to_ContextC_from_ContextA', 'ContextA', 'ContextC_from_ContextA'],
            ['switch_to_ContextC_from_ContextB', 'ContextB', 'ContextC_from_ContextB'],

            ['switch_to_ContextB', 'ContextC_from_ContextA', 'ContextB'],
            ['switch_to_ContextA', 'ContextC_from_ContextB', 'ContextA'],

            ['switch_to_ContextC_from_lick_LED_ContextA', 'lick_LED_ContextA', 'ContextC_from_ContextA'],
            ['switch_to_ContextC_from_lick_LED_ContextB', 'lick_LED_ContextB', 'ContextC_from_ContextB'],

            ['switch_to_lick_LED_ContextA_from_ContextA', 'ContextA', 'lick_LED_ContextA'],
            ['switch_to_lick_LED_ContextB_from_ContextB', 'ContextB', 'lick_LED_ContextB'],

            ['switch_to_ContextA_from_lick_LED_ContextA', 'lick_LED_ContextA', 'ContextA'],
            ['switch_to_ContextB_from_lick_LED_ContextB', 'lick_LED_ContextB', 'ContextB']
        ]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='standby'  # STARTS IN STANDBY MODE
            )

    # trial statistics
        self.LED_on_time_plus_LED_duration = 0
        self.trial_running = False
        self.innocent = True
        self.trial_number = 0
        self.error_count = 0
        self.error_list = []
        self.error_repeat = False
        self.lever_pressed_time = 0.0
        self.lever_press_interval = self.session_info["lever_press_interval"]
        # self.reward_time_start = None # for reward_available state time keeping purpose
        self.reward_time = 10  # sec. could be incorporate into the session_info; available time for reward
        self.reward_times_up = False
        self.reward_pump1 = self.session_info["reward_pump1"]  # update this in session_info
        self.reward_pump2 = self.session_info['reward_pump2']  # update this in session_info
        self.reward_size1 = self.session_info["reward_size1"]  # update this in session_info
        self.reward_size2 = self.session_info['reward_size2']  # update this in session_info

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
        self.right_error_entry = False
        self.left_error_entry = False

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
        if self.state == "standby":
            pass
        elif self.state == 'ContextA':  # if in ContextA
            self.trial_running = False
            print('in ContextA loop')
            ContextA_time = time.time()  # assign the context switch time to this variable
            while time.time() - ContextA_time <= self.session_info['ContextA_time']:  # need to be able to jump out of this loop even in a below while loop; runs when ContextB_duration hasn't elapsed
                self.right_error_entry = False
                self.left_error_entry = False
                if self.box.event_list:
                    self.event_name = self.box.event_list.popleft()
                else:
                    self.event_name = ''
                if self.event_name == "reserved_rx1_pressed":  # if an active lever press detected
                    print('active press within ContextA loop')
                    lever_pressed_time_temp = time.time()  # assign the current lever press to the current time; used to prevent repeated presses
                    lever_pressed_dt = lever_pressed_time_temp - self.lever_pressed_time  # used to check previous rewarded lever time
                    if lever_pressed_dt >= self.lever_press_interval:  # if the last rewarded press occurred more than 1s ago, then turn LED on
                        self.switch_to_lick_LED_ContextA_from_ContextA()  # switches state to lick_LED state from ContextB
                        self.LED_on_time_plus_LED_duration = time.time() + self.session_info['LED_duration']  # add this to session info; dicates how long the LED will remain on in the absence of a lick
                        while ((self.LED_on_time_plus_LED_duration - time.time()) > 0) and (time.time() - ContextA_time <= self.session_info['ContextA_time']) and (self.state == 'lick_LED_ContextA'):
                            if self.box.event_list:
                                self.event_name = self.box.event_list.popleft()
                            else:
                                self.event_name = '' # while loop states the current time the LED time hasn't elapsed AND ContextB_duration hasn't elapsed
                            if self.event_name == 'right_entry' and self.left_error_entry == False:  # if left entry detected, and there wasn't already a right_entry during this LED period
                                if random.random() <= self.session_info['ContextA_reward_probability']:  # randomly dispense reward based on the ContextB_reward_probability
                                    print('ContextA_reward_delivered')
                                    self.pump.reward(self.reward_pump1, self.reward_size1) # reward delivery based on pump number and reward size
                                    self.lever_pressed_time = lever_pressed_time_temp  # this is used for subsequent lever presses
                                    self.total_reward += 1
                                    self.switch_to_ContextA_from_lick_LED_ContextA()  # does this need a conditional statement? or can this just be as it is
                            elif self.event_name == 'left_entry':
                                self.box.cueLED1.off()  # don't switch the state; but need to turn the LEDs off
                                self.box.cueLED2.off()
                                self.left_entry_error = True  # need a boolean to say whether a right_entry occurred during the current LED block
                        if (time.time() - ContextA_time) >= self.session_info['ContextA_time']:
                            self.switch_to_ContextC_from_lick_LED_ContextA()
                        elif (time.time() - LED_on_time_plus_LED_duration) > self.session_info['LED_duration']:
                            self.switch_to_ContextA_from_lick_LED_ContextA()
                    else:
                        pass
                else:
                    pass
            if self.state != 'ContextC_from_ContextA':  # exiting out of the nested while loop puts you in one of a few states; exiting out of the outer while loop will initiate a transition to ContextC_from_ContextB IF not already in that state from the above nested while loop
                self.switch_to_ContextC_from_ContextA()
        elif self.state == 'ContextB':  # if in ContextB
            self.trial_running = False
            print('in ContextB loop')
            ContextB_time = time.time()  # assign the context switch time to this variable
            while time.time() - ContextB_time <= self.session_info['ContextB_time']:  # need to be able to jump out of this loop even in a below while loop; runs when ContextB_duration hasn't elapsed
                self.right_error_entry = False
                self.left_error_entry = False
                if self.box.event_list:
                    self.event_name = self.box.event_list.popleft()
                else:
                    self.event_name = ''
                if self.event_name == "reserved_rx1_pressed":  # if an active lever press detected
                    print('active press within ContextB loop')
                    lever_pressed_time_temp = time.time()  # assign the current lever press to the current time; used to prevent repeated presses
                    lever_pressed_dt = lever_pressed_time_temp - self.lever_pressed_time  # used to check previous rewarded lever time
                    if lever_pressed_dt >= self.lever_press_interval:  # if the last rewarded press occurred more than 1s ago, then turn LED on
                        self.switch_to_lick_LED_ContextB_from_ContextB()  # switches state to lick_LED state from ContextB
                        self.LED_on_time_plus_LED_duration = time.time() + self.session_info['LED_duration']  # add this to session info; dicates how long the LED will remain on in the absence of a lick
                        while ((self.LED_on_time_plus_LED_duration - time.time()) > 0) < self.session_info['LED_duration']) and (time.time() - ContextB_time <= self.session_info['ContextB_time']) and (self.state == 'lick_LED_ContextB'):
                            if self.box.event_list:
                                self.event_name = self.box.event_list.popleft()
                            else:
                                self.event_name = ''  # while loop states the current time the LED time hasn't elapsed AND ContextB_duration hasn't elapsed
                            if self.event_name == 'left_entry' and self.right_error_entry == False:  # if left entry detected, and there wasn't already a right_entry during this LED period
                                if random.random() <= self.session_info['ContextB_reward_probability']:  # randomly dispense reward based on the ContextB_reward_probability
                                    print('ContextB_reward_delivered')
                                    self.pump.reward(self.reward_pump2, self.reward_size2)  # reward delivery based on pump number and reward size
                                    self.lever_pressed_time = lever_pressed_time_temp  # this is used for subsequent lever presses
                                    self.total_reward += 1
                                    self.switch_to_ContextB_from_lick_LED_ContextB()
                            elif self.event_name == 'right_entry':
                                self.box.cueLED1.off()  # don't switch the state; but need to turn the LEDs off
                                self.box.cueLED2.off()
                                self.right_entry_error = True #in the above if X and Y statement, this prevents reward from being dispensed if a right entry occurs during the LED period
                        if (time.time() - ContextB_time) >= self.session_info['ContextB_time']:
                            self.switch_to_ContextC_from_lick_LED_ContextB()
                        elif (time.time() - LED_on_time_plus_LED_duration) > self.session_info['LED_duration']:
                            self.switch_to_ContextB_from_lick_LED_ContextB()
                    else:
                        pass
                else:
                    pass
            if self.state != 'ContextC_from_ContextB':  # exiting out of the nested while loop puts you in one of a few states; exiting out of the outer while loop will initiate a transition to ContextC_from_ContextB IF not already in that state from the above nested while loop
                self.switch_to_ContextC_from_ContextB()
        else:
            pass
        self.box.check_keybd()

    def LED_off(self):
        logging.info(";" + str(time.time()) + ";[transition];LED_off;" + str(self.error_repeat))
        self.box.cueLED1.off()  # turn on LED which signals lick choice available
        self.box.cueLED2.off()

    def enter_lick_LED_ContextA(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_lick_LED_ContextA;" + str(self.error_repeat))
        self.box.cueLED1.on()  # turn on LED which signals lick choice available
        self.box.cueLED2.on()

    def exit_lick_LED_ContextA(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_lick_LED_ContextA;" + str(self.error_repeat))
        self.box.cueLED1.off()  # turn on LED which signals lick choice available
        self.box.cueLED2.off()

    def enter_lick_LED_ContextB(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_lick_LED_ContextB;" + str(self.error_repeat))
        self.box.cueLED1.on()  # turn on LED which signals lick choice available
        self.box.cueLED2.on()

    def exit_lick_LED_ContextB(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_lick_LED_ContextB;" + str(self.error_repeat))
        self.box.cueLED1.off()  # turn on LED which signals lick choice available
        self.box.cueLED2.off()

    def exit_standby(self):
        # self.error_repeat = False
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(self.error_repeat))
        self.box.event_list.clear()

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

    def exit_ContextC_from_ContextA(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextC_from_ContextA;" + str(self.error_repeat))
        self.box.event_list.clear()

    def enter_ContextC_from_ContextB(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextC_from_ContextB;" + str(self.error_repeat))
        self.box.sound1.off()  # INACTIVATE SOUND CUE#

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

