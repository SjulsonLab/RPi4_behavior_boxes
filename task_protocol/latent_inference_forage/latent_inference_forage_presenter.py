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


SEED = 0
random.seed(SEED)


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

        ###############################################################################################
        # event list trigger by the interaction between the RPi and the animal for visualization
        # interact_list: lick, choice interaction between the board and the animal for visualization
        ###############################################################################################
        self.interact_list = []  # todo - remove references to this

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

        time_since_start = self.task.run_event_loop()
        self.perform_task_commands(correct_pump, incorrect_pump)
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

                if random.random() < self.session_info['switch_probability']:
                    if self.task.state == 'right_patch':
                        self.task.switch_to_left_patch()
                    elif self.task.state == 'left_patch':
                        self.task.switch_to_right_patch()
                    else:
                        pass
                        # raise RuntimeError('state not recognized')

                print('current state: {}; rewards earned in block: {}'.format(self.task.state,
                                                                              self.task.rewards_earned_in_block))
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

        self.task.presenter_commands.clear()

    def update_plot(self, save_fig: bool = False) -> None:
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
            # print('correct trials:', correct_trials)

            # update this to show the last 20-ish trials
            if times.size > 1:
                T = [times[-20:][0], times[-1]]
            else:
                T = [times[-1]-.5, times[-1]+.5]
            plt.xlim(T)

        self.gui.figure_window.text.set_text('State: {}; ITI: {}'.format(self.task.state,
                                                                                 self.task.ITI_active))

        self.gui.check_plot(figure=self.gui.figure_window.figure, savefig=save_fig)
