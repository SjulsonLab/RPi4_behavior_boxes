from task_protocol.latent_inference_forage.latent_inference_forage_presenter import LatentInferenceForagePresenter

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
from multiprocessing import Queue
import queue


# SEED = 0
# random.seed(SEED)

PUMP1_IX = 0
PUMP2_IX = 1
trial_choice_map = {'right': 0, 'left': 1}


class StimulusInferencePresenter(LatentInferenceForagePresenter):  # subclass from base task

    def __init__(self, model: Model, box: Box, pump: PumpBase, gui: GUI, session_info: dict):
        super().__init__(model, box, pump, gui, session_info)

        # threaded AV sync
        self.stimulus_A_thread = None
        self.stimulus_B_thread = None
        self.gratings_on = False
        self.dark_period_thread = None

        # multiprocess AV sync
        self.cur_sound_fn = None

        # self.box.visualstim.run_eventloop()
        if session_info['counterbalance_type'] == 'leftA':
            self.L_stimulus_on = self.stimulus_A_on
            self.R_stimulus_on = self.stimulus_B_on

            # self.L_sound_on = self.stimulus_A_sound_on
            # self.R_sound_on = self.stimulus_B_sound_on

        elif session_info['counterbalance_type'] == 'rightA':
            self.L_stimulus_on = self.stimulus_B_on
            self.R_stimulus_on = self.stimulus_A_on

            # self.L_sound_on = self.stimulus_B_sound_on
            # self.R_sound_on = self.stimulus_A_sound_on

        self.stimulus_C_on()

    # def stimulus_A_sound_on(self) -> None:
    #     # self.sounds_off()
    #     self.box.sound1.blink(0.1, 0.1)
    #
    # def stimulus_B_sound_on(self) -> None:
    #     # self.sounds_off()
    #     self.box.sound1.blink(0.2, 0.1)

    # multiprocessing AV sync
    # def stimulus_A_on(self) -> None:
    #     self.cur_sound_fn = self.stimulus_A_sound_on
    #     self.box.visualstim.stimulus_A_on()
    #
    # def stimulus_B_on(self) -> None:
    #     self.cur_sound_fn = self.stimulus_B_sound_on
    #     self.box.visualstim.stimulus_B_on()

    # multithreaded AV sync
    def stimulus_A_on(self) -> None:
        grating_name = 'vertical_grating_{}s.dat'.format(self.session_info['grating_duration'])
        sound_on_time = 0.1
        self.stimulus_A_thread = Thread(target=self.stimulus_loop, args=(grating_name, sound_on_time, self.stimulus_B_thread))
        logging.info(";" + str(time.time()) + ";[stimulus];" + "stimulus_A_on")
        self.stimulus_A_thread.start()

    def stimulus_B_on(self) -> None:
        grating_name = 'horizontal_grating_{}s.dat'.format(self.session_info['grating_duration'])
        sound_on_time = 0.2
        self.stimulus_B_thread = Thread(target=self.stimulus_loop, args=(grating_name, sound_on_time, self.stimulus_A_thread))
        logging.info(";" + str(time.time()) + ";[stimulus];" + "stimulus_B_on")
        self.stimulus_B_thread.start()

    def stimulus_C_on(self) -> None:
        logging.info(";" + str(time.time()) + ";[stimulus];" + "stimulus_C_on")
        # self.box.sound1.off()
        # self.box.sound2.on()
        self.box.sound2.off()
        self.box.sound1.on()
        self.box.visualstim.display_default_greyscale()

    def join_stimulus_threads(self) -> None:
        # threads
        self.gratings_on = False
        if self.stimulus_A_thread is not None:
            self.stimulus_A_thread.join()
        if self.stimulus_B_thread is not None:
            self.stimulus_B_thread.join()

        # parallel processes
        # self.box.visualstim.end_gratings_process()

    def stimulus_loop(self, grating_name: str, sound_on_time: float, prev_stim_thread: Thread) -> None:
        if prev_stim_thread is not None:
            self.gratings_on = False
            prev_stim_thread.join()

        t_start = time.perf_counter()
        self.gratings_on = True
        while self.gratings_on and time.perf_counter() - t_start < self.session_info['stimulus_duration']:
            self.box.visualstim.show_grating(grating_name)
            # self.box.sound2.off()
            # self.box.sound1.blink(sound_on_time, 0.1)
            self.box.sound1.off()
            self.box.sound2.blink(sound_on_time, 0.1)

            time.sleep(self.session_info['grating_duration'])
            # self.sounds_off()
            self.stimulus_C_on()
            time.sleep(self.session_info['inter_grating_interval'])

        self.gratings_on = False

    def set_dark_period_stimuli(self) -> None:
        # Set all stimuli off during dark period. To be run in a thread which waits for the stimulus loop or parallel
        # process to finish before turning off the stimuli.
        self.join_stimulus_threads()
        if self.task.state == 'dark_period':
            self.stimuli_off()
            self.task.reset_dark_period_timer()  # guarantee a full interval of darkness

    def sounds_off(self) -> None:
        self.box.sound1.off()
        self.box.sound2.off()

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
        self.join_stimulus_threads()
        self.box.visualstim.display_dark_greyscale()
        logging.info(";" + str(time.time()) + ";[stimulus];" + "stimuli_off")

    def stimulus_process_done(self) -> None:
        self.box.visualstim.gratings_on = False

    def match_command(self, command: str, correct_pump: int, incorrect_pump: int) -> None:
        # give reward if
        # 1. training reward/human reward (give reward, regardless of action)
        # 2. correct choice and meets correct reward probability
        # 3. incorrect but REAL choice (i.e. not a switch) and meets incorrect reward probability
        # state changes if choice is correct and switch probability is met
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
            logging.info(";" + str(time.time()) + ";[action];stimulus_C_on;" + str(""))

        elif command == 'reset_stimuli':
            self.stimuli_reset()
            logging.info(";" + str(time.time()) + ";[action];stimuli_reset;" + str(""))

        elif command == 'turn_sounds_on':
            self.cur_sound_fn()
            logging.info(";" + str(time.time()) + ";[action];sounds_on;" + str(""))

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

        elif command == 'set_dark_period_stimuli':
            self.dark_period_thread = Thread(target=self.set_dark_period_stimuli)
            self.dark_period_thread.start()

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

        # multiprocessing
        try:
            while True:
                c = self.box.visualstim.presenter_commands.get(block=False)
                self.match_command(c, correct_pump, incorrect_pump)
        except queue.Empty:
            pass

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

        self.gui.figure_window.state_text.set_text('State: {}; ITI: {}'.format(self.task.state, self.task.ITI_active))
        self.gui.figure_window.stimulus_text.set_text('Stimulus on: {}'.format(self.box.visualstim.gratings_on))
        # self.gui.figure_window.stimulus_text.set_text('Stimulus on: {}'.format(self.gratings_on))
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
