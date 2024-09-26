#!/usr/bin/env python
# coding: utf-8

"""
author: Julia Benville
date: 2024-08-05
name: JB_Cocaine_Cue_Learning.py (adapted from remi_self_admin_lever_task.py)
"""

import importlib
from transitions import Machine, State
from transitions.extensions.states import add_state_features, Timeout
import pysistence
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
import matplotlib.pyplot as plt
import numpy as np
import behavbox

# Configure logging
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
    }
)

# Adding timing capability to the state machine
@add_state_features(Timeout)
class TimedStateMachine(Machine):
    pass


class CocaineSelfAdminLeverTask(object):
    def __init__(self, **kwargs):
        # Set name and session_info
        if kwargs.get("name", None) is None:
            self.name = "name"
            print(Fore.RED + Style.BRIGHT + "Warning: no name supplied; using default 'name'" + Style.RESET_ALL)
        else:
            self.name = kwargs.get("name")
        
        if kwargs.get("session_info", None) is None:
            print(Fore.RED + Style.BRIGHT + "Warning: no session_info supplied; using default session_info" + Style.RESET_ALL)
            from fake_session_info import fake_session_info
            self.session_info = fake_session_info
        else:
            self.session_info = kwargs.get("session_info")

        ic(self.session_info)

        # Define states and transitions
        self.states = [
            State(name='standby', on_exit=["exit_standby"]),
            State(name="reward_available", on_enter=["enter_reward_available"], on_exit=["exit_reward_available"]),
            Timeout(name='timeout', on_enter=['enter_timeout'], on_exit=['exit_timeout'], timeout=self.session_info['timeout_time'], on_timeout=['switch_to_reward_available']),
            Timeout(name='cath_fill', on_enter=['enter_cath_fill'], on_exit=['exit_cath_fill'], timeout=self.session_info['cath_fill'], on_timeout=['switch_to_reward_available'])
        ]

        self.states.append(State(name='session_end', on_enter=["enter_session_end"]))

        self.transitions = [
            ['start_trial_logic', 'standby', 'cath_fill'],
            ['switch_to_reward_available', ['cath_fill', 'timeout'], 'reward_available'],
            ['switch_to_timeout', 'reward_available', 'timeout'],
            ['end_task', ['reward_available', 'timeout'], 'standby'],
            ['end_session', 'reward_available', 'session_end'],
        ]

        self.machine = TimedStateMachine(model=self, states=self.states, transitions=self.transitions, initial='standby')

        # Initialize variables for trials
        self.trial_running = False
        self.trial_number = 0
        self.entry_interval = self.session_info['entry_interval']
        self.reward_time = 10
        self.reward_list = []
        self.infusions = 0  # Track the number of infusions
        self.start_time = time.time()  # Record session start time
        
        # Initialize behavior box
        self.box = behavbox.BehavBox(self.session_info)
        self.syringe_pump = LED(17)
        self.total_reward = 0

    def reward(self):
        # Updated for 0.75 mg/kg dose with a 12.5 µL infusion per bolus
        infusion_duration = 12.5 / 3.125  # 12.5 µL at 3.125 µL/sec rate
        self.syringe_pump.blink(infusion_duration, 0.1, 1)  # Infuse drug for calculated duration
        self.reward_list.append(("syringe_pump_reward", infusion_duration))
        logging.info(";" + str(time.time()) + ";[reward];syringe_pump_reward;" + str(infusion_duration))

    def fill_cath(self):
        # Update to fill catheter with ~12 µL
        infusion_duration = 12 / 3.125  # 12 µL at 3.125 µL/sec rate
        self.syringe_pump.blink(infusion_duration, 0.1, 1)  # Infuse ~12 µL
        logging.info(";" + str(time.time()) + ";[reward];catheter_filled_with_~12ul;" + str(infusion_duration) + "_second_infusion")

    def run(self):
        if self.state in ["standby", "timeout"]:
            pass
        elif self.state == 'reward_available':
            if self.box.event_list:
                self.event_name = self.box.event_list.popleft()
            else:
                self.event_name = ''

            # Check for session end (40 infusions or 2 hours)
            if self.infusions >= 40 or (time.time() - self.start_time) >= 7200:
                self.end_session()
                return

            if self.event_name == 'right_entry':
                self.process_active_lever_press()

        self.box.check_keybd()

    def process_active_lever_press(self):
        logging.info(";" + str(time.time()) + ";[lever_press];active_lever_pressed;")
        self.box.cueLED2.off()  # Turn off LED
        self.box.sound2.on()  # Play sound
        sleep(2)
        self.box.sound2.off()  # Turn sound off
        self.box.cueLED2.on()  # Turn LED back on
        sleep(1)
        self.reward()  # Infuse drug
        self.infusions += 1
        self.switch_to_timeout()

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
        self.box.cueLED2.off()

    def end_session(self):
        self.state = "session_end"
        logging.info("Session ended due to reaching infusion or time limit.")

    def end_task(self):
        logging.info("Ending task...")
        self.box.clean_exit()


# To run as a script
if __name__ == "__main__":
    task = CocaineSelfAdminLeverTask(name="MouseTest", session_info={'weight': 30, 'timeout_time': 10, 'cath_fill': 3})
    task.run()
