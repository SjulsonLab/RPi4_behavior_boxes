#!/usr/bin/env python
# coding: utf-8

# python3: latent_inference_forage_task_three_states.py
"""
author: Mitch Farrell; edited Matthew Chin
last updated: 2024-01-24
name: latent_inference_forage_task_three_states.py
"""
from transitions import State, Machine
from task_protocol.base_classes import TimedStateMachine, Model

from icecream import ic
import logging
import time

import numpy as np

import logging.config
from collections import deque
from typing import Protocol, List, Tuple, Union

import logging.config
import threading

rng = np.random.default_rng()
RIGHT_IX = 0
LEFT_IX = 1


class LatentInferenceForageModel(Model):  # subclass from base task

    def __init__(self, session_info: dict):
        self.session_info = session_info

        # TASK + BEHAVIOR STATUS
        self.right_active = True
        self.trial_running = False
        self.trial_number = 0  # I don't think stopping at max trials is implemented - do that

        self.last_choice_time = -np.inf
        self.rewards_earned_in_block = 0
        self.rewards_available_in_block = rng.integers(1, 4)

        # Lick detection
        self.lick_side_buffer = np.zeros(2)

        ### TRAINING REWARDS PARAMETERS ###
        self.automate_training_rewards = False  # keep here, use in controller
        self.give_training_reward = False  # keep here, use in controller
        self.error_count = 0
        self.errors_to_reward = 5

        # These can't be refactored, session parameters needed for behavbox
        # maybe move them into a parameters class
        self.ITI = session_info['entry_interval']
        self.lick_threshold = session_info['lick_threshold']
        self.machine = self.make_state_machine()
        self.last_state_fxn = self.switch_to_standby
        self.block_type_counter = np.zeros(2)

        self.trial_choice_list: list = []
        self.trial_correct_list: list = []
        self.trial_choice_times: list = []
        self.trial_reward_given: list = []
        self.event_list = deque()
        self.t_session_start = time.time()

        self.presenter_commands = []
        self.ITI_active = False

        self.end_dark_time = 0
        self.next_dark_time = 0
        self.dark_period_times = [10]

        # trial statistics - TODO - edit these away
        # self.trial_running = False
        # self.innocent = True
        # self.trial_number = 0
        # self.error_count = 0
        # self.error_list = []
        # self.error_repeat = False
        # self.lick_time = 0.0
        # self.lick_interval = self.session_info["lick_interval"]
        # # self.reward_time_start = None # for reward_available state time keeping purpose
        # self.reward_time = 10
        # self.reward_times_up = False
        # self.reward_pump1 = self.session_info["reward_pump1"]
        # self.reward_pump2 = self.session_info['reward_pump2']
        # self.reward_size1 = self.session_info['reward_size1']
        # self.reward_size2 = self.session_info['reward_size2']
        # self.reward_size3 = self.session_info['reward_size3']
        # self.reward_size4 = self.session_info['reward_size4']
        # self.ITI = self.session_info['ITI']
        # self.p_switch = self.session_info['p_switch']
        # self.p_reward = self.session_info['p_reward']
        # self.reward_earned = False
        #
        # self.ContextA_time = 0
        # self.ContextB_time = 0
        # self.LED_on_time_plus_LED_duration = 0
        #
        # self.active_press = 0
        # self.inactive_press = 0
        # self.timeline_active_press = []
        # self.active_press_count_list = []
        # self.timeline_inactive_press = []
        # self.inactive_press_count_list = []
        #
        # self.left_poke_count = 0
        # self.right_poke_count = 0
        # self.timeline_left_poke = []
        # self.left_poke_count_list = []
        # self.timeline_right_poke = []
        # self.right_poke_count_list = []
        # self.event_name = ""

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
            # ['start_in_right_patch', 'standby', 'right_patch'],
            # ['start_in_left_patch', 'standby', 'left_patch'],
            ['switch_to_right_patch', ['standby', 'dark_period', 'left_patch'], 'right_patch'],
            ['switch_to_left_patch', ['standby', 'dark_period', 'right_patch'], 'left_patch'],
            ['switch_to_dark_period', ['left_patch', 'right_patch'], 'dark_period'],
            ['switch_to_standby', '*', 'standby']]

        machine = TimedStateMachine(
            model=self,
            states=states,
            transitions=transitions,
            initial='standby'
        )
        return machine

    def check_intertrial_interval(self, time_since_choice) -> bool:
        if time_since_choice < self.ITI:
            self.lick_side_buffer *= 0
            return False

        elif time_since_choice >= self.ITI and self.ITI_active:
            # turn on the LED, end the run loop
            self.turn_LED_on()
            self.lick_side_buffer *= 0
            self.ITI_active = False
            return False

        else:
            return True

    def check_dark_period(self, cur_time: float) -> bool:
        if self.state != 'dark_period' and cur_time >= self.next_dark_time:
            self.turn_LED_off()
            self.reset_counters()
            self.switch_to_dark_period()
            return False

        elif self.state != 'dark_period' and cur_time < self.next_dark_time:
            return True

        elif self.state == 'dark_period' and cur_time < self.end_dark_time:
            return False

        elif self.state == 'dark_period' and cur_time >= self.end_dark_time:
            self.turn_LED_on()
            self.reset_counters()
            if rng.random() > 0.5:
                self.switch_to_left_patch()
            else:
                self.switch_to_right_patch()
            return False

    def run_event_loop(self):
        cur_time = time.time()
        time_since_start = cur_time - self.t_session_start
        time_since_choice = cur_time - self.last_choice_time

        if self.event_list:
            event = self.event_list.popleft()
        else:
            event = ''

        if self.state == 'standby':
            return time_since_start

        continue_run = self.check_dark_period(cur_time)
        if not continue_run:
            return time_since_start

        continue_run = self.check_intertrial_interval(time_since_choice)
        if not continue_run:
            return time_since_start

        if event == 'right_entry':
            self.lick_side_buffer[RIGHT_IX] += 1
        elif event == 'left_entry':
            self.lick_side_buffer[LEFT_IX] += 1

        choice = self.determine_choice()
        if choice == 'right':
            self.last_choice_time = cur_time
            self.turn_LED_off()
            if self.state == 'right_patch':
                self.log_correct_choice(RIGHT_IX, time_since_start)
                self.give_correct_reward()
            else:
                self.log_incorrect_choice(RIGHT_IX, time_since_start)
                self.give_incorrect_reward()
                logging.info(";" + str(time.time()) + ";[transition];wrong_choice_right_patch;" + str())

        elif choice == 'left':
            self.last_choice_time = cur_time
            self.turn_LED_off()
            if self.state == 'left_patch':
                self.log_correct_choice(LEFT_IX, time_since_start)
                self.give_correct_reward()
            else:
                self.log_incorrect_choice(LEFT_IX, time_since_start)
                self.give_incorrect_reward()
                logging.info(";" + str(time.time()) + ";[transition];wrong_choice_right_patch;" + str(""))

        elif choice == 'switch':
            self.last_choice_time = cur_time  # for switches, enter ITI but do not update choices; decide whether to include this or not
            self.turn_LED_off()

        elif (self.error_count >= self.errors_to_reward and self.automate_training_rewards)\
                or self.give_training_reward:
            self.last_choice_time = cur_time
            self.turn_LED_off()
            self.presenter_commands.append('give_training_reward')

            give_training_reward = True
            if self.state == 'right_patch':
                choice_side = RIGHT_IX
            else:
                choice_side = LEFT_IX
            self.log_training_reward(choice_side, time_since_start)

        self.give_training_reward = False
        return time_since_start

    def turn_LED_on(self) -> None:
        self.presenter_commands.append('turn_LED_on')

    def turn_LED_off(self) -> None:
        self.presenter_commands.append('turn_LED_off')

    def give_correct_reward(self) -> None:
        self.presenter_commands.append('give_correct_reward')

    def give_incorrect_reward(self) -> None:
        self.presenter_commands.append('give_incorrect_reward')

    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(""))
        self.next_dark_time = time.time() + 120
        self.reset_counters()

    def enter_right_patch(self):
        self.trial_running = True
        self.last_state_fxn = self.switch_to_right_patch
        logging.info(";" + str(time.time()) + ";[transition];enter_right_patch;" + str(""))

    def exit_right_patch(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_right_patch;" + str(""))

    def enter_left_patch(self):
        self.trial_running = True
        self.last_state_fxn = self.switch_to_left_patch
        logging.info(";" + str(time.time()) + ";[transition];enter_left_patch;" + str(""))

    def exit_left_patch(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_left_patch;" + str(""))

    def enter_dark_period(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_dark_period;" + str(""))
        self.rewards_earned_in_block = 0
        self.trial_running = False
        self.end_dark_time = time.time() + rng.choice(self.dark_period_times)

    def exit_dark_period(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_dark_period;" + str())
        self.next_dark_time = time.time() + 120

    def start_task(self):
        ic('starting task')
        self.next_dark_time = time.time() + 120
        if rng.random() > 0.5:
            self.switch_to_left_patch()
        else:
            self.switch_to_right_patch()
