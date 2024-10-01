#!/usr/bin/env python
# coding: utf-8

"""
author: Julia Benville
date: 2024-10-01
name: julia_extinction_self_admin.py (adapted from julia_DCL_self_admin.py)
"""

import importlib
from transitions import Machine, State
import logging
import time
from datetime import datetime
import os
from gpiozero import LED
from colorama import Fore, Style
import threading

# Configure logging
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
    }
)

class ExtinctionSelfAdminLeverTask(object):
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

        # Define states and transitions
        self.states = [
            State(name='reward_available', on_enter=["enter_reward_available"], on_exit=["exit_reward_available"]),
            State(name='session_end', on_enter=["enter_session_end"])
        ]

        self.transitions = [
            ['start_trial_logic', 'reward_available', 'reward_available'],  # Always stays in reward_available
            ['end_session', 'reward_available', 'session_end'],
        ]

        self.machine = Machine(model=self, states=self.states, transitions=self.transitions, initial='reward_available')

        self.light = LED(17)  # Assuming a light is connected to GPIO pin 17
        self.light.on()  # Turn on the light at the start of the session

        self.infusions = 0
        self.lever_presses = 0
        self.start_time = time.time()

    def run(self):
        # Keep track of lever presses but don't change any state or trigger any events
        self.lever_presses += 1
        logging.info(f";{time.time()};[press];lever_press;{self.lever_presses}")

        if (time.time() - self.start_time) >= 7200:  # End session after 2 hours (7200 seconds)
            self.end_session()

    def enter_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_reward_available;")
        print("Session started, light is on. Lever presses will be tracked but have no effect.")

    def exit_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_reward_available;")

    def enter_session_end(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_session_end;")
        self.light.off()  # Turn off the light when the session ends
        print(Fore.RED + Style.BRIGHT + "Session ended after 2 hours" + Style.RESET_ALL)

    def end_session(self):
        self.state = "session_end"
        logging.info("Session ended after 2 hours.")
        self.light.off()
