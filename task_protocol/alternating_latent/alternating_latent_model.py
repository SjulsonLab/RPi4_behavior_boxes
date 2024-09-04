#!/usr/bin/env python
# coding: utf-8

# python3: lick_task_left_and_right_alternate.py
"""
author: Mitch Farrell; edited Matthew Chin
last updated: 2023-06-30
name: lick_task_left_and_right_alternate.py
"""
from transitions import State, Machine
from transitions.extensions.states import Timeout
from essential.base_classes import TimedStateMachine, Model

from icecream import ic
import logging
import time

import random
import numpy as np

import logging.config
from typing import List, Tuple, Union
from collections import defaultdict, deque
import threading

"""
Model for the task - i.e. only sees the the task state machine and status, necessary parameters, and presenter messages.
"""

RIGHT_IX = 0
LEFT_IX = 1

# SEED = 0
# random.seed(SEED)


class AlternatingLatentModel(Model):

    def __init__(self, session_info: dict):  # name and session_info should be provided as kwargs
        # TASK + BEHAVIOR STATUS
        self.trial_running = False
        self.trial_number = 0  # I don't think stopping at max trials is implemented - do that

        self.last_choice_time = -np.inf
        self.rewards_earned_in_block = 0
        self.rewards_available_in_block = random.randint(1, 4)

        # Lick detection
        self.lick_side_buffer = np.zeros(2)

        ### TRAINING REWARDS PARAMETERS ###
        self.automate_training_rewards = False  # keep here, use in controller
        self.give_training_reward = False  # keep here, use in controller
        self.error_count = 0
        self.errors_to_reward = 5

        # These can't be refactored, session parameters needed for behavbox
        # maybe move them into a parameters class
        self.ITI = session_info['intertrial_interval']
        self.lick_threshold = session_info['lick_threshold']
        # self.machine = self.make_state_machine(session_info['timeout_time'])
        self.machine = self.make_state_machine(session_info['intertrial_interval'])
        self.block_type_counter = np.zeros(2)

        # revise these later to make sure you need them
        self.trial_choice_list: list = []
        self.trial_correct_list: list = []
        self.trial_choice_times: list = []
        self.trial_reward_given: list = []
        self.event_list = deque()
        self.t_session = time.time()

        self.presenter_commands = []
        self.ITI_active = False
        self.ITI_thread = None
        self.t_ITI_start = 0

    def make_state_machine(self, timeout_time: float):
        # reward_available is not used - it would allow licking either side but this task does not use that
        states = [
            State(name='standby',
                  on_enter=['switch_to_reward_available'],
                  on_exit=['exit_standby']),
            State(name='right_patch',
                  on_enter=['enter_right_patch'],
                  on_exit=['exit_right_patch']),
            State(name='left_patch',
                  on_enter=['enter_left_patch'],
                  on_exit=['exit_left_patch']),
            Timeout(name='timeout',
                    on_enter=['enter_timeout'],
                    timeout=timeout_time,
                    on_timeout=['exit_timeout'])]

        # all of these transition functions are created automatically
        transitions = [
            # ['start_trial_logic', 'standby', 'reward_available'],  # format: ['trigger', 'origin', 'destination']

            ['switch_to_standby', ['right_patch', 'left_patch'], 'standby'],
            ['switch_to_left_patch', '*', 'left_patch'],
            ['switch_to_right_patch', '*', 'right_patch'],
            ['end_task', ['timeout', 'right_patch', 'left_patch'], 'standby']
        ]

        machine = TimedStateMachine(
            model=self,
            states=states,
            transitions=transitions,
            initial='standby'
        )
        return machine

    def enter_standby(self):  # This function should also call for updating the plot???
        logging.info(";" + str(time.time()) + ";[transition];enter_standby;" + str(""))
        self.trial_running = False
        self.event_list.clear()

    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(""))
        # self.last_state = self.state
        self.reset_counters()

    def exit_right_patch(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_right_active;" + str(""))
        # self.reset_counters()

    def exit_left_patch(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_left_active;" + str(""))
        # self.reset_counters()

    def enter_right_patch(self):
        self.trial_running = True
        logging.info(";" + str(time.time()) + ";[transition];enter_right_patch;" + str(""))
        print('entering right active')

    def enter_left_patch(self):
        self.trial_running = True
        logging.info(";" + str(time.time()) + ";[transition];enter_left_patch;" + str(""))
        print('entering left active')

    def activate_ITI(self):
        self.lick_side_buffer *= 0
        self.ITI_active = True
        t = threading.Timer(interval=self.ITI, function=self.end_ITI)
        self.t_ITI_start = time.perf_counter()
        t.start()
        self.ITI_thread = t

    def end_ITI(self):
        # ic(time.perf_counter() - self.t_ITI_start)
        self.lick_side_buffer *= 0
        self.ITI_active = False

    def sample_next_block(self):
        self.reset_counters()
        self.rewards_available_in_block = random.randint(1, 4)
        print('sampling_next_block')
        if self.state == 'standby':
            self.block_type_counter *= 0
            p = random.random()
            if p > 0.5:
                self.switch_to_right_patch()
                self.block_type_counter[0] += 1
            else:
                self.switch_to_left_patch()
                self.block_type_counter[1] += 1

        elif self.state == 'right_patch':
            p = random.random()
            if p > 0.5 or self.block_type_counter[0] >= 2:
                self.block_type_counter *= 0
                self.switch_to_left_patch()
                self.block_type_counter[1] += 1
            else:
                self.block_type_counter[0] += 1

        elif self.state == 'left_patch':
            p = random.random()
            if p > 0.5 or self.block_type_counter[1] >= 2:
                self.block_type_counter *= 0
                self.switch_to_right_patch()
                self.block_type_counter[0] += 1
            else:
                self.block_type_counter[1] += 1

    def run_event_loop(self) -> None:
        cur_time = time.time()
        time_since_start = cur_time - self.t_session

        if self.event_list:
            event = self.event_list.popleft()
        else:
            event = ''

        if event == 'right_entry':
            self.lick_side_buffer[RIGHT_IX] += 1
        elif event == 'left_entry':
            self.lick_side_buffer[LEFT_IX] += 1

        if self.state == 'standby' or self.ITI_active:
            self.lick_side_buffer *= 0
            # self.give_training_reward = False  # only toggle this in left/right active???
            return

        choice_side = self.determine_choice()
        # if no choice made, don't mark anything but maybe give reward
        if choice_side == 'right':
            self.activate_ITI()
            if self.state == 'right_patch':
                reward_given = self.give_correct_reward()
                self.log_correct_choice(RIGHT_IX, time_since_start, reward_given)
            else:
                reward_given = self.give_incorrect_reward()
                self.log_incorrect_choice(RIGHT_IX, time_since_start, reward_given)
                # logging.info(";" + str(time.time()) + ";[transition];wrong_choice_right_patch;" + str())

        elif choice_side == 'left':
            self.activate_ITI()
            if self.state == 'left_patch':
                reward_given = self.give_correct_reward()
                self.log_correct_choice(LEFT_IX, time_since_start, reward_given)
            elif self.state == 'right_patch':
                reward_given = self.give_incorrect_reward()
                self.log_incorrect_choice(LEFT_IX, time_since_start, reward_given)
                # logging.info(";" + str(time.time()) + ";[transition];wrong_choice_right_patch;" + str(""))

        elif choice_side == 'switch':
            self.activate_ITI()

        elif (self.error_count >= self.errors_to_reward and self.automate_training_rewards)\
                or self.give_training_reward:
            self.activate_ITI()
            self.presenter_commands.append('give_training_reward')
            if self.state == 'right_patch':
                choice_ix = RIGHT_IX
            elif self.state == 'left_patch':
                choice_ix = LEFT_IX
            else:
                raise RuntimeError('state not recognized')
            self.log_training_reward(choice_ix, time_since_start)

        else:
            pass

        self.give_training_reward = False
        return

    def start_task(self):
        """A wrapper function for main function use."""
        ic('starting task')
        self.sample_next_block()

    def give_correct_reward(self) -> bool:
        self.presenter_commands.append('give_correct_reward')
        return True

    def give_incorrect_reward(self) -> bool:
        self.presenter_commands.append('give_incorrect_reward')
        return False


def main():
    session_info = defaultdict(list)
    session_info['timeout_time'] = 1
    task = AlternatingLatentModel(session_info)
    # task.switch_to_left_active()
    # task.exit_standby()
    # task.switch_to_reward_available()
    task.sample_next_block()
    print(task.state)


if __name__ == '__main__':
    main()
