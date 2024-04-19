from task_protocol.latent_inference_forage.latent_inference_forage_presenter import LatentInferenceForagePresenter

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

class StimulusInferencePresenter(LatentInferenceForagePresenter):  # subclass from base task

    def __init__(self, model: Model, box: Box, pump: PumpBase, gui: GUI, session_info: dict):
        super().__init__(model, box, pump, gui, session_info)
        if session_info['counterbalance_type'] == 'leftA':
            self.L_stimulus_on = self.stimulus_A_on
            self.R_stimulus_on = self.stimulus_B_on
        elif session_info['counterbalance_type'] == 'rightA':
            self.L_stimulus_on = self.stimulus_B_on
            self.R_stimulus_on = self.stimulus_A_on

    def stimulus_A_on(self) -> None:
        self.box.sound1.blink(0.1, 0.1)
        grating_name = 'vertical_grating_{}s.dat'.format(self.session_info['stimulus_duration'])
        self.box.visualstim.loop_grating(self.session_info['gratings'][grating_name])

    def stimulus_B_on(self) -> None:
        self.box.sound1.blink(0.2, 0.1)
        grating_name = 'horizontal_grating_{}s.dat'.format(self.session_info['stimulus_duration'])
        self.box.visualstim.loop_grating(self.session_info['gratings'][grating_name])

    def stimulus_C_on(self) -> None:
        self.box.sound2.on()
        self.box.visualstim.display_default_greyscale()

    def stimuli_reset(self) -> None:
        self.box.sound1.off()
        self.box.sound2.off()
        self.box.visualstim.end_gratings_process()
        self.box.visualstim.display_default_greyscale()

    def stimuli_off(self) -> None:
        self.box.cueLED1.off()
        self.box.cueLED2.off()
        self.box.sound1.off()
        self.box.sound2.off()
        self.box.visualstim.end_gratings_process()
        self.box.visualstim.myscreen.display_greyscale(0)

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
                logging.info(";" + str(time.time()) + ";[action];LED_on;" + str(""))

            elif c == 'turn_LED_off':
                self.box.cueLED1.off()
                self.box.cueLED2.off()
                logging.info(";" + str(time.time()) + ";[action];LED_off;" + str(""))

            elif c == 'turn_L_stimulus_on':
                self.L_stimulus_on()
                logging.info(";" + str(time.time()) + ";[action];left_stimulus_on;" + str(""))

            elif c == 'turn_L_stimulus_off':
                self.stimuli_reset()  # self.stimuli_off()
                logging.info(";" + str(time.time()) + ";[action];left_stimulus_off;" + str(""))

            elif c == 'turn_R_stimulus_on':
                self.R_stimulus_on()
                logging.info(";" + str(time.time()) + ";[action];right_stimulus_on;" + str(""))

            elif c == 'turn_R_stimulus_off':
                self.stimuli_reset()  # self.stimuli_off()
                logging.info(";" + str(time.time()) + ";[action];right_stimulus_off;" + str(""))

            elif c == 'turn_stimulus_C_on':
                self.stimulus_C_on()
                logging.info(";" + str(time.time()) + ";[action];stimulus_C_on;" + str(""))

            elif c == 'reset_stimuli':
                self.stimuli_reset()
                logging.info(";" + str(time.time()) + ";[action];stimuli_reset;" + str(""))

            elif c == 'turn_stimuli_off':
                self.stimuli_off()
                logging.info(";" + str(time.time()) + ";[action];stimuli_off;" + str(""))

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
                raise ValueError('Presenter command not recognized')

            if c in ['give_training_reward', 'give_correct_reward'] and random.random() < self.session_info['switch_probability']:
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