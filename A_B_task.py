#!/usr/bin/env python
# coding: utf-8

# In[ ]:

# python3: A_B_task.py
"""
author: Mitch Farrell
date: 2023-05-15
name: A_B_task.py
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
import random

# adding timing capability to the state machine
@add_state_features(Timeout)
class TimedStateMachine(Machine):
    pass

class A_B_task(object):
    def __init__(self, **kwargs):  # name and session_info should be provided as kwargs
        self.ContextA_time = [40, 50, 60, 70, 80]
        self.ContextB_time = [40, 50, 60, 70, 80]
        self.intercontext_interval_time = [20, 25, 30, 35, 40]

        # used to create the Context_order_list (40 elements, 0s and 1s, no three in a row)
        self.random_list = []
        while self.random_list.count(0) != 20 and self.random_list.count(1) != 20:
            self.random_list = []
            i = 0
            for p in range(40):
                k = random.randint(0, 1)
                try:
                    if (self.random_list[i - 1] == 1 and self.random_list[i - 2] == 1):
                        self.random_list.append(0)
                        i += 1
                    elif (self.random_list[i - 1] == 0 and self.random_list[i - 2] == 0):
                        self.random_list.append(1)
                        i += 1
                    else:
                        self.random_list.append(k)
                        i += 1
                except:
                    self.random_list.append(k)
                    i += 1
        self.Context_order_list = self.random_list
        self.Context_order_list_names = self.Context_order_list.copy()

        for idx, element in enumerate(self.Context_order_list_names):
            if element == 0:
                self.Context_order_list_names[idx] = 'ContextA'
            elif element == 1:
                self.Context_order_list_names[idx] = 'ContextB'

        self.full_task_list_names = []
        self.temp = [(self.full_task_list_names.append(self.Context_order_list_names[i]),
                      self.full_task_list_names.append('intercontext_interval')) for i in
                     range(len(self.Context_order_list_names))]

        self.ContextA_time_temp = self.ContextA_time
        self.ContextB_time_temp = self.ContextB_time
        random.shuffle(self.ContextA_time_temp)
        random.shuffle(self.ContextB_time_temp)

        i = 0
        self.Context_timing_list = []
        while len(self.Context_timing_list) < 40:
            if len(self.ContextA_time_temp) == 0:
                self.ContextA_time_temp = [40, 50, 60, 70, 80]
                random.shuffle(self.ContextA_time_temp)
            if len(self.ContextB_time_temp) == 0:
                self.ContextB_time_temp = [40, 50, 60, 70, 80]
                random.shuffle(self.ContextB_time_temp)
            if self.Context_order_list[i] == 0:
                self.temp_ContextA_var = self.ContextA_time_temp.pop()
                self.Context_timing_list.append(self.temp_ContextA_var)
            if self.Context_order_list[i] == 1:
                self.temp_ContextB_var = self.ContextB_time_temp.pop()
                self.Context_timing_list.append(self.temp_ContextB_var)
            i += 1

        # generates a random list of intercontext intervals with 8 of each duration
        self.intercontext_interval_list = []
        random.shuffle(self.intercontext_interval_time)

        while len(self.intercontext_interval_list) < 40:
            if len(self.intercontext_interval_time) == 0:
                self.intercontext_interval_time = [20, 25, 30, 35, 40]
                random.shuffle(self.intercontext_interval_time)
            self.temp_intercontext_interval_time = self.intercontext_interval_time.pop()
            self.intercontext_interval_list.append(self.temp_intercontext_interval_time)
            i += 1

        # interleaves the Context list with intercontext interval lists to create a full session (note that a context initiates the session)
        self.full_task_list = []
        self.temp_list = [
            (self.full_task_list.append(self.Context_timing_list[i]),
             self.full_task_list.append(self.intercontext_interval_list[i])) for i in
            range(len(self.Context_timing_list))]

        # Creates nested list containing the states and their respective durations
        self.full_task_names_and_times = []
        self.temp = [self.full_task_names_and_times.append([self.full_task_list_names[i], self.full_task_list[i]]) for i in
                range(len(self.full_task_list_names))]

        logging.info(self.full_task_names_and_times)
        print(f"This is the order of the Contexts and intercontext_intervals along with their respective durations: {self.full_task_names_and_times}")

        self.trial_counter = 0

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
            Timeout(name="ContextA",
                  on_enter=["enter_ContextA"],
                  timeout = self.full_task_names_and_times[self.trial_counter][1],
                  on_timeout = ['exit_ContextA']),
            Timeout(name="ContextB",
                  on_enter=["enter_ContextB"],
                  timeout=self.full_task_names_and_times[self.trial_counter][1],
                  on_timeout=['exit_ContextB']),
            Timeout(name="intercontext_interval",
                    on_enter=["enter_intercontext_interval"],
                    on_exit=["exit_intercontext_interval"],
                    timeout = 30,
                    on_timeout=['switch_to_ContextA/B'])]

        self.transitions = [
            ['switch_to_intercontext_interval', ['ContextA','ContextB'], 'intercontext_interval'],
            ['end_task', ['ContextA','ContextB','intercontext_interval'], 'standby']]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='standby'
            )

        self.machine.add_transition('start_trial_logic', 'standby', 'ContextA', conditions='start_in_ContextA')
        self.machine.add_transition('start_trial_logic', 'standby', 'ContextB', conditions='start_in_ContextB')
        self.machine.add_transition('switch_to_ContextA/B', 'intercontext_interval', 'ContextA', conditions = 'transition_to_ContextA')
        self.machine.add_transition('switch_to_ContextA/B', 'intercontext_interval', 'ContextB',conditions='transition_to_ContextB')

    # trial statistics
        self.random_ITI = random.randint(2, 4)
        self.LED_delay_time = 0.3
        self.LED_on_time = 0
        self.trial_running = False
        self.innocent = True
        self.trial_number = 0
        self.error_count = 0
        self.error_list = []
        self.error_repeat = False
        self.entry_time = 0.0
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
        elif self.state == 'ContextA':
            self.trial_running = False
            self.ContextA_time = time.time()
            self.LED_bool = False
            self.prior_reward_time = 0
            while time.time() - self.ContextA_time <= self.full_task_names_and_times[self.trial_counter][1] and self.state == 'ContextA':  # need to be able to jump out of this loop even in a below while loop; runs when ContextB_duration hasn't elapsed
                if not self.LED_bool:
                    if self.prior_reward_time == 0 or time.time() - self.prior_reward_time > self.random_ITI: #first trial after entering the state
                        self.box.cueLED1.on()
                        self.box.cueLED2.on()
                        self.LED_on_time = time.time()
                        self.LED_bool = True
                        self.box.event_list.clear()
                    while self.LED_bool and time.time() - self.ContextA_time <= self.full_task_names_and_times[self.trial_counter][1]:
                        if self.box.event_list:
                            self.event_name = self.box.event_list.popleft()
                        else:
                            self.event_name = ''
                        if self.event_name == "left_entry" and time.time() - self.LED_on_time > self.LED_delay_time:
                            self.box.cueLED1.off()
                            self.box.cueLED2.off()
                            self.pump.reward(self.reward_pump2, self.reward_size2)
                            self.prior_reward_time = time.time()
                            self.random_ITI = random.randint(2,4) #2,3,4
                            logging.info(";" + str(time.time()) + ";[transition];current_ITI;" + str(self.random_ITI))
                            self.LED_bool = False
                        elif self.event_name == 'right_entry' and time.time() - self.LED_on_time > self.LED_delay_time:
                            self.box.cueLED1.off()
                            self.box.cueLED2.off()
                            self.pump.reward(self.reward_pump1, self.reward_size1)
                            self.prior_reward_time = time.time()
                            self.random_ITI = random.randint(2, 4)  # 2,3,4
                            logging.info(";" + str(time.time()) + ";[transition];current_ITI;" + str(self.random_ITI))
                            self.LED_bool = False
        elif self.state == 'ContextB':
            self.trial_running = False
            self.ContextB_time = time.time()  # assign the context switch time to this variable
            self.LED_bool = False
            self.prior_reward_time = 0
            while time.time() - self.ContextB_time <= self.full_task_names_and_times[self.trial_counter][1] and self.state == 'ContextB':
                if self.prior_reward_time == 0 or time.time() - self.prior_reward_time > self.random_ITI:  # first trial after entering the state
                    self.box.cueLED1.on()
                    self.box.cueLED2.on()
                    self.LED_on_time = time.time()
                    self.LED_bool = True
                    self.box.event_list.clear()
                    while self.LED_bool and time.time() - self.ContextB_time <= self.full_task_names_and_times[self.trial_counter][1]:
                        if self.box.event_list:
                            self.event_name = self.box.event_list.popleft()
                        else:
                            self.event_name = ''
                        if self.event_name == "left_entry" and time.time() - self.LED_on_time > self.LED_delay_time:
                            self.box.cueLED1.off()
                            self.box.cueLED2.off()
                            self.pump.reward(self.reward_pump2, self.reward_size3)
                            self.prior_reward_time = time.time()
                            self.random_ITI = random.randint(2, 4)  # 2,3,4
                            logging.info(";" + str(time.time()) + ";[transition];current_ITI;" + str(self.random_ITI))
                            self.LED_bool = False
                        elif self.event_name == 'right_entry' and time.time() - self.LED_on_time > self.LED_delay_time:
                            self.box.cueLED1.off()self.in_loop_bool
                            self.box.cueLED2.off()
                            self.pump.reward(self.reward_pump1, self.reward_size4)
                            self.prior_reward_time = time.time()
                            self.random_ITI = random.randint(2, 4)  # 2,3,4
                            logging.info(";" + str(time.time()) + ";[transition];current_ITI;" + str(self.random_ITI))
                            self.LED_bool = False
    def start_in_ContextA(self):
        if self.full_task_names_and_times[self.trial_counter][0] == 'ContextA':
            return True
        else:
            return False
    def start_in_ContextB(self):
        if self.full_task_names_and_times[self.trial_counter][0] == 'ContextB':
            return True
        else:
            return False

    def transition_to_ContextA(self):
        # self.trial_counter += 1
        if self.full_task_names_and_times[self.trial_counter][0] == 'ContextA':
            return True
        else:
            return False
    def transition_to_ContextB(self):
        # self.trial_counter += 1
        if self.full_task_names_and_times[self.trial_counter][0] == 'ContextB':
            return True
        else:
            return False

    def exit_standby(self):
        # self.error_repeat = False
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(self.error_repeat))
        self.box.event_list.clear()

    def enter_ContextA(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextA;" + str(self.error_repeat))
        self.box.sound1.blink(0.1, 0.1)
        logging.info(";" + str(time.time()) + ";[transition];current_state_and_duration;" +
                     str(self.full_task_names_and_times[self.trial_counter][0]) + '_' +
                     str(self.full_task_names_and_times[self.trial_counter][1]))
        print(list(self.box.visualstim.gratings))
        if self.full_task_names_and_times[self.trial_counter][1] == 40:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[0],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 50:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[1],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 60:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[2],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 70:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[3],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 80:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[4],0)
        self.trial_running = True

    def exit_ContextA(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextA;" + str(self.error_repeat))
        self.box.sound1.off()
        self.box.cueLED1.off()
        self.box.cueLED2.off()
        self.box.event_list.clear()
        self.trial_counter += 1
        self.switch_to_intercontext_interval()

    def enter_ContextB(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextB;" + str(self.error_repeat))
        self.box.sound1.blink(0.2, 0.1)
        logging.info(";" + str(time.time()) + ";[transition];current_state_and_duration;" +
                     str(self.full_task_names_and_times[self.trial_counter][0]) + '_' +
                     str(self.full_task_names_and_times[self.trial_counter][1]))
        print(list(self.box.visualstim.gratings))
        if self.full_task_names_and_times[self.trial_counter][1] == 40:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[5],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 50:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[6],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 60:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[7],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 70:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[8],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 80:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[9],0)
        self.trial_running = True

    def exit_ContextB(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextB;" + str(self.error_repeat))
        self.box.sound1.off()
        self.box.cueLED1.off()
        self.box.cueLED2.off()
        self.box.event_list.clear()
        self.trial_counter += 1
        self.switch_to_intercontext_interval()

    def enter_intercontext_interval(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_intercontext_interval;" + str(self.error_repeat))
        # logging.info(";" + str(time.time()) + ";[transition];current_state_and_duration;" +
        #              str(self.full_task_names_and_times[self.trial_counter][0]) + '_' +
        #              str(self.full_task_names_and_times[self.trial_counter][1]))
        self.trial_running = False

    def exit_intercontext_interval(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_intercontext_interval;" + str(self.error_repeat))
        self.box.event_list.clear()
        self.trial_counter += 1

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

