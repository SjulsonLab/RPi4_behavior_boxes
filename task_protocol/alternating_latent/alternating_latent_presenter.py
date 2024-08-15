from typing import List, Tuple

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


class AlternatingLatentPresenter(Presenter):

    def __init__(self, model: Model, box: Box, pump: PumpBase, gui: GUI, session_info: dict):

        self.task: Model = model
        self.gui: GUI = gui
        self.box = box
        self.pump = pump
        self.session_info = session_info
        self.pump_keys = (session_info["reward_pump1"], session_info['reward_pump2'])
        self.reward_size_large = session_info['reward_size_large']
        self.reward_size_small = session_info['reward_size_small']

        # self.keypress_training_reward = False
        # self.automatic_training_rewards = False

    def run(self) -> None:
        """
        Process one event, checking GUI and events as needed.
        """
        if self.task.state in ['A', 'C1', 'right_patch']:
            correct_pump = PUMP1_IX
            incorrect_pump = PUMP2_IX
        elif self.task.state in ['B', 'C2', 'left_patch']:
            correct_pump = PUMP2_IX
            incorrect_pump = PUMP1_IX
        else:
            correct_pump = None
            incorrect_pump = None

        # if self.task.state in ['right_patch', 'left_patch', 'A', 'B', 'C1', 'C2']:
        #     self.task.run_event_loop()  # determine choice, trigger ITI
        if self.task.state == 'standby' or self.task.ITI_active:
            self.task.lick_side_buffer *= 0
            self.task.event_list.clear()
        else:
            self.task.run_event_loop()

        self.perform_task_commands(correct_pump, incorrect_pump)
        self.update_plot()

        self.check_keyboard()
        if self.task.rewards_earned_in_block >= self.task.rewards_available_in_block:
            self.task.sample_next_block()

    def perform_task_commands(self, correct_pump: int, incorrect_pump: int) -> None:
        # give reward if
        # 1. training reward/human reward (give reward, regardless of action)
        # 2. correct choice and meets correct reward probability
        # 3. incorrect but REAL choice (i.e. not a switch) and meets incorrect reward probability
        # state changes if choice is correct and switch probability is met

        for c in self.task.presenter_commands:
            if c == 'give_training_reward':
                reward_size = self.reward_size_large
                # self.task.rewards_earned_in_block += 1  # trying this out - not incrementing collected rewards if they are given by experimenter
                self.task.trial_reward_given.append(True)
                logging.info(";" + str(time.time()) + ";[reward];giving_reward;" + str(""))
                self.deliver_reward(pump_key=self.pump_keys[correct_pump], reward_size=reward_size)

            elif c == 'give_correct_reward':
                reward_size = self.reward_size_large
                self.task.rewards_earned_in_block += 1
                self.task.trial_reward_given.append(True)

                # alternating_latent is being used as a pretraining module, so we don't want to use probabilistic rewards anymore
                # if random.random() < self.session_info['correct_reward_probability']:
                #     reward_size = self.reward_size_large
                #     self.task.rewards_earned_in_block += 1
                #     self.task.trial_reward_given.append(True)
                # else:
                #     reward_size = 0
                #     self.task.trial_reward_given.append(False)

                print('current state: {}; rewards earned in block: {}'.format(self.task.state,
                                                                              self.task.rewards_earned_in_block))
                self.deliver_reward(pump_key=self.pump_keys[correct_pump], reward_size=reward_size)

            elif c == 'give_incorrect_reward':
                self.task.trial_reward_given.append(False)

                # alternating_latent is being used as a pretraining module, so we don't want to use probabilistic rewards anymore
                # if random.random() < self.session_info['incorrect_reward_probability']:
                #     reward_size = self.reward_size_small  # can modify these to a single value, reward large and reward small
                #     self.task.rewards_earned_in_block += 1
                #     self.task.trial_reward_given.append(True)
                # else:
                #     reward_size = 0
                #     self.task.trial_reward_given.append(False)

                print('current state: {}; rewards earned in block: {}'.format(self.task.state,
                                                                              self.task.rewards_earned_in_block))
                self.deliver_reward(pump_key=self.pump_keys[incorrect_pump], reward_size=reward_size)

        self.task.presenter_commands.clear()
