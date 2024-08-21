#!/usr/bin/env python
# coding: utf-8

# python3: latent_inference_forage_task_three_states.py
"""
author: Mitch Farrell; edited Matthew Chin
last updated: 2024-01-24
name: latent_inference_forage_task_three_states.py
"""
from transitions import State, Machine
from essential.base_classes import TimedStateMachine, Model
# from task_protocol.base_classes import TimedStateMachine, Model

from icecream import ic
import logging
import time

import numpy as np
import random

import logging.config
from collections import deque
from typing import List, Tuple, Union

import logging.config
import threading

# SEED = 0
# random.seed(SEED)
RIGHT_IX = 0
LEFT_IX = 1


class LatentInferenceModel(Model):  # subclass from base task

    def __init__(self, session_info: dict):
        self.session_info = session_info

        # TASK + BEHAVIOR STATUS
        # self.right_active = True
        # self.trial_running = False
        self.trial_number = 0  # I don't think stopping at max trials is implemented - do that
        self.rewards_earned_in_block = 0

        self.last_choice_time = -np.inf
        self.rewards_available_in_block = random.randint(1, 4)

        # Lick detection
        self.lick_side_buffer = np.zeros(2)

        ### TRAINING REWARDS PARAMETERS ###
        self.automate_training_rewards = False  # keep here, use in controller
        self.give_training_reward = False  # keep here, use in controller
        self.error_count = 0
        self.errors_to_reward = 5
        self.max_consecutive_correct_trials = 30

        # These can't be refactored, session parameters needed for behavbox
        # maybe move them into a parameters class
        self.ITI = session_info['intertrial_interval']
        self.lick_threshold = session_info['lick_threshold']
        self.machine = self.make_state_machine()
        # self.last_state_fxn = self.switch_to_standby
        self.block_type_counter = np.zeros(2)

        self.trial_choice_list: list = []
        self.trial_correct_list: list = []
        self.trial_choice_times: list = []
        self.trial_reward_given: list = []
        self.event_list = deque()
        self.t_session_start = time.time()

        self.presenter_commands = []
        self.ITI_active = False
        self.ITI_thread = None

        self.end_dark_time = 0
        self.next_dark_time = 0
        self.dark_period_thread = None
        self.dark_period_length = 0

        # debugging
        self.t_ITI_start = 0

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

    def determine_experimental_rewards(self, choice_side: str, training_reward_flag: bool, time_since_start: float) -> bool:
        reward_earned = False
        if training_reward_flag:
            self.presenter_commands.append('give_training_reward')
            self.trial_reward_given.append(True)
            if self.state == 'right_patch':
                self.log_training_reward(RIGHT_IX, time_since_start)
            elif self.state == 'left_patch':
                self.log_training_reward(LEFT_IX, time_since_start)

        elif choice_side == 'right':
            if self.state == 'right_patch':
                self.log_correct_choice(RIGHT_IX, time_since_start, choice_side)
                self.give_correct_reward()
                reward_earned = True
            elif self.state == 'left_patch':
                self.log_incorrect_choice(RIGHT_IX, time_since_start, choice_side)
                self.give_incorrect_reward()

        elif choice_side == 'left':
            if self.state == 'left_patch':
                self.log_correct_choice(LEFT_IX, time_since_start, choice_side)
                self.give_correct_reward()
                reward_earned = True
            elif self.state == 'right_patch':
                self.log_incorrect_choice(LEFT_IX, time_since_start, choice_side)
                self.give_incorrect_reward()

        return reward_earned

    def determine_control_rewards(self, choice_side: str, training_reward_flag: bool, time_since_start: float) -> bool:
        reward_earned = False
        if training_reward_flag:
            self.presenter_commands.append('give_training_reward')
            self.trial_reward_given.append(True)
            self.log_training_reward(RIGHT_IX, time_since_start)

        elif choice_side == 'right':
            self.log_correct_choice(RIGHT_IX, time_since_start, choice_side)
            reward_earned = True
            self.give_correct_reward()

        elif choice_side == 'left':
            self.log_incorrect_choice(LEFT_IX, time_since_start, choice_side)
            self.give_incorrect_reward()

        return reward_earned

    def run_event_loop(self, control: bool = False):
        cur_time = time.time()
        time_since_start = cur_time - self.t_session_start

        if self.event_list:
            event = self.event_list.popleft()
        else:
            event = ''

        if event == 'right_entry':
            self.lick_side_buffer[RIGHT_IX] += 1
        elif event == 'left_entry':
            self.lick_side_buffer[LEFT_IX] += 1

        if self.state in ['standby', 'dark_period']:
            self.lick_side_buffer *= 0
            return time_since_start

        if self.state in ['left_patch', 'right_patch'] and cur_time >= self.next_dark_time:
            self.lick_side_buffer *= 0
            self.activate_dark_period()
            return time_since_start

        if self.ITI_active:
            self.lick_side_buffer *= 0
            if self.session_info['quiet_ITI'] and self.lick_side_buffer.sum() > 0:
                self.ITI_thread.cancel()
                self.activate_ITI()
            return time_since_start

        choice_side = self.determine_choice()
        choice_flag = choice_side in ['right', 'left', 'switch']
        training_reward_flag = ((self.error_count >= self.errors_to_reward and self.automate_training_rewards)
                                or self.give_training_reward)
        if choice_flag or training_reward_flag:
            self.activate_ITI()

        reward_earned = False
        if choice_side in ['right', 'left'] or training_reward_flag:  # no rewards for switch
            if control:
                reward_earned = self.determine_control_rewards(choice_side, training_reward_flag, time_since_start)
            else:
                reward_earned = self.determine_experimental_rewards(choice_side, training_reward_flag, time_since_start)

        if ((reward_earned and random.random() < self.session_info['switch_probability']) or
                self.rewards_earned_in_block >= self.max_consecutive_correct_trials):
            self.rewards_earned_in_block = 0
            if self.state == 'right_patch':
                self.switch_to_left_patch()
            elif self.state == 'left_patch':
                self.switch_to_right_patch()
            else:
                pass
                # raise RuntimeError('state not recognized')

        self.give_training_reward = False
        return time_since_start

    def turn_LED_on(self) -> None:
        self.presenter_commands.append('turn_LED_on')

    def turn_LED_off(self) -> None:
        self.presenter_commands.append('turn_LED_off')

    def give_correct_reward(self) -> None:
        if random.random() < self.session_info['correct_reward_probability']:
            self.rewards_earned_in_block += 1
            self.trial_reward_given.append(True)
        else:
            self.trial_reward_given.append(False)

        self.presenter_commands.append('give_correct_reward')

    def give_incorrect_reward(self) -> None:
        if random.random() < self.session_info['incorrect_reward_probability']:
            self.rewards_earned_in_block += 1
            self.trial_reward_given.append(True)
        else:
            self.trial_reward_given.append(False)

        self.presenter_commands.append('give_incorrect_reward')

    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(""))
        self.next_dark_time = time.time() + self.session_info['epoch_length']
        self.reset_counters()
        self.turn_LED_on()

    def enter_right_patch(self):
        self.trial_running = True
        # self.last_state_fxn = self.switch_to_right_patch
        logging.info(";" + str(time.time()) + ";[transition];enter_right_patch;" + str(""))

    def exit_right_patch(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_right_patch;" + str(""))

    def enter_left_patch(self):
        self.trial_running = True
        # self.last_state_fxn = self.switch_to_left_patch
        logging.info(";" + str(time.time()) + ";[transition];enter_left_patch;" + str(""))

    def exit_left_patch(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_left_patch;" + str(""))

    def enter_dark_period(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_dark_period;" + str(""))
        self.rewards_earned_in_block = 0
        self.trial_running = False

    def exit_dark_period(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_dark_period;" + str())
        self.next_dark_time = time.time() + self.session_info['epoch_length']

    def start_task(self):
        ic('starting task')
        self.next_dark_time = time.time() + self.session_info['epoch_length']
        self.sample_next_patch()
        self.turn_LED_on()

    def activate_ITI(self):
        self.lick_side_buffer *= 0
        self.ITI_active = True
        self.turn_LED_off()
        t = threading.Timer(interval=self.ITI, function=self.end_ITI)
        self.t_ITI_start = time.perf_counter()
        t.start()
        self.ITI_thread = t

    def end_ITI(self):
        # ic(time.perf_counter() - self.t_ITI_start)
        self.lick_side_buffer *= 0
        self.ITI_active = False
        if self.state == 'dark_period':
            self.turn_LED_off()
        else:
            self.turn_LED_on()

    def activate_dark_period(self):
        # make sure this overrides ITI, so you don't get an LED turned on after darkmode starts
        self.ITI_active = False
        if self.ITI_thread:
            self.ITI_thread.cancel()

        self.turn_LED_off()
        self.reset_counters()
        self.switch_to_dark_period()

        t = threading.Timer(random.choice(self.session_info['dark_period_times']), self.end_dark_period)
        t.start()
        self.dark_period_thread = t

    def end_dark_period(self):
        self.reset_counters()
        self.sample_next_patch()
        self.turn_LED_on()

    def sample_next_patch(self):
        self.rewards_earned_in_block = 0
        if random.random() > 0.5:
            self.switch_to_left_patch()
        else:
            self.switch_to_right_patch()
