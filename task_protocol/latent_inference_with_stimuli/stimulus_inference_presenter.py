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
        self.stimulus_thread = None

        if session_info['counterbalance_type'] == 'leftA':
            self.L_stimulus_on = self.stimulus_A_on
            self.R_stimulus_on = self.stimulus_B_on
        elif session_info['counterbalance_type'] == 'rightA':
            self.L_stimulus_on = self.stimulus_B_on
            self.R_stimulus_on = self.stimulus_A_on

    def stimulus_A_on(self) -> None:
        self.box.sound1.blink(0.1, 0.1)
        grating_name = 'vertical_grating_{}s.dat'.format(self.session_info['grating_duration'])
        # self.box.visualstim.loop_grating(self.session_info['gratings'][grating_name])
        self.box.visualstim.loop_grating(grating_name, self.session_info['stimulus_duration'])

    def stimulus_B_on(self) -> None:
        self.box.sound1.blink(0.2, 0.1)
        grating_name = 'horizontal_grating_{}s.dat'.format(self.session_info['grating_duration'])
        # self.box.visualstim.loop_grating(self.session_info['gratings'][grating_name])
        self.box.visualstim.loop_grating(grating_name, self.session_info['stimulus_duration'])

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


    def match_command(self, command: str, correct_pump: int, incorrect_pump: int) -> None:
        # give reward if
        # 1. training reward/human reward (give reward, regardless of action)
        # 2. correct choice and meets correct reward probability
        # 3. incorrect but REAL choice (i.e. not a switch) and meets incorrect reward probability
        # state changes if choice is correct and switch probability is met
        if command == 'turn_LED_on':
            self.box.cueLED1.on()
            self.box.cueLED2.on()
            logging.info(";" + str(time.time()) + ";[action];LED_on;" + str(""))

        elif command == 'turn_LED_off':
            self.box.cueLED1.off()
            self.box.cueLED2.off()
            logging.info(";" + str(time.time()) + ";[action];LED_off;" + str(""))

        elif command == 'turn_L_stimulus_on':
            self.L_stimulus_on()
            logging.info(";" + str(time.time()) + ";[action];left_stimulus_on;" + str(""))

        elif command == 'turn_L_stimulus_off':
            self.stimuli_reset()  # self.stimuli_off()
            logging.info(";" + str(time.time()) + ";[action];left_stimulus_off;" + str(""))

        elif command == 'turn_R_stimulus_on':
            self.R_stimulus_on()
            logging.info(";" + str(time.time()) + ";[action];right_stimulus_on;" + str(""))

        elif command == 'turn_R_stimulus_off':
            self.stimuli_reset()  # self.stimuli_off()
            logging.info(";" + str(time.time()) + ";[action];right_stimulus_off;" + str(""))

        elif command == 'turn_stimulus_C_on':
            self.stimulus_C_on()
            logging.info(";" + str(time.time()) + ";[action];stimulus_C_on;" + str(""))

        elif command == 'reset_stimuli':
            self.stimuli_reset()
            logging.info(";" + str(time.time()) + ";[action];stimuli_reset;" + str(""))

        elif command == 'turn_stimuli_off':
            self.stimuli_off()
            logging.info(";" + str(time.time()) + ";[action];stimuli_off;" + str(""))

        elif command == 'give_training_reward':
            reward_size = self.reward_size_large
            self.task.rewards_earned_in_block += 1
            self.task.trial_reward_given.append(True)
            logging.info(";" + str(time.time()) + ";[reward];giving_reward;" + str(""))
            self.deliver_reward(pump_key=self.pump_keys[correct_pump], reward_size=reward_size)

        elif command == 'give_correct_reward':
            if random.random() < self.session_info['correct_reward_probability']:
                reward_size = self.reward_size_large
                self.task.rewards_earned_in_block += 1
                self.task.trial_reward_given.append(True)
            else:
                reward_size = 0
                self.task.trial_reward_given.append(False)

            self.deliver_reward(pump_key=self.pump_keys[correct_pump], reward_size=reward_size)

        elif command == 'give_incorrect_reward':
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

        if command in ['give_training_reward', 'give_correct_reward'] and random.random() < self.session_info[
            'switch_probability']:
            if self.task.state == 'right_patch':
                self.task.switch_to_left_patch()
            elif self.task.state == 'left_patch':
                self.task.switch_to_right_patch()
            else:
                pass
                # raise RuntimeError('state not recognized')

            print('current state: {}; rewards earned in block: {}'.format(self.task.state,
                                                                          self.task.rewards_earned_in_block))

    def perform_task_commands(self, correct_pump: int, incorrect_pump: int) -> None:
        for i in range(len(self.task.presenter_commands)):
            c = self.task.presenter_commands.pop(0)
            self.match_command(c, correct_pump, incorrect_pump)

        for i in range(len(self.box.visualstim.presenter_commands)):
            c = self.box.visualstim.presenter_commands.pop(0)
            self.match_command(c, correct_pump, incorrect_pump)

    def update_plot(self, save_fig=False) -> None:
        if self.task.trial_choice_list:
            ix = np.array(self.task.trial_correct_list)
            choices = np.array(self.task.trial_choice_list)
            times = np.array(self.task.trial_choice_times)
            rewards = np.array(self.task.trial_reward_given)

            correct_trials = choices[ix]
            correct_times = times[ix]

            incorrect_trials = choices[~ix]
            incorrect_times = times[~ix]

            reward_trials = choices[rewards]
            reward_times = times[rewards]

            self.gui.figure_window.correct_line.set_data(correct_times, correct_trials)
            self.gui.figure_window.error_line.set_data(incorrect_times, incorrect_trials)
            self.gui.figure_window.reward_line.set_data(reward_times, reward_trials)

            # update this to show the last 20-ish trials
            if times.size > 1:
                T = [times[-20:][0], times[-1]]
            else:
                T = [times[-1] - .5, times[-1] + .5]
            plt.xlim(T)

        self.gui.figure_window.state_text.set_text('State: {}; ITI: {}'.format(self.task.state,
                                                                         self.task.ITI_active))
        self.gui.figure_window.stimulus_text.set_text('Stimulus on: {}'.format(self.box.visualstim.gratings_on))

        self.gui.check_plot(figure=self.gui.figure_window.figure, savefig=save_fig)
