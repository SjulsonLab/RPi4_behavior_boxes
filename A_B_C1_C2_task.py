#!/usr/bin/env python
# coding: utf-8

# In[ ]:

# python3: A_B_C1_C2_task.py
"""
author: Mitch Farrell
date: 2023-06-09
name: A_B_C1_C2_task.py
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
import random

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

class A_B_C1_C2_task(object):
    def __init__(self, **kwargs):  # name and session_info should be provided as kwargs
        # Function to generate random list with no 3 in a row of same kind and no two consecutive Contexts
        self.context_order_list = []
        self.last_element = -1
        while len(self.context_order_list) < 80:
            self.k = random.randint(0, 3)
            if self.k != self.last_element:
                self.context_order_list.append(self.k)
                self.last_element = self.k

        self.context_timing_list = []
        self.context_time_pool = [15, 20, 25, 30, 35] * 16
        for i in range(len(self.context_order_list)):
            random.shuffle(self.context_time_pool)
            self.context_timing_list.append(self.context_time_pool.pop())

        self.intercontext_interval_time = [10, 15, 20, 25, 30] * 16
        self.intercontext_interval_list = self.intercontext_interval_time
        random.shuffle(self.intercontext_interval_list)

        self.context_order_list_names = self.context_order_list.copy()
        for idx, element in enumerate(self.context_order_list_names):
            if element == 0:
                self.context_order_list_names[idx] = 'ContextA'
            elif element == 1:
                self.context_order_list_names[idx] = 'ContextB'
            elif element == 2:
                self.context_order_list_names[idx] = 'ContextC1'
            elif element == 3:
                self.context_order_list_names[idx] = 'ContextC2'

        self.full_task_list = []
        for i in range(len(self.context_order_list)):
            self.full_task_list.append(self.context_timing_list[i])
            self.full_task_list.append(self.intercontext_interval_list[i])

        self.full_task_names_and_times = []
        for i in range(len(self.context_order_list_names)):
            self.full_task_names_and_times.append([self.context_order_list_names[i], self.context_timing_list[i]])
            self.full_task_names_and_times.append(['intercontext_interval', self.intercontext_interval_list[i]])

        self.full_task_names_and_times.append(['task_end', 60])

        logging.info(self.full_task_names_and_times)

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
            State(name="ContextA",
                  on_enter=["enter_ContextA"],
                  on_exit = ['exit_ContextA']),
            State(name="ContextB",
                  on_enter=["enter_ContextB"],
                  on_exit=['exit_ContextB']),
            State(name="ContextC1",
                  on_enter=["enter_ContextC1"],
                  on_exit=['exit_ContextC1']),
            State(name="ContextC2",
                  on_enter=["enter_ContextC2"],
                  on_exit=['exit_ContextC2']),
            State(name="intercontext_interval",
                    on_enter=["enter_intercontext_interval"],
                    on_exit=["exit_intercontext_interval"])
        ]

        self.transitions = [
            ['switch_to_intercontext_interval', ['ContextA','ContextB', 'ContextC1','ContextC2'], 'intercontext_interval'],
            ['end_task', ['ContextA','ContextB','ContextC1', 'ContextC2', 'intercontext_interval'], 'standby'],
            ['switch_to_ContextA', 'intercontext_interval', 'ContextA'],
            ['switch_to_ContextB', 'intercontext_interval', 'ContextB'],
            ['switch_to_ContextC1', 'intercontext_interval', 'ContextC1'],
            ['switch_to_ContextC2', 'intercontext_interval', 'ContextC2']

        ]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='standby'
            )

        self.machine.add_transition('start_trial_logic', 'standby', 'ContextA', conditions='start_in_ContextA')
        self.machine.add_transition('start_trial_logic', 'standby', 'ContextB', conditions='start_in_ContextB')
        self.machine.add_transition('start_trial_logic', 'standby', 'ContextC1', conditions='start_in_ContextC1')
        self.machine.add_transition('start_trial_logic', 'standby', 'ContextC2', conditions='start_in_ContextC2')

    # trial statistics
        self.intercontext_interval_time = 0
        self.current_state_time = 0
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
        self.ContextC1_time = 0
        self.ContextC2_time = 0

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
        elif self.state == 'intercontext_interval':
            self.trial_running = False
            self.intercontext_interval_time = time.time()
            while (time.time() - self.intercontext_interval_time) <= self.current_state_time:
                pass
            self.switch_to_ContextA_B_C1_C2()
        elif self.state == 'ContextA':
            self.trial_running = False
            self.ContextA_time = time.time()
            self.LED_bool = False
            self.prior_reward_time = 0
            while (time.time() - self.ContextA_time) <= self.current_state_time:  # need to be able to jump out of this loop even in a below while loop; runs when ContextB_duration hasn't elapsed
                if not self.LED_bool:
                    if self.prior_reward_time == 0 or time.time() - self.prior_reward_time > self.random_ITI: #first trial after entering the state
                        self.box.cueLED1.on()
                        self.box.cueLED2.on()
                        self.LED_on_time = time.time()
                        self.LED_bool = True
                        self.box.event_list.clear()
                    while self.LED_bool and time.time() - self.ContextA_time <= self.current_state_time:
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
                            logging.info(";" + str(time.time()) + ";[transition];current_ITI_" + str(self.random_ITI))
                            self.LED_bool = False
                        elif self.event_name == 'right_entry' and time.time() - self.LED_on_time > self.LED_delay_time:
                            self.box.cueLED1.off()
                            self.box.cueLED2.off()
                            self.pump.reward(self.reward_pump1, self.reward_size1)
                            self.prior_reward_time = time.time()
                            self.random_ITI = random.randint(2, 4)  # 2,3,4
                            logging.info(";" + str(time.time()) + ";[transition];current_ITI_" + str(self.random_ITI))
                            self.LED_bool = False
            if (time.time() - self.ContextA_time) >= self.current_state_time:
                self.switch_to_intercontext_interval()
        elif self.state == 'ContextB':
            self.trial_running = False
            self.ContextB_time = time.time()  # assign the context switch time to this variable
            self.LED_bool = False
            self.prior_reward_time = 0
            while (time.time() - self.ContextB_time) <= self.current_state_time:
                if self.prior_reward_time == 0 or time.time() - self.prior_reward_time > self.random_ITI:  # first trial after entering the state
                    self.box.cueLED1.on()
                    self.box.cueLED2.on()
                    self.LED_on_time = time.time()
                    self.LED_bool = True
                    self.box.event_list.clear()
                    while self.LED_bool and time.time() - self.ContextB_time <= self.current_state_time:
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
                            logging.info(";" + str(time.time()) + ";[transition];current_ITI_" + str(self.random_ITI))
                            self.LED_bool = False
                        elif self.event_name == 'right_entry' and time.time() - self.LED_on_time > self.LED_delay_time:
                            self.box.cueLED1.off()
                            self.box.cueLED2.off()
                            self.pump.reward(self.reward_pump1, self.reward_size4)
                            self.prior_reward_time = time.time()
                            self.random_ITI = random.randint(2, 4)  # 2,3,4
                            logging.info(";" + str(time.time()) + ";[transition];current_ITI_" + str(self.random_ITI))
                            self.LED_bool = False
            if (time.time() - self.ContextB_time) >= self.current_state_time:
                self.switch_to_intercontext_interval()
        elif self.state == 'ContextC1':
            self.trial_running = False
            self.ContextC1_time = time.time()
            self.LED_bool = False
            self.prior_reward_time = 0
            while (time.time() - self.ContextC1_time) <= self.current_state_time:
                if not self.LED_bool:
                    if self.prior_reward_time == 0 or time.time() - self.prior_reward_time > self.random_ITI: #first trial after entering the state
                        self.box.cueLED1.on()
                        self.box.cueLED2.on()
                        self.LED_on_time = time.time()
                        self.LED_bool = True
                        self.box.event_list.clear()
                    while self.LED_bool and time.time() - self.ContextC1_time <= self.current_state_time:
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
                            logging.info(";" + str(time.time()) + ";[transition];current_ITI_" + str(self.random_ITI))
                            self.LED_bool = False
                        elif self.event_name == 'right_entry' and time.time() - self.LED_on_time > self.LED_delay_time:
                            self.box.cueLED1.off()
                            self.box.cueLED2.off()
                            self.pump.reward(self.reward_pump1, self.reward_size1)
                            self.prior_reward_time = time.time()
                            self.random_ITI = random.randint(2, 4)  # 2,3,4
                            logging.info(";" + str(time.time()) + ";[transition];current_ITI_" + str(self.random_ITI))
                            self.LED_bool = False
            if (time.time() - self.ContextC1_time) >= self.current_state_time:
                self.switch_to_intercontext_interval()
        elif self.state == 'ContextC2':
            self.trial_running = False
            self.ContextC2_time = time.time()  # assign the context switch time to this variable
            self.LED_bool = False
            self.prior_reward_time = 0
            while (time.time() - self.ContextC2_time) <= self.current_state_time:
                if self.prior_reward_time == 0 or time.time() - self.prior_reward_time > self.random_ITI:  # first trial after entering the state
                    self.box.cueLED1.on()
                    self.box.cueLED2.on()
                    self.LED_on_time = time.time()
                    self.LED_bool = True
                    self.box.event_list.clear()
                    while self.LED_bool and time.time() - self.ContextC2_time <= self.current_state_time:
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
                            logging.info(";" + str(time.time()) + ";[transition];current_ITI_" + str(self.random_ITI))
                            self.LED_bool = False
                        elif self.event_name == 'right_entry' and time.time() - self.LED_on_time > self.LED_delay_time:
                            self.box.cueLED1.off()
                            self.box.cueLED2.off()
                            self.pump.reward(self.reward_pump1, self.reward_size4)
                            self.prior_reward_time = time.time()
                            self.random_ITI = random.randint(2, 4)  # 2,3,4
                            logging.info(";" + str(time.time()) + ";[transition];current_ITI_" + str(self.random_ITI))
                            self.LED_bool = False
            if (time.time() - self.ContextC2_time) >= self.current_state_time:
                self.switch_to_intercontext_interval()
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

    def start_in_ContextC1(self):
        if self.full_task_names_and_times[self.trial_counter][0] == 'ContextC1':
            return True
        else:
            return False

    def start_in_ContextC2(self):
        if self.full_task_names_and_times[self.trial_counter][0] == 'ContextC2':
            return True
        else:
            return False

    def switch_to_ContextA_B_C1_C2(self):
        self.trial_counter += 1
        if self.full_task_names_and_times[self.trial_counter][0] == 'ContextA':
            self.switch_to_ContextA()
        elif self.full_task_names_and_times[self.trial_counter][0] == 'ContextB':
            self.switch_to_ContextB()
        elif self.full_task_names_and_times[self.trial_counter][0] == 'ContextC1':
            self.switch_to_ContextC1()
        elif self.full_task_names_and_times[self.trial_counter][0] == 'ContextC2':
            self.switch_to_ContextC2()

    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby")
        self.box.event_list.clear()

    def enter_ContextA(self):
        self.current_state_time = self.full_task_names_and_times[self.trial_counter][1]
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextA")
        self.box.sound1.blink(0.1, 0.1)
        logging.info(";" + str(time.time()) + ";[transition];current_state_and_duration_" +
                     str(self.full_task_names_and_times[self.trial_counter][0]) + '_' +
                     str(self.full_task_names_and_times[self.trial_counter][1]))
        if self.full_task_names_and_times[self.trial_counter][1] == 15:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[0],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 20:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[1],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 25:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[2],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 30:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[3],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 35:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[4],0)
        self.trial_running = True

    def exit_ContextA(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextA")
        self.box.sound1.off()
        self.box.cueLED1.off()
        self.box.cueLED2.off()
        self.box.event_list.clear()
        self.trial_counter += 1
        self.current_state_time = self.full_task_names_and_times[self.trial_counter][1]

    def enter_ContextB(self):
        self.current_state_time = self.full_task_names_and_times[self.trial_counter][1]
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextB")
        self.box.sound1.blink(0.2, 0.1)
        logging.info(";" + str(time.time()) + ";[transition];current_state_and_duration_" +
                     str(self.full_task_names_and_times[self.trial_counter][0]) + '_' +
                     str(self.full_task_names_and_times[self.trial_counter][1]))
        if self.full_task_names_and_times[self.trial_counter][1] == 15:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[5],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 20:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[6],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 25:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[7],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 30:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[8],0)
        elif self.full_task_names_and_times[self.trial_counter][1] == 35:
            self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[9],0)
        self.trial_running = True

    def exit_ContextB(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextB")
        self.box.sound1.off()
        self.box.cueLED1.off()
        self.box.cueLED2.off()
        self.box.event_list.clear()
        self.trial_counter += 1
        self.current_state_time = self.full_task_names_and_times[self.trial_counter][1]

    def enter_ContextC1(self):
        self.current_state_time = self.full_task_names_and_times[self.trial_counter][1]
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextC1")
        self.box.sound2.on()
        logging.info(";" + str(time.time()) + ";[transition];current_state_and_duration_" +
                     str(self.full_task_names_and_times[self.trial_counter][0]) + '_' +
                     str(self.full_task_names_and_times[self.trial_counter][1]))
        self.box.visualstim.myscreen.display_greyscale(self.session_info['gray_level']['default'])
        self.trial_running = True

    def exit_ContextC1(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextC1")
        self.box.sound2.off()
        self.box.cueLED1.off()
        self.box.cueLED2.off()
        self.box.event_list.clear()
        self.trial_counter += 1
        self.current_state_time = self.full_task_names_and_times[self.trial_counter][1]
        self.box.visualstim.myscreen.display_greyscale(0)

    def enter_ContextC2(self):
        self.current_state_time = self.full_task_names_and_times[self.trial_counter][1]
        logging.info(";" + str(time.time()) + ";[transition];enter_ContextC2")
        self.box.sound2.on()
        logging.info(";" + str(time.time()) + ";[transition];current_state_and_duration_" +
                     str(self.full_task_names_and_times[self.trial_counter][0]) + '_' +
                     str(self.full_task_names_and_times[self.trial_counter][1]))
        self.box.visualstim.myscreen.display_greyscale(self.session_info['gray_level']['default'])
        self.trial_running = True

    def exit_ContextC2(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_ContextC2")
        self.box.sound2.off()
        self.box.cueLED1.off()
        self.box.cueLED2.off()
        self.box.event_list.clear()
        self.trial_counter += 1
        self.current_state_time = self.full_task_names_and_times[self.trial_counter][1]
        self.box.visualstim.myscreen.display_greyscale(0)

    def enter_intercontext_interval(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_intercontext_interval")
        # logging.info(";" + str(time.time()) + ";[transition];enter_inter_" +
        #              str(self.full_task_names_and_times[self.trial_counter][0]) + '_' +
        #              str(self.full_task_names_and_times[self.trial_counter][1]))
        self.trial_running = True

    def exit_intercontext_interval(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_intercontext_interval")
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

