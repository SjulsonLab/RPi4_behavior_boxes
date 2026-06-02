#!/usr/bin/env python
# coding: utf-8

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

# SEED = 0
# random.seed(SEED)


class AlternatingLatentModel(Model):

    def __init__(self, session_info: dict):  # name and session_info should be provided as kwargs
        # TASK + BEHAVIOR STATUS
        self.session_info = session_info
        self.trial_running = False
        self.trial_number = 0  # I don't think stopping at max trials is implemented - do that

        self.last_choice_time = -np.inf
        self.rewards_earned_in_block = 0
        self.rewards_available_in_block = random.randint(1, 4)

        # Lick detection
        self.lick_side_buffer = np.zeros(2)
        self.lick_entry_buffer = np.zeros(2)
        self.lick_exit_buffer = np.array([np.inf, np.inf])

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

        self.t_session_start = time.time()

        self.trial_choice_list = []
        self.trial_correct_list = []
        self.trial_choice_times = []
        self.trial_reward_given = []
        self.event_list = deque()
        self.presenter_commands = deque()
        self.ITI_active = False
        self.ITI_thread = None
        self.t_ITI_start = 0
        self.t_choice_window_open = -np.inf

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
        logging.info(";" + str(time.time()) + ";[transition];trial_start;" + str(""))

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
        self.lick_entry_buffer *= 0
        self.lick_exit_buffer *= np.inf
        self.close_choice_window()
        self.ITI_active = True
        t = threading.Timer(interval=self.ITI, function=self.end_ITI)
        self.t_ITI_start = time.perf_counter()
        t.start()
        self.ITI_thread = t
        logging.info(";" + str(time.time()) + ";[transition];trial_stop;" + str(""))

    def end_ITI(self):
        # ic(time.perf_counter() - self.t_ITI_start)
        self.lick_side_buffer *= 0
        self.ITI_active = False
        self.open_choice_window()
        logging.info(";" + str(time.time()) + ";[transition];trial_start;" + str(""))

    def restart_ITI(self) -> None:
        """Restart the current intertrial interval after a quiet-ITI lick.

        Data contract:
        - Inputs: none.
        - Output:
          - Returns `None`; cancels the active timer when present and starts a new ITI timer.
        """
        if self.ITI_thread is not None:
            self.ITI_thread.cancel()
        self.activate_ITI()

    def open_choice_window(self) -> None:
        """Mark the current time as the earliest event time eligible for choices.

        Data contract:
        - Inputs: none.
        - Output:
          - Returns `None`; stores `time.time()` seconds in `t_choice_window_open`.
        """
        self.t_choice_window_open = time.time()

    def close_choice_window(self) -> None:
        """Prevent queued licks from being accepted until the next trial starts.

        Data contract:
        - Inputs: none.
        - Output:
          - Returns `None`; stores `np.inf` in `t_choice_window_open`.
        """
        self.t_choice_window_open = np.inf

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

        if self.state in ['right_patch', 'left_patch']:
            self.open_choice_window()

    def drain_pending_input_events(self) -> bool:
        """Process all queued lick events eligible for the current choice window.

        Data contract:
        - Inputs: none; queued event timestamps use seconds from `time.time()`.
        - Output:
          - `bool`, true when one or more lick events occurred during ITI and should
            restart the ITI if `quiet_ITI` is enabled.
        """
        iti_lick_detected = False
        while self.event_list:
            event = self.normalize_event(self.event_list.popleft())
            if not self.is_lick_event(event.name):
                continue

            discard_reason = self.lick_discard_reason(event)
            if discard_reason is not None:
                self.discard_lick_event(event, discard_reason)
                if discard_reason == "ITI":
                    iti_lick_detected = True
                continue

            if self.session_info['debounce_licks']:
                self.debounce_lick(event.name, event.timestamp)
            else:
                self.detect_lick_no_debounce(event.name)

        return iti_lick_detected

    def run_event_loop(self) -> None:
        cur_time = time.time()
        time_since_start = cur_time - self.t_session_start

        iti_lick_detected = self.drain_pending_input_events()

        if self.state == 'standby' or self.ITI_active:
            self.lick_side_buffer *= 0
            self.lick_entry_buffer *= 0
            self.lick_exit_buffer *= np.inf
            if self.ITI_active and self.session_info['quiet_ITI'] and iti_lick_detected:
                self.restart_ITI()
            # self.give_training_reward = False  # only toggle this in left/right active???
            return

        choice_side = self.determine_choice()
        if (self.error_count >= self.errors_to_reward and self.automate_training_rewards)\
                or self.give_training_reward:
            self.activate_ITI()
            self.presenter_commands.append('give_training_reward')
            self.trial_reward_given.append(True)
            if self.state == 'right_patch':
                self.log_training_reward(self.session_info['right_ix'], time_since_start)
            elif self.state == 'left_patch':
                self.log_training_reward(self.session_info['left_ix'], time_since_start)
            else:
                raise RuntimeError('state not recognized')

        elif choice_side == 'right':
            self.activate_ITI()
            if self.state == 'right_patch':
                reward_given = self.give_correct_reward()
                self.log_correct_choice(self.session_info['right_ix'], time_since_start, reward_given)
            elif self.state == 'left_patch':
                reward_given = self.give_incorrect_reward()
                self.log_incorrect_choice(self.session_info['right_ix'], time_since_start, reward_given)
                # logging.info(";" + str(time.time()) + ";[transition];wrong_choice_right_patch;" + str())

        elif choice_side == 'left':
            self.activate_ITI()
            if self.state == 'left_patch':
                reward_given = self.give_correct_reward()
                self.log_correct_choice(self.session_info['left_ix'], time_since_start, reward_given)
            elif self.state == 'right_patch':
                reward_given = self.give_incorrect_reward()
                self.log_incorrect_choice(self.session_info['left_ix'], time_since_start, reward_given)
                # logging.info(";" + str(time.time()) + ";[transition];wrong_choice_right_patch;" + str(""))

        elif choice_side == 'switch':
            self.activate_ITI()

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
