#!/usr/bin/env python
# coding: utf-8

# python3: lick_task_left_and_right_alternate.py
"""
author: Mitch Farrell; edited Matthew Chin
date: 2023-06-30 (to be updated)
name: lick_task_left_and_right_alternate.py
"""
from numpy import ndarray
from transitions import State, Machine
from transitions.extensions.states import add_state_features, Timeout

from icecream import ic
import logging
import time

import random
import numpy as np

import logging.config
from collections import deque
from typing import Protocol, List, Tuple, Union
from collections import defaultdict

"""
Model for the task - i.e. only sees the the task state machine and status, necessary parameters, and presenter messages.
"""

RIGHT_IX = 0
LEFT_IX = 1

@add_state_features(Timeout)
class TimedStateMachine(Machine):
    pass

class AlternateLatent(object):

    def __init__(self, session_info: dict):  # name and session_info should be provided as kwargs
        # TASK + BEHAVIOR STATUS
        self.right_active = True
        self.trial_running = False
        self.trial_number = 0  # I don't think stopping at max trials is implemented - do that

        self.last_choice_time = 0.0
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
        self.choice_interval = session_info['entry_interval']
        self.lick_threshold = session_info['lick_threshold']
        self.machine = self.make_state_machine(session_info['timeout_time'])
        self.last_state_fxn = self.switch_to_standby
        self.block_type_counter = np.zeros(2)

        # revise these later to make sure you need them
        self.trial_choice_list: list = []
        self.trial_correct_list: list = []
        self.trial_choice_times: list = []
        self.trial_reward_given: list = []
        self.event_list = deque()
        self.t_session = time.time()

    def make_state_machine(self, timeout_time: float):
        states = [
            State(name='standby',
                  on_enter=['switch_to_reward_available'],
                  on_exit=["exit_standby"]),
            State(name="reward_available",
                  on_enter=["enter_reward_available"],
                  on_exit=["exit_reward_available"]),
            State(name="right_active",
                  on_enter=["enter_right_active"],
                  on_exit=['exit_right_active']),
            State(name="left_active",
                  on_enter=["enter_left_active"],
                  on_exit=['exit_left_active']),
            Timeout(name='timeout',
                    on_enter=['enter_timeout'],
                    timeout=timeout_time,
                    on_timeout=['exit_timeout'])]

        # all of these transition functions are created automatically
        transitions = [
            # ['start_trial_logic', 'standby', 'reward_available'],  # format: ['trigger', 'origin', 'destination']

            ['switch_to_standby', ['reward_available', 'right_active', 'left_active'], 'standby'],
            ['switch_to_reward_available', ['standby', 'timeout'], 'reward_available'],
            ['switch_to_left_active', '*', 'left_active'],
            ['switch_to_right_active', '*', 'right_active'],


            ['switch_to_timeout', ['reward_available', 'right_active', 'left_active'], 'timeout'],
            ['end_task', ['reward_available', 'timeout', 'right_active', 'left_active'], 'standby']]

        machine = TimedStateMachine(
            model=self,
            states=states,
            transitions=transitions,
            initial='standby'
        )
        return machine

    def start_trial_logic(self):
        p = np.random.random_sample()
        if p < 0.5:
            # right sample
            if self.state != 'right_active':
                self.block_type_counter *= 0
            else:
                self.block_type_counter[0] += 1


            self.switch_to_right_active()
        else:
            self.switch_to_left_active()

    def enter_standby(self):  # This function should also call for updating the plot???
        logging.info(";" + str(time.time()) + ";[transition];enter_standby;" + str(""))
        self.trial_running = False
        self.event_list.clear()
        # self.last_state_fxn = self.switch_to_standby

    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(""))
        # self.last_state = self.state
        self.reset_counters()

    def exit_right_active(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_right_active;" + str(""))
        # self.last_state_fxn = self.switch_to_right_active
        # self.reset_counters()

    def exit_left_active(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_left_active;" + str(""))
        # self.last_state_fxn = self.switch_to_left_active
        # self.reset_counters()

    def enter_right_active(self):
        self.right_active = True
        self.trial_running = True
        self.last_state_fxn = self.switch_to_right_active
        logging.info(";" + str(time.time()) + ";[transition];enter_right_active;" + str(""))

    def enter_left_active(self):
        self.right_active = False
        self.trial_running = True
        self.last_state_fxn = self.switch_to_left_active
        logging.info(";" + str(time.time()) + ";[transition];enter_left_active;" + str(""))

    def enter_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_reward_available;" + str(""))
        self.last_state_fxn = self.switch_to_reward_available
        self.trial_running = True

    def exit_reward_available(self):
        self.last_state = self.state
        logging.info(";" + str(time.time()) + ";[transition];exit_reward_available;" + str(""))
        self.reset_counters()

    def enter_timeout(self):
        # log the entrance to timeout; reset counters
        self.event_list.clear()
        self.lick_side_buffer *= 0
        self.trial_running = False
        logging.info(";" + str(time.time()) + ";[transition];enter_timeout;" + str(""))

    def exit_timeout(self):
        # logs the exit-timeout; doesn't do anything else
        self.event_list.clear()
        self.lick_side_buffer *= 0
        logging.info(";" + str(time.time()) + ";[transition];exit_timeout;" + str(""))
        if self.rewards_earned_in_block >= self.rewards_available_in_block:
            self.sample_next_block()
        else:
            self.last_state_fxn()

    def sample_next_block(self):
        self.reset_counters()
        self.rewards_available_in_block = random.randint(1, 4)
        print('sampling_next_block')
        if random.randint(0, 1) == 0:
            if self.state != 'right_active':
                self.block_type_counter *= 0
            else:
                self.block_type_counter[0] += 1

            if self.block_type_counter[0] >= 2:
                self.switch_to_left_active()
            else:
                self.switch_to_right_active()

        else:
            if self.state != 'left_active':
                self.block_type_counter *= 0
            else:
                self.block_type_counter[1] += 1

            if self.block_type_counter[1] >= 2:
                self.switch_to_right_active()
            else:
                self.switch_to_left_active()

    def reset_counters(self):
        self.lick_side_buffer *= 0
        self.rewards_earned_in_block = 0
        self.error_count = 0
        self.event_list.clear()

    def determine_choice(self) -> Union[int, ndarray[int]]:
        """Determine whether there has been a choice to the left ports, right ports, or a switch."""

        sides_licked = np.sum(self.lick_side_buffer.astype(bool))  # get nonzero sides
        if sides_licked > 1:
            # made a switch, reset the counter
            self.lick_side_buffer *= 0
            return -1

        if np.amax(self.lick_side_buffer) >= self.lick_threshold:
            choice_ix = np.argmax(self.lick_side_buffer)  # either 0 or 1
            # choice = ['right', 'left'][choice_ix]
            self.lick_side_buffer *= 0
            return choice_ix
        else:
            return -1  # no choice made/not enough licks

    def run_event_loop(self) -> Tuple[str, bool, float]:
        choice_correct = ''  # ['correct', 'incorrect', 'switch', '']
        give_training_reward = False
        cur_time = time.time()
        time_since_start = cur_time - self.t_session
        dt = cur_time - self.last_choice_time

        if self.event_list:
            event = self.event_list.popleft()
        else:
            event = ''

        if self.state in ['reward_available', 'left_active', 'right_active']:
            if dt < self.choice_interval:
                self.lick_side_buffer *= 0
                return choice_correct, give_training_reward, time_since_start  # check keyboard in controller, not here

            if event == "right_entry":
                self.lick_side_buffer[RIGHT_IX] += 1
            elif event == 'left_entry':
                self.lick_side_buffer[LEFT_IX] += 1

            choice_side = self.determine_choice()
            # if no choice made, don't mark anything but maybe give reward
            if choice_side == 0:  #'right':
                self.last_choice_time = cur_time
                if self.right_active:
                    choice_correct = 'correct'
                    self.correct_choice_updates(choice_side, time_since_start)
                else:
                    choice_correct = 'incorrect'
                    self.incorrect_choice_updates(choice_side, time_since_start)

            elif choice_side == 1:  #'left':
                self.last_choice_time = cur_time
                if not self.right_active:
                    choice_correct = 'correct'
                    self.correct_choice_updates(choice_side, time_since_start)
                else:
                    choice_correct = 'incorrect'
                    self.incorrect_choice_updates(choice_side, time_since_start)

            # elif choice_side == ['switch', 'none']:  # no updates unless giving reward
                # self.incorrect_choice_updates(choice_side, cur_time)
                    # give_reward = self.incorrect_choice_updates(choice_side, cur_time)

            elif (self.error_count >= self.errors_to_reward and self.automate_training_rewards)\
                    or self.give_training_reward:
                self.last_choice_time = cur_time
                give_training_reward = True
                if self.right_active:
                    choice_side = 0
                else:
                    choice_side = 1
                self.training_reward_updates(choice_side, time_since_start)

            self.give_training_reward = False
            return choice_correct, give_training_reward, time_since_start

        else:
            self.give_training_reward = False
            return choice_correct, give_training_reward, time_since_start

    def correct_choice_updates(self, choice: int, event_time: float) -> None:
        self.trial_choice_list.append(choice)
        self.trial_choice_times.append(event_time)
        self.trial_correct_list.append(True)
        self.error_count = 0

    def incorrect_choice_updates(self, choice: int, event_time: float) -> None:
        self.trial_choice_list.append(choice)
        self.trial_choice_times.append(event_time)
        self.trial_correct_list.append(False)
        self.error_count += 1

    def training_reward_updates(self, choice: int, event_time: float) -> None:
        self.trial_choice_list.append(choice)
        self.trial_choice_times.append(event_time)
        self.trial_correct_list.append(False)
        self.error_count = 0


def main():
    session_info = defaultdict(list)
    session_info['timeout_time'] = 1
    task = AlternateLatent(session_info)
    # task.switch_to_left_active()
    # task.exit_standby()
    # task.switch_to_reward_available()
    task.sample_next_block()
    print(task.state)


if __name__ == '__main__':
    main()
