# python3: headfixed_task.py
"""
author: tian qiu & Soyoun Kim
date: 2024-02-25
name: headfixed_taskSoundLR.py
goal: to soundL/R choice with vibration with sound

"""
import importlib
from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
import pysistence, collections
from icecream import ic
import logging
import time
from datetime import datetime
import os
from gpiozero import PWMLED, LED, Button
from colorama import Fore, Style
import logging.config
from time import sleep
import random
import threading
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.figure as fg
import numpy as np

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
    }
)
# all modules above this line will have logging disabled

import sys
sys.path.insert(0,'/home/pi/RPi4_behavior_boxes/essential')
import behavbox


# adding timing capability to the state machine
@add_state_features(Timeout)
class TimedStateMachine(Machine):
    pass


class HeadfixedTaskSoundLR(object):
    # Define states. States where the animals is waited to make their decision

    def __init__(self, **kwargs):  # name and session_info should be provided as kwargs

        # if no name or session, make fake ones (for testing purposes)
        if kwargs.get("name", None) is None:
            self.name = "name"
            print(
                Fore.RED
                + Style.BRIGHT
                + "Warning: no name supplied; making fake one"
                + Style.RESET_ALL
            )
        else:
            self.name = kwargs.get("name", None)

        if kwargs.get("session_info", None) is None:
            print(
                Fore.RED
                + Style.BRIGHT
                + "Warning: no session_info supplied; making fake one"
                + Style.RESET_ALL
            )
            from fake_session_info import fake_session_info

            self.session_info = fake_session_info
        else:
            self.session_info = kwargs.get("session_info", None)
        ic(self.session_info)

        # initialize the state machine
        self.states = [
            State(name='standby',
                  on_enter=["enter_standby"],
                  on_exit=["exit_standby"]),
            Timeout(name="initiate",
                    on_enter=["enter_initiate"],
                    on_exit=["exit_initiate"],
                    timeout=self.session_info["initiation_timeout"],
                    on_timeout = ["restart"]),
            Timeout(name='cue_state',
                    on_enter=["enter_cue_state"],
                    on_exit=["exit_cue_state"],
                    timeout=self.session_info["cue_timeout"],
                    on_timeout=["restart"]),
            Timeout(name='reward_available',
                    on_enter=["enter_reward_available"],
                    on_exit=["exit_reward_available"],
                    timeout=self.session_info["wait_for_choice"],
                    on_timeout=["restart"])
        ]
        self.transitions = [
            ['start_trial', 'standby', 'initiate'],
            ['start_cue', 'initiate', 'cue_state'],
            ['evaluate_reward', 'cue_state', 'reward_available'],
            ['restart', ['initiate', 'cue_state', 'reward_available'], 'standby']
        ]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='standby'
        )
        self.trial_running = False

        # trial statistics
        self.correct_trial_number = 0
        self.actual_trial_number = 0
        self.error_count = 0
        self.error_list = []
        self.early_lick_error = False
        self.initiate_error = False
        self.cue_state_error = False
        self.wrong_choice_error = False
        self.multiple_choice_error = False
        self.error_repeat = False

        self.pump_num = None
        self.reward_size = None
        self.current_reward = None
        self.reward_check = False
        self.reward_size_offset = self.session_info['reward_size_offset']

        self.block_count = 0
        self.blocknumber = self.session_info["block_number"]
        self.current_card = None
        self.left_poke_count = 0
        self.right_poke_count = 0
        self.timeline_left_poke = []
        self.left_poke_count_list = []
        self.timeline_right_poke = []
        self.right_poke_count_list = []
        self.event_name = ""
        # initialize behavior box
        self.box = behavbox.BehavBox(self.session_info)
        self.pump = self.box.pump

        self.treadmill = self.box.treadmill

        self.distance_initiation = self.session_info['treadmill_setup']['distance_initiation']
        self.distance_cue = self.session_info['treadmill_setup']['distance_cue']
        self.distance_buffer = None
        self.distance_diff = 0

        self.cue_time = self.session_info['cue_time']
        self.initiation_time = self.session_info['initiation_time']
        self.time_diff = 0
        self.time_buffer = None
        self.extra_reward = self.session_info['extra_reward']
        self.extra_reward_size = self.session_info['extra_reward_size']


        # for foragaing parameters
        self.side_choice = None  # whether free choice is left or right
        self.cue_state = None

        # for refining the lick detection
        self.lick_count = 0
        self.side_mice_buffer = None
        self.LED_blink = False
        try:
            self.lick_threshold = self.session_info["lick_threshold"]
        except:
            print("No lick_threshold defined in session_info. Therefore, default defined as 1 \n")
            self.lick_threshold = 1

        # session_statistics
        self.total_reward = 0

    ########################################################################
    # functions called when state transitions occur
    ########################################################################
    def run(self):
        if self.box.event_list:
            self.event_name = self.box.event_list.popleft()
        else:
            self.event_name = ""

        # animal can lick any time during habituation
        # if lick detected correct reward pass the next reward
        #
        if self.event_name is "left_entry" or self.event_name == "right_entry":
            # print("EVENT NAME !!!!!! " + self.event_name)
            if self.state == "reward_available" or self.state == "standby" or self.state == "initiate":
                pass
            #else:
            #    self.early_lick_error = True
            #    self.error_repeat = True
            #    self.restart()
        if self.state == "standby":
            pass
        elif self.state == "initiate":
            self.time_diff = time.time() - self.time_buffer
            self.distance_diff = self.get_distance() - self.distance_buffer
            if self.time_diff >= self.initiation_time or self.distance_diff >= self.distance_initiation:
                self.initiate_error = False
                self.start_cue()
                if self.extra_reward:
                    self.pump.reward(self.current_card[2][0], self.extra_reward_size)
                    self.pump.reward(self.current_card[2][1], self.extra_reward_size)
            else:
                self.initiate_error = True
        elif self.state == "cue_state":
            self.distance_diff = self.get_distance() - self.distance_buffer
            self.time_diff = time.time() - self.time_buffer
            if self.distance_diff >= self.distance_cue or self.time_diff >= self.cue_time:
                self.cue_state_error = False
                self.evaluate_reward()
            else:
                self.cue_state_error = True
        elif self.state == "reward_available":
            cue_state = self.current_card[0]
            side_mice = None
            if self.event_name == "left_entry":
                side_mice = 'left'
                self.left_poke_count += 1
                self.left_poke_count_list.append(self.left_poke_count)
                self.timeline_left_poke.append(time.time())
            elif self.event_name == "right_entry":
                side_mice = 'right'
                self.right_poke_count += 1
                self.right_poke_count_list.append(self.right_poke_count)
                self.timeline_right_poke.append(time.time())
            if side_mice:
                self.side_mice_buffer = side_mice
                self.cue_state = cue_state # cue state for foraging
                if cue_state == 'all':
                    side_choice = side_mice
                    if side_choice == 'left':
                        self.pump_num = self.current_card[2][0]
                        self.reward_size = self.current_reward[0]
                        print("self.current_reward[0]: " + str(self.current_reward[0]))
                    elif side_choice == 'right':
                        self.pump_num = self.current_card[2][1]
                        self.reward_size = self.current_reward[1]
                        print("self.current_reward[0]: " + str(self.current_reward[1]))
                elif cue_state == 'L':
                    side_choice = self.current_card[1]
                    self.pump_num = self.current_card[2]
                    self.reward_size = self.current_reward[0]
                elif cue_state == 'R':
                    side_choice = self.current_card[1]
                    self.pump_num = self.current_card[2]
                    self.reward_size = self.current_reward[1]
                print("!!!!!!!!CUE_STATE: " + str(cue_state))
                if side_mice == side_choice:  # if the animal chose correctly
                    self.side_mice_buffer = side_mice
                    if side_mice == side_choice:  # if the animal chose correctly
                        if self.lick_count == 0:  # if this is the first lick
                            self.side_choice = side_choice # foraging task
                            self.wrong_choice_error = False
                            self.reward_check = True
                            self.lick_count += 1
                            self.restart()
                elif self.side_mice_buffer:
                    if self.lick_count == 0:
                        self.wrong_choice_error = True
                        self.lick_count += 1
                        self.restart()

        # look for keystrokes
        self.box.check_keybd()

    def enter_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_standby;" + str(self.error_repeat))
        self.update_plot_choice()
        # self.update_plot_error()
        self.trial_running = False
        # self.reward_error = False
        if self.early_lick_error:
            self.error_list.append("early_lick_error")
            logging.info(";" + str(time.time()) + ";[error];early_lick_error;" + str(self.error_repeat))
            #self.check_cue('sound2')
            self.early_lick_error = False
        print(str(time.time()) + ", Total reward up till current session: " + str(self.total_reward))
        logging.info(";" + str(time.time()) + ";[trial];trial_" + str(self.actual_trial_number) + ";" + str(self.error_repeat))

    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(self.error_repeat))
        self.lick_count = 0
        self.side_mice_buffer = None
        self.box.event_list.clear()
        pass

    def enter_initiate(self):
        # print("!!!!!!!!!!!event name is " + self.event_name) # for debugging purposes
        # check error_repeat
        logging.info(";" + str(time.time()) + ";[transition];enter_initiate;" + str(self.error_repeat))
        #self.check_cue('sound1')
        self.trial_running = True
        # wait for treadmill signal and process the treadmill signal
        self.distance_buffer = self.get_distance()
        self.time_buffer = time.time()
        logging.info(
            ";" + str(time.time()) + ";[treadmill];" + str(self.distance_buffer) + ";" + str(self.error_repeat))

    def exit_initiate(self):
        # check the flag to see whether to shuffle or keep the original card
        logging.info(";" + str(time.time()) + ";[transition];exit_initiate;" + str(self.error_repeat))
        print("EVENT NAME: " + str(self.box.event_list))
        #self.cue_off('sound1')
        if self.initiate_error:
            self.error_list.append('initiate_error')
            self.error_repeat = True
            logging.info(";" + str(time.time()) + ";[error];initiate_error;" + str(self.error_repeat))
            self.error_count += 1

    def enter_cue_state(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_cue_state;" + str(self.error_repeat))
        # turn on the cue according to the current card
        self.check_cue(self.current_card[0])
        # wait for treadmill signal and process the treadmill signal
        self.distance_buffer = self.get_distance()
        self.time_buffer = time.time()

        logging.info(
            ";" + str(time.time()) + ";[treadmill];" + str(self.distance_buffer) + ";" + str(self.error_repeat))

    def exit_cue_state(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_cue_state;" + str(self.error_repeat))
        self.cue_off(self.current_card[0])
        if not self.early_lick_error:
            if self.cue_state_error:
                #self.check_cue("sound2")
                self.error_list.append('cue_state_error')
                self.error_repeat = True
                logging.info(";" + str(time.time()) + ";[error];cue_state_error;" + str(self.error_repeat))
                self.error_count += 1
                self.cue_state_error = False

    def enter_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_reward_available;" + str(self.error_repeat))
        print(str(time.time()) + ", " + str(self.actual_trial_number) + ", cue_state distance satisfied")

    def exit_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_reward_available;" + str(self.error_repeat))
        if self.lick_count == 0:
            logging.info(";" + str(time.time()) + ";[error];no_choice_error;" + str(self.error_repeat))
            #self.check_cue('sound2')
            self.error_repeat = True
            self.error_count += 1
            self.error_list.append('no_choice_error')
        elif self.wrong_choice_error:
            logging.info(";" + str(time.time()) + ";[error];wrong_choice_error;" + str(self.error_repeat))
            #self.check_cue('sound2')
            self.error_repeat = True
            self.error_count += 1
            self.error_list.append('wrong_choice_error')
        elif self.reward_check:
            logging.info(";" + str(time.time()) + ";[error];correct_trial;" + str(self.error_repeat))
            self.pump.reward(self.pump_num, self.reward_size)
            self.error_repeat = False
            self.total_reward += 1
            self.reward_check = False
            self.error_list.append('correct_trial')
        self.pump_num = None
        self.reward_size = None
        self.wrong_choice_error = False


    def check_cue(self, cue):
        if cue == 'sound1':
            logging.info(";" + str(time.time()) + ";[cue];cue_sound1_on;" + str(self.error_repeat))
            self.box.sound1.on()
        if cue == 'sound2':
            logging.info(";" + str(time.time()) + ";[cue];cue_sound2_on;" + str(self.error_repeat))
            self.box.sound2.on()
        elif cue == 'LED_L':
            self.box.cueLED1.on()
            logging.info(";" + str(time.time()) + ";[cue];cueLED_L_on;" + str(self.error_repeat))

        elif cue == 'LED_R':
            self.box.cueLED2.on()
            logging.info(";" + str(time.time()) + ";[cue];cueLED_R_on;" + str(self.error_repeat))

        elif cue == 'L':
            logging.info(";" + str(time.time()) + ";[cue];cue_LED+soundL_on;" + str(self.error_repeat))
            self.box.sound1.on()
            self.box.cueLED1.on()

        elif cue == 'R':
            logging.info(";" + str(time.time()) + ";[cue];cue_LED+soundR_on;" + str(self.error_repeat))
            self.box.sound2.on()
            self.box.cueLED2.on()

        elif cue == 'all':
            self.box.cueLED1.on()
            self.box.cueLED2.on()
            self.box.sound1.on()
            self.box.sound2.on()
            logging.info(";" + str(time.time()) + ";[cue];LED_L+R_on; " + str(self.error_repeat))

    def cue_off(self, cue):
        if cue == 'all':
            self.box.cueLED1.off()
            self.box.cueLED2.off()
            self.box.sound1.off()
            self.box.sound2.off()
            logging.info(";" + str(time.time()) + ";[cue];LED_L+R_off; " + str(self.error_repeat))

        elif cue == 'sound1':
            self.box.sound1.off()
            logging.info(";" + str(time.time()) + ";[cue];cue_sound1_off;" + str(self.error_repeat))
        elif cue == 'sound2':
            self.box.sound2.off()
            logging.info(";" + str(time.time()) + ";[cue];cue_sound2_off;" + str(self.error_repeat))
        elif cue == 'LED_L':
            self.box.cueLED1.off()
            logging.info(";" + str(time.time()) + ";[cue];cueLED1_off;" + str(self.error_repeat))
        elif cue == 'LED_R':
            self.box.cueLED2.off()
            logging.info(";" + str(time.time()) + ";[cue];cueLED2_off;" + str(self.error_repeat))
        elif cue == 'L':
            self.box.cueLED1.off()
            self.box.sound1.off()
            logging.info(";" + str(time.time()) + ";[cue];cueLED+soundL_off;" + str(self.error_repeat))
        elif cue == 'R':
            self.box.cueLED2.off()
            self.box.sound2.off()
            logging.info(";" + str(time.time()) + ";[cue];cueLED+soundR_off;" + str(self.error_repeat))

    def get_distance(self):
        try:
            distance = self.treadmill.distance_cm
        except Exception as e:
            logging.info(";" + str(time.time()) + ";[system_error];" + str(e) + ";" + str(self.error_repeat))
            self.treadmill = self.box.treadmill
            distance = self.treadmill.distance_cm
        return distance



    def update_plot(self):
        fig, axes = plt.subplots(1, 1, )
        axes.plot([1, 2], [1, 2], color='green', label='test')
        self.box.check_plot(fig)

    def update_plot_error(self):
        error_event = self.error_list
        labels, counts = np.unique(error_event, return_counts=True)
        ticks = range(len(counts))
        fig, ax = plt.subplots(1, 1, )
        ax.bar(ticks, counts, align='center', tick_label=labels)
        ax = plt.gca()
        ax.set_xticks(ticks, labels)
        ax.set_xticklabels(labels=labels, rotation=70)

        self.box.check_plot(fig)

    def update_plot_choice(self, save_fig=False):
        trajectory_left = self.left_poke_count_list
        time_left = self.timeline_left_poke
        trajectory_right = self.right_poke_count_list
        time_right = self.timeline_right_poke
        fig, ax = plt.subplots(1, 1, )
        print(type(fig))

        ax.plot(time_left, trajectory_left, color='b', marker="o", label='left_lick_trajectory')
        ax.plot(time_right, trajectory_right, color='r', marker="o", label='right_lick_trajectory')
        if save_fig:
            plt.savefig(self.session_info['basedir'] + "/" + self.session_info['basename'] + "/" + \
                        self.session_info['basename'] + "_choice_plot" + '.png')
        self.box.check_plot(fig)

    def integrate_plot(self, save_fig=False):

        fig, ax = plt.subplots(2, 1)

        trajectory_left = self.left_poke_count_list
        time_left = self.timeline_left_poke
        trajectory_right = self.right_poke_count_list
        time_right = self.timeline_right_poke
        print(type(fig))

        ax[0].plot(time_left, trajectory_left, color='b', marker="o", label='left_lick_trajectory')
        ax[0].plot(time_right, trajectory_right, color='r', marker="o", label='right_lick_trajectory')

        error_event = self.error_list
        labels, counts = np.unique(error_event, return_counts=True)
        ticks = range(len(counts))
        ax[1].bar(ticks, counts, align='center', tick_label=labels)
        # plt.xticks(ticks, labels)
        # plt.title(session_name)
        ax[1] = plt.gca()
        ax[1].set_xticks(ticks, labels)
        ax[1].set_xticklabels(labels=labels, rotation=70)

        if save_fig:
            plt.savefig(self.session_info['basedir'] + "/" + self.session_info['basename'] + "/" + \
                        self.session_info['basename'] + "_summery" + '.png')
        self.box.check_plot(fig)

    ########################################################################
    # methods to start and end the behavioral session
    ########################################################################

    def start_session(self):
        ic("TODO: start video")
        self.box.video_start()

    def end_session(self):
        ic("TODO: stop video")
        self.update_plot_choice(save_fig=True)
        self.box.video_stop()