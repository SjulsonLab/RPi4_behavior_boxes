import collections
from typing import Tuple, List

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import random

from icecream import ic
import time
import logging
from essential.base_classes import Presenter, Model, GUI, Box, PumpBase


# SEED = 0
# random.seed(SEED)

PUMP1_IX = 0
PUMP2_IX = 1
trial_choice_map = {'right': 0, 'left': 1}


class LatentInferenceForagePresenter(Presenter):

    def __init__(self, model: Model, box: Box, pump: PumpBase, gui: GUI, session_info: dict):
        self.task = model
        self.gui = gui
        self.box = box
        self.pump = pump
        self.session_info = session_info
        self.pump_keys = (session_info["reward_pump1"], session_info['reward_pump2'])
        self.reward_size_large = session_info['reward_size_large']
        self.reward_size_small = session_info['reward_size_small']
        self.keypress_training_reward = False
        self.automatic_training_rewards = False

    def run(self) -> None:
        """
        Process one event, checking GUI and events as needed.
        Currently set to give rewards probabilistically (same reward sizes, unequal reward probabilities)
        """
        if self.task.state == 'right_patch':
            correct_pump = PUMP1_IX
            incorrect_pump = PUMP2_IX
        elif self.task.state == 'left_patch':
            correct_pump = PUMP2_IX
            incorrect_pump = PUMP1_IX
        else:
            correct_pump = None
            incorrect_pump = None
            # raise RuntimeError('state not recognized')

        if self.task.state in ['right_patch', 'left_patch']:
            time_since_start = self.task.run_event_loop()  # determine choice, trigger ITI
        self.perform_task_commands(correct_pump, incorrect_pump)  # switch state, give rewards, toggle stimuli, etc.
        self.update_plot()

        self.check_keyboard()

    def run_control(self) -> None:
        if self.task.state in ['right_patch', 'left_patch']:
            correct_pump = PUMP1_IX
            incorrect_pump = PUMP2_IX
            time_since_start = self.task.run_control_loop()  # determine choice, trigger ITI
        else:
            correct_pump = None
            incorrect_pump = None

        self.perform_task_commands(correct_pump, incorrect_pump)  # switch state, give rewards, toggle stimuli, etc.
        self.update_plot()
        self.check_keyboard()

    def perform_task_commands(self, correct_pump: int, incorrect_pump: int) -> None:
        # give reward if
        # 1. training reward/human reward (give reward, regardless of action)
        # 2. correct choice and meets correct reward probability
        # 3. incorrect but REAL choice (i.e. not a switch) and meets incorrect reward probability
        # state changes if choice is correct and switch probability is met

        for c in self.task.presenter_commands:
            if c == 'turn_LED_on':
                self.box.cueLED1.on()
                self.box.cueLED2.on()

            elif c == 'turn_LED_off':
                self.box.cueLED1.off()
                self.box.cueLED2.off()

            elif c == 'give_training_reward':
                reward_size = self.reward_size_large
                self.task.rewards_earned_in_block += 1
                self.task.trial_reward_given.append(True)
                logging.info(";" + str(time.time()) + ";[reward];giving_reward;" + str(""))
                self.deliver_reward(pump_key=self.pump_keys[correct_pump], reward_size=reward_size)

            elif c == 'give_correct_reward':
                if random.random() < self.session_info['correct_reward_probability']:
                    reward_size = self.reward_size_large
                    self.task.rewards_earned_in_block += 1
                    self.task.trial_reward_given.append(True)
                else:
                    reward_size = 0
                    self.task.trial_reward_given.append(False)

                self.deliver_reward(pump_key=self.pump_keys[correct_pump], reward_size=reward_size)

            elif c == 'give_incorrect_reward':
                if random.random() < self.session_info['incorrect_reward_probability']:
                    reward_size = self.reward_size_small
                    self.task.rewards_earned_in_block += 1
                    self.task.trial_reward_given.append(True)
                else:
                    reward_size = 0
                    self.task.trial_reward_given.append(False)

                print('current state: {}; rewards earned in block: {}'.format(self.task.state,
                                                                              self.task.rewards_earned_in_block))
                self.deliver_reward(pump_key=self.pump_keys[incorrect_pump], reward_size=reward_size)

            else:
                pass

            if c in ['give_training_reward', 'give_correct_reward'] and random.random() < self.session_info['switch_probability']:
                # if self.session_info['control']:  # control should only ever use right port/patch
                #     self.task.switch_to_right_patch()
                # elif

                if self.task.state == 'right_patch':
                    self.task.switch_to_left_patch()
                elif self.task.state == 'left_patch':
                    self.task.switch_to_right_patch()
                else:
                    pass
                    # raise RuntimeError('state not recognized')

            print('current state: {}; rewards earned in block: {}'.format(self.task.state,
                                                                          self.task.rewards_earned_in_block))

        self.task.presenter_commands.clear()

