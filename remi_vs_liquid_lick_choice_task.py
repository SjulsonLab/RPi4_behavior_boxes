#DRAFT


#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# python3: remi_vs_liquid_lick_choice_task.py
"""
author: Mitch Farrell
date: 2024-03-06
name: remi_vs_liquid_lick_choice_task.py
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

class RemiVSLiquidLickChoiceTask(object):
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
                  on_enter=['end_task'],
                  on_exit=["exit_standby"]),

            State(name="free_choice",
                  on_enter=["enter_free_choice"],
                  on_exit=["exit_free_choice"]),
            State(name='remi_forced',
                  on_enter=['enter_remi_forced'],
                  on_exit=['exit_remi_forced']),
            State(name='liquid_forced',
                  on_enter=['enter_liquid_forced'],
                  on_exit=['exit_liquid_forced']),

            State(name='free_choice_remi_delay',
                  on_enter=['enter_free_choice_remi_delay'],
                  on_exit=['exit_free_choice_remi_delay']),
            State(name='free_choice_liquid_delay',
                  on_enter=['enter_free_choice_liquid_delay'],
                  on_exit=['exit_free_choice_liquid_delay']),
            State(name='remi_forced',
                  on_enter=['enter_remi_forced_delay'],
                  on_exit=['exit_remi_forced_delay']),
            State(name='liquid_forced_delay',
                  on_enter=['enter_liquid_forced_delay'],
                  on_exit=['exit_liquid_forced_delay']),

            Timeout(name='ITI',
                    on_enter=['enter_ITI'],
                    on_exit=['exit_ITI'],
                    timeout = self.session_info['ITI'], #session_info
                    on_timeout = ['switch_to_next_phase'])] #?????????

        self.transitions = [
            ['start_trial_logic', 'standby', ['free_choice', 'remi_forced', 'liquid_forced']],  # format: ['trigger', 'origin', 'destination']

            ['switch_to_free_choice', 'ITI', 'free_choice'],
            ['switch_to_remi_forced', 'ITI', 'remi_forced'],
            ['switch_to_liquid_forced', 'ITI', 'liquid_forced'],

            ['switch_to_free_choice_remi_delay', 'free_choice', 'free_choice_remi_delay'],
            ['switch_to_free_choice_liquid_delay', 'free_choice', 'free_choice_liquid_delay'],

            ['switch_to_remi_forced_delay', 'remi_forced', 'remi_forced_delay'],
            ['switch_to_liquid_forced_delay', 'liquid_forced', 'liquid_forced_delay'],

            ['switch_to_ITI', ['free_choice', 'remi_forced', 'liquid_forced', 'free_choice_delay',
                               'remi_forced_delay','liquid_forced_delay'], 'ITI'],

            ['end_task', ['free_choice','remi_forced','liquid_forced', 'ITI'], 'standby']]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='standby'
            )

    # trial statistics
        self.trial_time =
        self.trial_duration =


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
        elif self.state == 'free_choice':
            self.right_entry_count = 0
            self.left_entry_count = 0
            self.trial_end = time.time() + self.trial_duration
            self.trial_running = False
            while self.trial_end > time.time() and self.state == 'free_choice':
                if self.box.event_list:
                    self.event_name = self.box.event_list.popleft()
                else:
                    self.event_name = ''
                if self.event_name == "right_entry": #assume liquid is left and remi is right
                    self.switch_to_free_choice_remi_delay()
                if self.event_name == "left_entry":
                    self.switch_to_free_choice_liquid_delay()







        elif self.state == 'remi_forced':
            self.current_time = time.time()
            self.motivation_phase_end = time.time() + 10
            self.right_entry_count = 0
            self.trial_running = False
            while self.motivation_phase_end > self.current_time and self.state == 'right_motivation_phase':
                self.current_time = time.time()
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
            if self.state != 'timeout':
                self.switch_to_timeout()
        elif self.state == 'liquid_forced':
            self.current_time = time.time()
            self.motivation_phase_end = time.time() + 10
            self.left_entry_count = 0
            self.trial_running = False
            while self.motivation_phase_end > self.current_time and self.state == 'left_motivation_phase':
                self.current_time = time.time()
                if self.box.event_list:
                    self.event_name = self.box.event_list.popleft()
                else:
                    self.event_name = ''
                if self.event_name == "left_entry":
                    self.left_entry_count += 1
                if self.left_entry_count >= self.left_motivation_phase_FR:
                    self.pump.reward(self.reward_pump2, self.reward_size2)
                    if self.reward_size2 > 0:
                        self.reward_size2 = self.reward_size2 - 1
                    if self.reward_size1 < 5:
                        self.reward_size1 = self.reward_size1 + 1
                    self.switch_to_timeout()
            if self.state != 'timeout':
                self.switch_to_timeout()

    def enter_standby(self):
        # self.error_repeat = False
        logging.info(";" + str(time.time()) + ";[transition];enter_standby;" + str(self.error_repeat))
        self.trial_running = False
        self.box.event_list.clear()
    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(self.error_repeat))
        self.box.event_list.clear()

    def enter_free_choice(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_free_choice;" + str(self.error_repeat))
        self.trial_running = True
        self.box.cueLED1.on()
        self.box.cueLED2.on()
    def exit_free_choice(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_free_choice;" + str(self.error_repeat))
        self.box.event_list.clear()

    def enter_remi_forced(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_remi_forced;" + str(self.error_repeat))
        self.trial_running = True
        self.box.cueLED1.on()
        self.box.cueLED2.on()
    def exit_remi_forced(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_remi_forced;" + str(self.error_repeat))
        self.box.event_list.clear()
        self.box.cueLED2.off()
        self.box.sound1.off()

    def enter_liquid_forced(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_liquid_forced;" + str(self.error_repeat))
        self.trial_running = True
        self.box.cueLED1.on()
        self.box.cueLED2.on()
    def exit_liquid_forced(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_liquid_forced;" + str(self.error_repeat))
        self.box.event_list.clear()
        self.box.cueLED1.off()
        self.box.sound1.off()

    def enter_free_choice_remi_delay(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_free_choice_remi_delay;" + str(self.error_repeat))
        self.box.event_list.clear()
        self.box.cueLED1.off()
        self.box.cueLED2.off()
        self.box.sound1.off()
        self.trial_running = False
    def exit_free_choice_remi_delay(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_free_choice_remi_delay;" + str(self.error_repeat))
        self.box.event_list.clear()

    def enter_free_choice_liquid_delay(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_free_choice_liquid_delay;" + str(self.error_repeat))
        self.trial_running = True
        self.box.cueLED2.off()
        self.box.sound1.on()
    def exit_free_choice_liquid_delay(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_free_choice_liquid_delay;" + str(self.error_repeat))
        self.box.event_list.clear()
        self.box.cueLED1.off()
        self.box.sound1.off()

    def enter_remi_forced_delay(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_remi_forced_delay;" + str(self.error_repeat))
        self.trial_running = True
        self.box.cueLED2.off()
        self.box.sound1.on()
    def exit_remi_forced_delay(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_remi_forced_delay;" + str(self.error_repeat))
        self.box.event_list.clear()
        self.box.cueLED1.off()
        self.box.sound1.off()

    def enter_liquid_forced_delay(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_liquid_forced_delay;" + str(self.error_repeat))
        self.trial_running = True
        self.box.cueLED2.off()
        self.box.sound1.on()
    def exit_liquid_forced_delay(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_liquid_forced_delay;" + str(self.error_repeat))
        self.box.event_list.clear()
        self.box.cueLED1.off()
        self.box.sound1.off()

    def enter_ITI(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_ITI;" + str(self.error_repeat))
        self.trial_running = True
        self.box.cueLED2.off()
        self.box.sound1.on()
    def exit_ITI(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ITI;" + str(self.error_repeat))
        self.box.event_list.clear()
        self.box.cueLED1.off()
        self.box.sound1.off()












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

