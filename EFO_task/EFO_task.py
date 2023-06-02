# -*- coding: utf-8 -*-
"""
Created on Tue Oct 11 18:02:34 2022
First tentative to do a new 2 AFC task that has 4 pokes, with the 4th poke being
the reward that is delivered to the animal separate from the choices
@author: eliezyer
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

import behavbox

# adding timing capability to the state machine
@add_state_features(Timeout)
class TimedStateMachine(Machine):
    pass


class EFOTask(object):
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

        ########################################################################
        # Task has three possible states: standby, reward_available, and cue
        # Task has the following states: standby, trial_available, cue, choice_available, and reward_available (punishment?)
        ########################################################################
        self.states = [
            State(name="standby", on_enter=["enter_standby"], on_exit=["exit_standby"]),
            Timeout(
                name="initiate", #this is the trial available, init poke is lit
                on_enter=["enter_initiate"],
                on_exit=["exit_initiate"],
                timeout=self.session_info["initiate_timeout"],
                on_timeout=["restart"],
            ),
            Timeout(
                name="start_cue", #start cue is which poke the animal has to go (or free choice one), either left or right poke
                on_enter=["enter_start_cue"],
                on_exit=["exit_start_cue"],
                timeout=self.session_info["cue_timeout"],
                on_timeout=["restart"],
            ),
            Timeout(
                name="reward", #reward is available at the back poke, which is lit
                on_enter=["enter_reward"],
                on_exit=["exit_reward"],
            ),
        ]
        # can set later with task.machine.states['cue'].timeout etc.

        ########################################################################
        # list of possible transitions between states
        # format is: [event_name, source_state, destination_state]
        ########################################################################
        self.transitions = [
            ["trial_available", "standby", "initiate"],
            ["choice_available", "initiate", "start_cue"],
            ["reward_available", "start_cue", "reward"],
            ["restart", ["initiate", "cue_state", "reward_available"], "standby"]
        ]
        
        ########################################################################
        # initialize state machine and behavior box
        ########################################################################
        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial="standby",
        )
        self.trial_running = False

        # initialize behavior box
        self.box = behavbox.BehavBox(self.session_info)
        self.pump = behavbox.Pump()
        
        # trial statistics
        self.trial_number = 0
        self.error_count = 0
        self.error_list = []
        self.early_lick_error = False
        self.initiate_error = False
        self.cue_state_error = False
        self.wrong_choice_error = False
        self.multiple_choice_error = False
        self.error_repeat = False
        self.reward_time_start = None # for reward_available state time keeping purpose
        self.reward_time = 10 # sec. could be incorporate into the session_info; available time for reward
        self.reward_times_up = False
        self.total_reward = 0
        self.correct_trial_in_block = 0

        self.block_count = 0
        self.blocknumber = self.session_info['block_number']
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

    ########################################################################
    # functions called when state transitions occur
    ########################################################################
    
    
    def enter_standby(self):
        print('entering standby')
        # self.box.sound2.blink(0.5, 0.1, 1)
        self.trial_running = False

    def exit_standby(self):
        pass

    def enter_reward_available(self):
        print("entering reward_available")
        print("start white noise")
        self.box.sound1.blink(0.5, 0.1, 1)
        self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[0])
        self.trial_running = True

    def exit_reward_available(self):
        print("stop white noise")

    def enter_cue(self):
        print("deliver reward")
        self.box.cueLED4.on()
        self.box.sound3.blink(0.5, 0.1, 1)
        # self.pump.reward("left", self.session_info["reward_size"])
        print("start cue")
        self.box.cueLED4.off()
        # self.box.cueLED1.on()


    def exit_cue(self):
        print("stop cue")
        # self.box.sound3.blink(0.5, 0.1, 1)
        # self.box.cueLED1.off()

    ########################################################################
    # call the run() method repeatedly in a while loop in the main session
    # script it will process all detected events from the behavior box (e.g.
    # nosepokes and licks) and trigger the appropriate state transitions
    ########################################################################
    def run(self):

        # read in name of an event the box has detected
        if self.box.event_list:
            event_name = self.box.event_list.popleft()
        else:
            event_name = ""

        if self.state == "standby":
            pass

        elif self.state == "reward_available":
            if event_name == "left_IR_entry":
                # self.box.sound2.blink(0.5,0.1,1)
                self.pump.reward("1", self.session_info["reward_size"])
                self.active_poke()  # triggers state transition
            if event_name == "right_IR_entry":
                self.pump.reward("3", self.session_info["reward_size"])
                # self.box.sound2.blink(0.5,0.1,1)
                self.active_poke()  # triggers state transition
        elif self.state == "cue":
            # self.box.sound3.blink(0.5, 0.1, 1)
            pass

        # look for keystrokes
        self.box.check_keybd()
    
    def run(self):
        if self.box.event_list:
            self.event_name = self.box.event_list.popleft()
        else:
            self.event_name = ""
        # there can only be lick during the reward available state
        # if lick detected prior to reward available state
        # the trial will restart and transition to standby
        # if self.event_name == "left_entry" or self.event_name == "right_entry":
        #     # print("EVENT NAME !!!!!! " + self.event_name)
        #     if self.state == "reward_available" or self.state == "standby" or self.state == "initiate":
        #         pass
        #     else:
        #         # print("beeeeeeep") # debug signal
        #         self.early_lick_error = True
        #         self.error_repeat = True
        #         self.restart()
        if self.state == "standby":
            pass
        elif self.state == "initiate":
            self.distance_diff = self.get_distance() - self.distance_buffer
            if self.distance_diff >= self.distance_initiation:
                self.initiate_error = False
                self.start_cue()
            else:
                self.initiate_error = True
        elif self.state == "cue_state":
            # if self.LED_blink:
            #     self.box.cueLED1.blink(0.2, 0.1)
            self.distance_diff = self.get_distance() - self.distance_buffer
            if self.distance_diff >= self.distance_cue:
                self.cue_state_error = False
                self.evaluate_reward()
            else:
                self.cue_state_error = True
        elif self.state == "reward_available":
            if not self.reward_times_up:
                if self.reward_time_start:
                    if time.time() >= self.reward_time_start + self.reward_time:
                        self.restart()
            # first detect the lick signal:
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
                if cue_state == 'all':
                    side_choice = side_mice
                    if side_choice == 'left':
                        left_reward = self.session_info['reward_size'][self.current_card[2][0]]
                        reward_size = random.uniform(left_reward - self.session_info['reward_deviation'],
                                                     left_reward + self.session_info['reward_deviation'])
                        pump_num = self.current_card[3][0]
                    elif side_choice == 'right':
                        right_reward = self.session_info['reward_size'][self.current_card[2][1]]
                        reward_size = random.uniform(right_reward - self.session_info['reward_deviation'],
                                                     right_reward + self.session_info['reward_deviation'])
                        pump_num = self.current_card[3][1]
                else:
                    side_choice = self.current_card[1]
                    forced_reward = self.session_info['reward_size'][self.current_card[2]]
                    reward_size = random.uniform(forced_reward - self.session_info['reward_deviation'],
                                                 forced_reward + self.session_info['reward_deviation'])
                    pump_num = self.current_card[3]
                if side_mice == side_choice:  # if the animal chose correctly
                    print("Number of lick detected: " + str(self.lick_count))
                    if self.lick_count == 0:  # if this is the first lick
                        self.pump.reward(pump_num, reward_size)
                        self.total_reward += 1
                        self.correct_trial_in_block += 1
                        self.reward_time_start = time.time()
                        print("Reward time start" + str(self.reward_time_start))
                    self.lick_count += 1
                elif self.side_mice_buffer:
                    if self.lick_count == 0:
                        self.check_cue('sound2')
                        self.wrong_choice_error = True
                        self.restart()

        # look for keystrokes
        self.box.check_keybd()

    ########################################################################
    # methods to start and end the behavioral session
    ########################################################################
    def start_session(self):
        ic("TODO: start video")
        self.box.video_start()

    def end_session(self):
        ic("TODO: stop video")
        self.box.video_stop()
        self.box.visualstim.myscreen.close()