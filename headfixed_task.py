# python3: headfixed_task.py
"""
author: tian qiu
date: 2022-03-16
name: headfixed_task.py
goal: model_based reinforcement learning behavioral training task structure
description:
    an updated test version of soyoun_task.py

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

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
    }
)
# all modules above this line will have logging disabled

import behavbox


# adding timing capability to the state machine
@add_state_features(Timeout)
class TimedStateMachine(Machine):
    pass


class HeadfixedTask(object):
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
                    on_timeout=["restart"]),
            Timeout(name='cue_state',
                    on_enter=["enter_cue_state"],
                    on_exit=["exit_cue_state"],
                    timeout=self.session_info["cue_timeout"],
                    on_timeout=["restart"]),
            Timeout(name='reward_available',
                    on_enter=["enter_reward_available"],
                    on_exit=["exit_reward_available"],
                    timeout=self.session_info["reward_timeout"],
                    on_timeout=["restart"])
        ]
        self.transitions = [
            ['start_trial', 'standby', 'initiate'],  # format: ['trigger', 'origin', 'destination']
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
        self.trial_number = 0
        self.error_count = 0
        self.current_card = None

        # initialize behavior box
        self.box = behavbox.BehavBox(self.session_info)
        self.pump = behavbox.Pump()
        self.treadmill = self.box.treadmill
        self.distance_initiation = self.session_info['treadmill_setup']['distance_initiation']
        self.distance_buffer = self.treadmill.distance_cm
        self.distance_diff = 0
        self.sound_on = False

        # for refining the lick detection
        self.lick_count = 0

    ########################################################################
    # functions called when state transitions occur
    ########################################################################
    def run(self):
        self.box.sound1.off()
        if self.sound_on:

            self.box.sound1.blink(0.1, 0.9, 1)
        if self.box.event_list:
            event_name = self.box.event_list.popleft()
        else:
            event_name = ""
        if self.state == "standby":
            pass
        elif self.state == "initiate":
            self.distance_diff = self.treadmill.distance_cm - self.distance_buffer
            if self.distance_diff >= self.distance_initiation:
                self.start_cue()
            else:
                self.error_count += 1
        elif self.state == "cue_state":
            self.distance_diff = self.treadmill.distance_cm - self.distance_buffer
            distance_condition = self.current_card[1]
            distance_required = self.session_info['treadmill_setup'][distance_condition]
            if self.distance_diff >= distance_required:
                self.evaluate_reward()
            else:
                self.error_count += 1

        elif self.state == "reward_available":
            # first detect the lick signal:
            cue_state = self.current_card[0]
            side_choice = self.current_card[2]
            # question: do we want entry mark as lick?
            side_mice = None
            if event_name == "left_IR_entry":
                side_mice = 'left'
            elif event_name == "right_IR_entry":
                side_mice = 'right'
            if side_mice:
                reward_size = self.current_card[3]
                if cue_state == 'sound+LED':
                    if side_mice == 'left':
                        pump_num = '1'
                    elif side_mice == 'right':
                        pump_num = '2'
                    self.pump.reward(pump_num, self.session_info["reward_size"][reward_size])
                elif side_choice == side_mice:
                    print(str(self.lick_count))
                    if self.lick_count >= 2:
                        if side_mice == 'left':
                            self.pump.reward('1', self.session_info["reward_size"][reward_size])
                            self.lick_count = 0
                        elif side_mice == 'right':
                            self.pump.reward('2', self.session_info["reward_size"][reward_size])
                            self.lick_count = 0
                        self.restart()
                    else:
                        self.lick_count += 1
                else:
                    self.error_count += 1
                    self.lick_count = 0
                    self.restart()
            else:
                self.error_count += 1
                self.lick_count = 0
        # look for keystrokes
        self.box.check_keybd()

    def enter_standby(self):
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", entering standby")
        self.trial_running = False

    def exit_standby(self):
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", exiting standby")
        pass

    def enter_initiate(self):
        # check error_repeat
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", entering initiate")
        self.trial_running = True
        # wait for treadmill signal and process the treadmill signal
        self.distance_buffer = self.treadmill.distance_cm
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", treadmill distance t0: " + str(self.distance_buffer))

    def exit_initiate(self):
        # check the flag to see whether to shuffle or keep the original card
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", exiting initiate")

    def enter_cue_state(self):
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", entering cue state")
        # turn on the cue according to the current card
        self.check_cue(self.current_card[0])
        # wait for treadmill signal and process the treadmill signal
        self.distance_buffer = self.treadmill.distance_cm
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", treadmill distance t0: " + str(self.distance_buffer))

    def exit_cue_state(self):
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", exiting cue state")
        self.cue_off(self.current_card[0])

    def enter_reward_available(self):
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", entering reward available")
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", cue_state distance satisfied")
        self.cue_off(self.current_card[0])

    def exit_reward_available(self):
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", exiting reward available")
        pass

    def check_cue(self, cue):
        if cue == 'sound':
            logging.info(str(time.time()) + ", " + str(self.trial_number) + ", cue sound1 on")
            self.box.sound1.on()
            self.sound_on = True
        elif cue == 'LED':
            self.box.cueLED1.on()
            logging.info(str(time.time()) + ", " + str(self.trial_number) + ", cueLED1 on")
        else:
            self.box.cueLED1.on()
            self.box.sound1.blink(0.1, 0.9, 1)
            self.sound_on = True
            logging.info(str(time.time()) + ", " + str(self.trial_number) + ", sound1 + cueLED1 on (free choice)")

    def cue_off(self, cue):
        if cue == 'sound':
            self.sound_on = False
            logging.info(str(time.time()) + ", " + str(self.trial_number) + ", cue sound1 off")
            pass
        elif cue == 'LED':
            self.box.cueLED1.off()
            logging.info(str(time.time()) + ", " + str(self.trial_number) + ", cueLED1 off")
        else:
            self.sound_on = False
            self.box.cueLED1.off()
            logging.info(str(time.time()) + ", " + str(self.trial_number) + ", sound1 + cueLED1 off (free choice)")

    # def play_sound(self):
    #     if self.sound_on:
    #         self.box.sound1.blink(0.1, 0.9, 1)
    ########################################################################
    # methods to start and end the behavioral session
    ########################################################################
    def start_session(self):
        ic("TODO: start video")
        self.box.video_start()

    def end_session(self):
        ic("TODO: stop video")
        self.box.video_stop()