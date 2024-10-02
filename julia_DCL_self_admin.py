#!/usr/bin/env python
# coding: utf-8

"""
author: Julia Benville
date: 2024-08-05
name: julia_DCL_self_admin.py (adapted from remi_self_admin_lever_task.py)
"""

import importlib
from transitions import Machine, State
from transitions.extensions.states import add_state_features, Timeout
import pysistence
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

        # Access mouse weight from session info
        self.mouse_weight = self.session_info['weight']  # Read mouse weight from session_info

        # Define drug dosage parameters
        self.dosage_mg_per_kg = 0.75  # 0.75 mg/kg dosage per infusion
        self.infusion_rate_ul_per_sec = 6.25  # Infusion rate in µL/sec (converted from 375 µL/min)
        self.solution_concentration_mg_per_ml = 1.8  # Concentration of cocaine solution in mg/mL

        # Calculate the required dosage for this mouse in mg per infusion
        dosage_mg = self.dosage_mg_per_kg * self.mouse_weight  # Amount of cocaine in mg needed per infusion

        # Calculate the required bolus volume in µL based on the solution concentration
        self.bolus_volume_ul = (dosage_mg / self.solution_concentration_mg_per_ml) * 1000  # Convert from mL to µL

        # Calculate infusion time in seconds based on bolus volume and infusion rate
        self.infusion_time_sec = self.bolus_volume_ul / self.infusion_rate_ul_per_sec

        # Print statements for debugging (optional)
        print(f"Mouse weight: {self.mouse_weight} kg")
        print(f"Dosage per infusion: {dosage_mg} mg")
        print(f"Bolus volume: {self.bolus_volume_ul} µL")
        print(f"Infusion time: {self.infusion_time_sec} seconds")

# Now, you can use self.bolus_volume_ul and self.infusion_time_sec to control your infusion pump.

        # Define states and transitions
        self.states = [
            State(name='standby', on_exit=["exit_standby"]),
            State(name="reward_available", on_enter=["enter_reward_available"], on_exit=["exit_reward_available"]),
            Timeout(name='timeout', on_enter=['enter_timeout'], on_exit=['exit_timeout'], timeout=20, on_timeout=['switch_to_reward_available']),
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

        self.syringe_pump = PWMLED(17)
        self.infusions = 0
        self.start_time = time.time()

    def calculate_infusion_duration(self):
        # Calculate drug infusion duration based on bolus volume and infusion rate
        dose_volume = self.bolus_volume_ul
        infusion_duration = dose_volume / self.infusion_rate_ul_per_sec
        return infusion_duration

    def reward(self):
        # Infusion duration calculation
        infusion_duration = self.calculate_infusion_duration()

        # Infuse drug for calculated duration
        self.syringe_pump.blink(infusion_duration, 0.1, 1)
        logging.info(f";{time.time()};[reward];syringe_pump_reward;{infusion_duration}")

    def fill_cath(self):
        # Use 'cath_fill' value from session_info for the catheter fill duration
        self.syringe_pump.blink(self.session_info['cath_fill'], 0.1, 1)
        logging.info(";" + str(time.time()) + ";[reward];catheter_filled_with_~12ul")

    def run(self):
        if self.state in ["standby", "timeout"]:
            pass
        elif self.state == 'reward_available':
            if self.infusions >= 40 or (time.time() - self.start_time) >= 7200:
                self.end_session()
                return
            self.infusions += 1
            threading.Timer(3, self.reward).start()  # Start infusion 3 seconds after lever press
            threading.Timer(3, self.switch_to_timeout).start()  # Switch to timeout 3 seconds after lever press

    def enter_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_standby;")

    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;")
        self.fill_cath()

    def enter_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_reward_available;")

    def exit_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_reward_available;")

    def enter_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_timeout;")

    def exit_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_timeout;")

    def enter_cath_fill(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_cath_fill;")

    def exit_cath_fill(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_cath_fill;")
        self.fill_cath()

    def enter_session_end(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_session_end;")
        self.syringe_pump.off()

    def end_session(self):
        self.state = "session_end"
        logging.info("Session ended due to reaching infusion or time limit.")

    def end_task(self):
        logging.info("Ending task...")
