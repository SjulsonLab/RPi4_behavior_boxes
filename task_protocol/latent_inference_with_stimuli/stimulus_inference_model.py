from task_protocol.latent_inference_forage.latent_inference_forage_model import LatentInferenceForageModel

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


class StimulusInferenceModel(LatentInferenceForageModel):
    """
    Subclass of the LatentInferenceForageModel class, which is a subclass of the Model class from the essential package.
    The only thing this needs to add on top of the LatentInferenceForageModel is the ability to (probabilistically)
    turn on and off stimuli.
    """

    def __init__(self, session_info: dict):
        super().__init__(session_info)
        # self.L_stimulus_active = False
        # self.R_stimulus_active = False

    def L_stimulus_on(self) -> None:
        # self.L_stimulus_active = True
        self.presenter_commands.append('turn_L_stimulus_on')

    def L_stimulus_off(self) -> None:
        # self.L_stimulus_active = False
        self.presenter_commands.append('turn_L_stimulus_off')

    def R_stimulus_on(self) -> None:
        # self.R_stimulus_active = True
        self.presenter_commands.append('turn_R_stimulus_on')

    def stimulus_C_on(self) -> None:
        self.presenter_commands.append('turn_stimulus_C_on')

    def stimuli_off(self) -> None:
        # self.L_stimulus_active = False
        # self.R_stimulus_active = False
        self.presenter_commands.append('turn_stimuli_off')

    def reset_stimuli(self) -> None:
        # self.L_stimulus_active = False
        # self.R_stimulus_active = False
        self.presenter_commands.append('reset_stimuli')

    def R_stimulus_off(self) -> None:
        self.R_stimulus_active = False
        self.presenter_commands.append('turn_R_stimulus_off')

    def set_dark_period_stimuli(self) -> None:
        self.presenter_commands.append('set_dark_period_stimuli')

    def enter_left_patch(self) -> None:
        logging.info(";" + str(time.time()) + ";[transition];enter_left_patch;" + str(""))
        if random.random() < self.session_info['p_stimulus']:
            self.L_stimulus_on()
            logging.info(";" + str(time.time()) + ";[action];left_stimulus_on;" + str(""))
        else:
            self.stimulus_C_on()
            logging.info(";" + str(time.time()) + ";[action];stimulus_C_on;" + str(""))

    def exit_left_patch(self):
        # self.reset_stimuli()
        logging.info(";" + str(time.time()) + ";[transition];exit_left_patch;" + str(""))

    def enter_right_patch(self) -> None:
        logging.info(";" + str(time.time()) + ";[transition];enter_right_patch;" + str(""))
        if random.random() < self.session_info['p_stimulus']:
            self.R_stimulus_on()
            logging.info(";" + str(time.time()) + ";[action];right_stimulus_on;" + str(""))
        else:
            self.stimulus_C_on()
            logging.info(";" + str(time.time()) + ";[action];stimulus_C_on;" + str(""))

    def exit_right_patch(self):
        # self.reset_stimuli()
        logging.info(";" + str(time.time()) + ";[transition];exit_right_patch;" + str(""))

    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(""))
        self.next_dark_time = time.time() + self.session_info['epoch_length']
        self.reset_counters()
        self.reset_stimuli()

    def enter_dark_period(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_dark_period;" + str(""))
        self.rewards_earned_in_block = 0
        self.set_dark_period_stimuli()

    def exit_dark_period(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_dark_period;" + str())
        self.next_dark_time = time.time() + self.session_info['epoch_length']

    def activate_dark_period(self):
        self.ITI_active = False
        if self.ITI_thread:
            self.ITI_thread.cancel()

        self.reset_counters()
        self.switch_to_dark_period()

    def reset_dark_period_timer(self):
        if self.dark_period_thread is not None:
            self.dark_period_thread.cancel()
        # self.dark_period_length = random.choice(self.session_info['dark_period_times'])
        t = threading.Timer(random.choice(self.session_info['dark_period_times']), self.end_dark_period)
        t.start()
        self.dark_period_thread = t
