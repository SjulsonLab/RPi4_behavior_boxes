# add in all the imports etc
# !/usr/bin/env python
# coding: utf-8
# In[ ]:
# python3: JB_Cocaine_Cue_Learning.py
"""
author: Julia Benville
date: 2024-08-05
name: JB_Cocaine_Cue_Learning.py (adapted from remi_self_admin_lever_task.py)
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

# from IPython.display import display, HTML
#
# display(HTML("<style>.container { width:100% !important; }</style>"))
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


class CocaineSelfAdminLeverTask(object):
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

        # Initialize the state for DRUG CUE LEARNING ONLY, this is NEW with the cath filling problem edited
        self.states = [
            State(name='standby',
                  on_exit=["exit_standby"]),
            State(name="reward_available",
                  on_enter=["enter_reward_available"],
                  on_exit=["exit_reward_available"]),
            Timeout(name='timeout',
                    on_enter=['enter_timeout'],
                    on_exit=['exit_timeout'],
                    timeout=self.session_info['timeout_time'],
                    on_timeout=['switch_to_reward_available']),
            Timeout(name='cath_fill',
                    on_enter=['enter_cath_fill'],
                    on_exit=['exit_cath_fill'],
                    timeout=self.session_info['cath_fill'],
                    on_timeout=['switch_to_reward_available'])]

        # Add a new state for ending the session when conditions are met
        self.states.append(
            State(name='session_end',
                  on_enter=["enter_session_end"])
        )

        self.transitions = [
            ['start_trial_logic', 'standby', 'cath_fill'],  # format: ['trigger', 'origin', 'destination']
            ['switch_to_reward_available', ['cath_fill', 'timeout'], 'reward_available'],
            ['switch_to_timeout', 'reward_available', 'timeout'],
            ['end_task', ['reward_available', 'timeout'], 'standby'],
            # New transition for ending the session
            ['end_session', 'reward_available', 'session_end'],
        ]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='standby')

        # trial statistics
        self.trial_running = False
        self.innocent = True
        self.trial_number = 0
        self.error_count = 0
        self.error_list = []
        self.error_repeat = False
        self.entry_time = 0.0
        self.entry_interval = self.session_info[
            "entry_interval"]  # update lever_press_interval to entry_interval--make this 3s instead of 1s
        self.reward_time = 10
        self.reward_times_up = False
        self.reward_pump1 = self.session_info["reward_pump1"]
        self.reward_pump2 = self.session_info['reward_pump2']
        self.DCL_time = 0  # changed from two contexts to this? just drug cue learning
        self.active_press = 0
        self.inactive_press = 0
        self.timeline_active_press = []
        self.active_press_count_list = []
        self.timeline_inactive_press = []
        self.inactive_press_count_list = []
        self.timeline_left_poke = []
        self.timeline_right_poke = []
        # initialize behavior box
        self.box = behavbox.BehavBox(self.session_info)
        self.pump = self.box.pump
        self.syringe_pump = LED(17)
        self.treadmill = self.box.treadmill
        # for refining the lick detection REMOVING
        self.reward_list = []
        self.left_poke_count_list = []
        self.right_poke_count_list = []
        # session_statistics
        self.total_reward = 0
        self.infusions = 0  # Track the number of infusions
        self.start_time = time.time()  # Record the start time of the session

    def reward(self):  # prototype mouse weight equals 30
        infusion_duration = (self.session_info['weight'] / 30)  # 6.25 uL for a 30g mouse
        self.syringe_pump.blink(2 * infusion_duration, 0.1, 1)  # 2 second infusion duration for 6.25 ul (hence 2*)
        self.reward_list.append(("syringe_pump_reward", 2 * infusion_duration))
        logging.info(";" + str(time.time()) + ";[reward];syringe_pump_reward" + str(2 * infusion_duration))

    def fill_cath(self):
        self.syringe_pump.blink(3.76, 0.1, 1)  # 3.125ul/second, calculated cath holds ~11.74ul; 3.76 seconds delivers ~12ul into cath; will need to update based on instech catheters
        logging.info(";" + str(time.time()) + ";[reward];catheter_filled_with_~12ul;" + '3.76_second_infusion')

    def run(self):
        if self.state == "standby" or self.state == 'timeout':
            pass
        elif self.state == 'reward_available':
            if self.box.event_list:
                self.event_name = self.box.event_list.popleft()
            else:
                self.event_name = ''

            # Check for session end condition (40 infusions or 2 hours)
            if self.infusions >= 40 or (time.time() - self.start_time) >= 7200:  # 7200 seconds = 2 hours
                self.end_session()
                return  # Exit run if session ended

            if self.event_name == 'right_entry':
                self.process_active_lever_press()  # Process the active lever press

        self.box.check_keybd()

    def process_active_lever_press(self):
        # New behavior for active lever press
        logging.info(";" + str(time.time()) + ";[lever_press];active_lever_pressed;")
        
        self.box.cueLED2.off()  # Turn off the LED
        self.box.sound2.on()  # Turn on the noise
        sleep(2)  # Wait for 2 seconds
        
        self.box.sound2.off()  # Turn off the noise after 2 seconds
        self.box.cueLED2.on()  # Turn the LED back on after 2 seconds
        
        sleep(1)  # Wait for 1 second before infusion
        self.reward()  # Infuse drug
        self.infusions += 1  # Increment infusion count
        self.switch_to_timeout()  # Switch to timeout state

    def enter_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_standby;")
        self.trial_running = False
        self.box.event_list.clear()

    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;")
        self.box.event_list.clear()
        self.fill_cath()

    def enter_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_reward_available;")
        self.box.cueLED2.on()
        self.box.event_list.clear()
        self.trial_running = True

    def exit_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_reward_available;")
        self.box.cueLED2.off()
        self.box.event_list.clear()

    def enter_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_timeout;")
        self.trial_running = False
        self.box.sound2.on()
        self.box.event_list.clear()

    def exit_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_timeout;")
        self.box.sound2.off()

    def enter_cath_fill(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_cath_fill;")
        self.trial_running = False
        self.box.event_list.clear()

    def exit_cath_fill(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_cath_fill;")
        self.fill_cath()

    def enter_session_end(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_session_end;")
        self.box.cueLED2.off()  # Turn off the LED
        # Add any other session end logic needed here

    def end_session(self):
        self.state = "session_end"
        logging.info("Session has ended due to reaching infusion limit or time limit.")

    def end_task(self):
        logging.info("Ending task...")
        self.box.clean_exit()

# to run it as a script
if __name__ == "__main__":
    task = CocaineSelfAdminLeverTask(name="MouseTest", session_info={'weight': 30, 'timeout_time': 10, 'cath_fill': 3})
    task.run()
