from task_protocol.latent_inference_forage.latent_inference_presenter import LatentInferencePresenter

import collections
from typing import Tuple, List, Callable

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import random

from icecream import ic
import time
import logging
from essential.base_classes import Presenter, Model, GUI, Box, PumpBase
from threading import Thread


# SEED = 0
# random.seed(SEED)

PUMP1_IX = 0
PUMP2_IX = 1
trial_choice_map = {'right': 0, 'left': 1}


class StimulusInferencePresenter(LatentInferencePresenter):  # subclass from base task

    def __init__(self, model: Model, box: Box, pump: PumpBase, gui: GUI, session_info: dict):
        super().__init__(model, box, pump, gui, session_info)

        # threaded AV sync
        self.stimulus_A_thread = None
        self.stimulus_B_thread = None
        self.gratings_on = False
        self.dark_period_thread = None
        self.current_stimulus = None
        self.previous_stimulus = None

        if session_info['counterbalance_type'] == 'leftA':
            self.L_stimulus_on = self.stimulus_A_on
            self.R_stimulus_on = self.stimulus_B_on

        elif session_info['counterbalance_type'] == 'rightA':
            self.L_stimulus_on = self.stimulus_B_on
            self.R_stimulus_on = self.stimulus_A_on

        self.stimulus_C_on()

    def play_soundA(self):
        # for some reason sound1 (white noise) is physically connected to DIO2, and sound2 (tone) is connected to DIO1
        # that means you need to control sounds 1 and 3 for stimuli A and B - change this if the physical setup changes
        if self.session_info['ephys_rig']:
            self.box.sound1.off()
            self.box.sound2.off()
            self.box.sound3.blink(on_time=.1, off_time=0.1)
        else:
            self.box.sound2.off()
            self.box.sound3.off()
            self.box.sound1.blink(on_time=.1, off_time=0.1)

    def play_soundB(self):
        # for some reason sound1 (white noise) is physically connected to DIO2, and sound2 (tone) is connected to DIO1
        # that means you need to control sounds 1 and 3 for stimuli A and B - change this if the physical setup changes
        if self.session_info['ephys_rig']:
            if self.session_info['num_sounds'] == 2:
                self.box.sound2.off()
                self.box.sound3.off()
                self.box.sound1.blink(on_time=.2, off_time=0.1)
            else:
                self.box.sound1.off()
                self.box.sound2.off()
                self.box.sound3.blink(on_time=.2, off_time=0.1)

        else:
            if self.session_info['num_sounds'] == 2:
                self.box.sound1.off()
                self.box.sound2.off()
                self.box.sound3.blink(on_time=.2, off_time=0.1)
            else:
                self.box.sound2.off()
                self.box.sound3.off()
                self.box.sound1.blink(on_time=.2, off_time=0.1)

    def stimulus_A_on(self) -> None:
        grating_name = 'vertical_grating_{}s.dat'.format(self.session_info['grating_duration'])
        sound_on_time = 0.1
        # self.stimulus_A_thread = Thread(target=self.stimulus_loop, args=(grating_name, sound_on_time, self.stimulus_B_thread))
        self.stimulus_A_thread = Thread(target=self.stimulus_loop, args=(grating_name, self.play_soundA, self.stimulus_B_thread))
        # logging.info(";" + str(time.time()) + ";[stimulus];" + "stimulus_A_on;")
        self.current_stimulus = 'A'
        self.stimulus_A_thread.start()

    def stimulus_B_on(self) -> None:
        grating_name = 'horizontal_grating_{}s.dat'.format(self.session_info['grating_duration'])
        sound_on_time = 0.2
        # self.stimulus_B_thread = Thread(target=self.stimulus_loop, args=(grating_name, sound_on_time, self.stimulus_A_thread))
        self.stimulus_B_thread = Thread(target=self.stimulus_loop, args=(grating_name, self.play_soundB, self.stimulus_A_thread))
        # logging.info(";" + str(time.time()) + ";[stimulus];" + "stimulus_B_on;")
        self.current_stimulus = 'B'
        self.stimulus_B_thread.start()

    def stimulus_C_on(self) -> None:
        logging.info(";" + str(time.time()) + ";[stimulus];" + "stimulus_C_on;")
        self.box.sound1.off()
        self.box.sound3.off()
        self.box.sound2.on()
        # self.box.sound2.off()
        # self.box.sound1.on()
        self.box.visualstim.display_default_greyscale()

    def join_stimulus_threads(self) -> None:
        self.gratings_on = False
        if self.stimulus_A_thread is not None:
            self.stimulus_A_thread.join()
        if self.stimulus_B_thread is not None:
            self.stimulus_B_thread.join()

    def stimulus_loop(self, grating_name: str, sound_fn: Callable, prev_stim_thread: Thread) -> None:
        if prev_stim_thread is not None and prev_stim_thread.is_alive():
            self.gratings_on = False
            prev_stim_thread.join()
            logging.info(";" + str(time.time()) + ";[stimulus];" + "stimulus_{}_off;".format(self.previous_stimulus))

        t_start = time.perf_counter()
        self.gratings_on = True
        logging.info(";" + str(time.time()) + ";[stimulus];" + "stimulus_{}_on;".format(self.current_stimulus))
        self.previous_stimulus = self.current_stimulus
        while (self.gratings_on and time.perf_counter() - t_start < self.session_info['stimulus_duration'] and
               self.task.state != 'dark_period'):
            self.box.visualstim.show_grating(grating_name)
            sound_fn()

            time.sleep(self.session_info['grating_duration'])
            if self.task.state == 'dark_period':
                self.stimuli_off()
                break

            self.stimulus_C_on()
            time.sleep(self.session_info['inter_grating_interval'])

        logging.info(";" + str(time.time()) + ";[stimulus];" + "stimulus_{}_off;".format(self.current_stimulus))
        self.gratings_on = False

    def set_dark_period_stimuli(self) -> None:
        # Set all stimuli off during dark period. To be run in a thread which waits for the stimulus loop or parallel
        # process to finish before turning off the stimuli.
        self.join_stimulus_threads()
        self.stimuli_off()
        self.task.reset_dark_period_timer()  # guarantee a full interval of darkness

    def sounds_off(self) -> None:
        self.box.sound1.off()
        self.box.sound2.off()
        self.box.sound3.off()

    def stimuli_reset(self) -> None:
        self.sounds_off()
        self.join_stimulus_threads()
        self.box.visualstim.gratings_on = False
        self.box.visualstim.display_default_greyscale()
        # self.stimulus_C_on()

    def stimuli_off(self) -> None:
        self.box.cueLED1.off()
        self.box.cueLED2.off()
        self.sounds_off()
        # self.join_stimulus_threads()
        self.box.visualstim.display_dark_greyscale()
        logging.info(";" + str(time.time()) + ";[stimulus];" + "stimuli_off;")

    def stimulus_process_done(self) -> None:
        self.box.visualstim.gratings_on = False

    def match_command(self, command: str, correct_pump: str, incorrect_pump: str) -> None:
        ic('received command:', command)
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

        elif command == 'reset_stimuli':
            self.stimuli_reset()
            logging.info(";" + str(time.time()) + ";[action];stimuli_reset;" + str(""))

        elif command == 'turn_sounds_off':
            self.sounds_off()
            logging.info(";" + str(time.time()) + ";[action];sounds_off;" + str(""))

        elif command == 'turn_stimuli_off':
            self.stimuli_off()
            logging.info(";" + str(time.time()) + ";[action];stimuli_off;" + str(""))

        elif command == 'stimulus_process_done':
            self.stimulus_process_done()

        elif command == 'give_training_reward':
            reward_size = self.reward_size_large
            logging.info(";" + str(time.time()) + ";[reward];giving_reward;" + str(""))
            self.deliver_reward(pump_key=correct_pump, reward_size=reward_size)

        elif command == 'give_correct_reward':
            reward_size = self.reward_size_large
            self.deliver_reward(pump_key=correct_pump, reward_size=reward_size)

        elif command == 'give_incorrect_reward':
            reward_size = self.reward_size_small
            self.deliver_reward(pump_key=incorrect_pump, reward_size=reward_size)

        elif command == 'set_dark_period_stimuli':
            self.dark_period_thread = Thread(target=self.set_dark_period_stimuli)
            self.dark_period_thread.start()

        else:
            raise ValueError('Presenter command not recognized')

        # switch_flag = ((command in ['give_training_reward', 'give_correct_reward'] and random.random() < self.session_info['switch_probability']) or
        #                self.task.consecutive_correct_trials >= self.task.max_consecutive_correct_trials)
        # if switch_flag:
        #     # if self.session_info['control']:  # control should only ever use right port/patch
        #     #     self.task.switch_to_right_patch()
        #     # elif
        #
        #     self.task.consecutive_correct_trials = 0
        #     if self.task.state == 'right_patch':
        #         self.task.switch_to_left_patch()
        #     elif self.task.state == 'left_patch':
        #         self.task.switch_to_right_patch()
        #     else:
        #         pass
                # raise RuntimeError('state not recognized')

        # print('current state: {}; rewards earned in block: {}'.format(self.task.state,
        #                                                               self.task.rewards_earned_in_block))

    def perform_task_commands(self, correct_pump: str, incorrect_pump: str) -> None:
        for i in range(len(self.task.presenter_commands)):
            c = self.task.presenter_commands.pop(0)
            self.match_command(c, correct_pump, incorrect_pump)

    def update_plot(self, save_fig=False, n_plot=20) -> None:
        if self.task.trial_choice_list:
            correct_ix = np.array(self.task.trial_correct_list)[-n_plot:]
            reward_ix = np.array(self.task.trial_reward_given)[-n_plot:]
            choices = np.array(self.task.trial_choice_list)[-n_plot:]
            times = np.array(self.task.trial_choice_times)[-n_plot:]

            correct_trials = choices[correct_ix]
            correct_times = times[correct_ix]

            incorrect_trials = choices[~correct_ix]
            incorrect_times = times[~correct_ix]

            reward_trials = choices[reward_ix]
            reward_times = times[reward_ix]

            self.gui.figure_window.correct_line.set_data(correct_times, correct_trials)
            self.gui.figure_window.error_line.set_data(incorrect_times, incorrect_trials)
            self.gui.figure_window.reward_line.set_data(reward_times, reward_trials)

            # update this to show the last 20-ish trials
            if times.size > 1:
                T = [times[-n_plot:][0], times[-1]]
            else:
                T = [times[-1] - .5, times[-1] + .5]
            plt.xlim(T)

        self.gui.figure_window.state_text.set_text('State: {}; ITI: {}'.format(self.task.state, self.task.ITI_active))
        self.gui.figure_window.stimulus_text.set_text('Stimulus on: {}'.format(self.gratings_on))
        self.gui.check_plot(figure=self.gui.figure_window.figure, savefig=save_fig)

    def K_z_callback(self) -> None:
        # L stimulus on
        self.task.L_stimulus_on()
        logging.info(";" + str(time.time()) + ";[action];user_triggered_L_stimulus_on;" + str(""))

    def K_x_callback(self) -> None:
        # R stimulus on
        self.task.R_stimulus_on()
        logging.info(";" + str(time.time()) + ";[action];user_triggered_R_stimulus_on;" + str(""))

    def print_controls(self) -> None:
        print("[***] KEYBOARD CONTROLS [***]")
        print("1, 2, 3: left/center/right nosepoke entry")
        print("q, w, e, r: pump 1/2/3/4 reward delivery")
        print("t: vacuum activation")
        print("a: toggle automated training rewards")
        print("g: give training reward")
        print("z, x: L/R stimulus on")
