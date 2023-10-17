#!/usr/bin/env python
# coding: utf-8

# In[ ]:

# python3: remi_self_admin_lever_within_session_reinstatement_task.py
"""
author: Mitch Farrell
date: 2023-10-11
name: remi_self_admin_lever_within_session_reinstatement_task.py
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

class RemiSelfAdminLeverWithinSessionReinstatementTask(object):
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
            State(name='extinction',
                    on_enter=['enter_extinction'],
                    on_exit=['exit_extinction']),
            State(name='reinstatement',
                  on_enter=['enter_reinstatement'],
                  on_exit=['exit_reinstatement'])]

        self.transitions = [
            ['start_trial_logic', 'standby', 'reward_available'],  # format: ['trigger', 'origin', 'destination']

            ['switch_to_extinction', 'reward_available', 'extinction'],
            ['switch_to_reinstatement', 'extinction', 'reinstatement'],

            ['end_task', ['reward_available', 'extinction', 'reinstatement'], 'standby']]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='standby'
        )

        # trial statistics
        self.start_time = 0
        self.end_reward_available = 0
        self.end_extinction = 0
        self.end_reinstatement = 0
        self.next_available_reward_time = 0
        self.trial_running = False
        self.innocent = True
        self.trial_number = 0
        self.error_count = 0
        self.error_list = []
        self.error_repeat = False
        self.entry_time = 0.0
        self.entry_interval = self.session_info["entry_interval"] #update lever_press_interval to entry_interval--make this 3s instead of 1s
        self.reward_time = 10
        self.reward_times_up = False
        self.reward_pump1 = self.session_info["reward_pump1"]
        self.reward_pump2 = self.session_info['reward_pump2']

        self.reward_size1 = self.session_info["reward_size1"] #large, right
        self.reward_size2 = self.session_info['reward_size2'] #small, left
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
        self.syringe_pump = LED(17)
        self.reward_list = []

        try:
            self.lick_threshold = self.session_info["lick_threshold"]
        except:
            print("No lick_threshold defined in session_info. Therefore, default defined as 2 \n")
            self.lick_threshold = 1

        # session_statistics
        self.total_reward = 0
    def reward(self):  # prototype mouse weight equals 30
        infusion_duration = (self.session_info['weight'] / 30)
        self.syringe_pump.blink(infusion_duration, 0.1, 1)
        self.reward_list.append(("syringe_pump_reward", infusion_duration))
        logging.info(";" + str(time.time()) + ";[reward];syringe_pump_reward" + str(infusion_duration))
    def fill_cath(self):
        self.syringe_pump.blink(2.2, 0.1, 1) #5ul/second, calculated cath holds ~11.74ul; 2.2seconds delivers ~12ul into cath
        logging.info(";" + str(time.time()) + ";[reward];catheter_filled_with_~12ul;" + '2.2_second_infusion')

    def run(self):
        if self.state == "standby":
            pass
        elif self.state == 'reward_available':
            self.end_reward_available = self.start_time + 60 #1800
            self.next_available_reward_time = 0
            self.trial_running = False
            while time.time() < self.end_reward_available:
                if time.time() > self.next_available_reward_time:
                    self.box.event_list.clear()
                    self.box.sound1.off()
                    self.box.cueLED2.on()
                    self.reward_available_bool = True
                    while self.reward_available_bool and time.time() < self.end_reward_available:
                        if self.box.event_list:
                            self.event_name = self.box.event_list.popleft()
                        else:
                            self.event_name = ''
                        if self.event_name == 'reserved_rx1_pressed':
                            self.prior_reward_time = time.time()
                            self.next_available_reward_time = self.prior_reward_time + 20
                            self.reward_available_bool = False
                            self.reward()
                            self.box.cueLED2.off()
                            self.box.sound1.on()
            if time.time() >= self.end_reward_available:
                self.switch_to_extinction()
        elif self.state == 'extinction':
            self.end_extinction = self.start_time + 120 #3600
            self.next_available_reward_time = 0
            self.box.sound1.off()
            self.box.cueLED2.off()
            self.trial_running = False
            while time.time() < self.end_extinction:
                if time.time() > self.next_available_reward_time:
                    self.box.event_list.clear()
                    # self.box.cueLED2.on()
                    self.reward_available_bool = True
                    while self.reward_available_bool and time.time() < self.end_extinction:
                        if self.box.event_list:
                            self.event_name = self.box.event_list.popleft()
                        else:
                            self.event_name = ''
                        if self.event_name == 'reserved_rx1_pressed':
                            self.prior_reward_time = time.time()
                            self.next_available_reward_time = self.prior_reward_time + 20
                            self.reward_available_bool = False
                            logging.info(";" + str(time.time()) + ";[reward];extinction_no_reward")
            if time.time() >= self.end_extinction:
                self.switch_to_reinstatement()
        elif self.state == 'reinstatement':
            self.end_reinstatement = self.start_time + 180 #5400
            self.next_available_reward_time = 0
            self.trial_running = False
            while time.time() < self.end_reinstatement:
                if time.time() > self.next_available_reward_time:
                    self.box.event_list.clear()
                    self.box.sound1.off()
                    self.box.cueLED2.on()
                    self.reward_available_bool = True
                    while self.reward_available_bool and time.time() < self.end_reinstatement:
                        if self.box.event_list:
                            self.event_name = self.box.event_list.popleft()
                        else:
                            self.event_name = ''
                        if self.event_name == 'reserved_rx1_pressed':
                            self.prior_reward_time = time.time()
                            self.next_available_reward_time = self.prior_reward_time + 20
                            self.reward_available_bool = False
                            logging.info(";" + str(time.time()) + ";[reward];reinstatement_no_reward")
                            self.box.cueLED2.off()
                            self.box.sound1.on()

    def enter_standby(self):
        # self.error_repeat = False
        logging.info(";" + str(time.time()) + ";[transition];enter_standby;")
        self.trial_running = False
        self.box.event_list.clear()
    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;")
        self.start_time = time.time()
        self.box.event_list.clear()
        self.fill_cath()

    def enter_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_reward_available;")
        self.box.event_list.clear()
        self.trial_running = True
    def exit_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_reward_available;")
        self.box.event_list.clear()

    def enter_extinction(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_extinction;")
        self.trial_running = True
        self.box.event_list.clear()

    def exit_extinction(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_extinction;")
        self.box.event_list.clear()

    def enter_reinstatement(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_reinstatement;")
        self.trial_running = True
        self.box.event_list.clear()

    def exit_reinstatement(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_reinstatement;")
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
        self.box.cueLED2.off()

