#!/usr/bin/env python
# coding: utf-8

"""
author: Julia Benville
date: 2024-10-01
name: julia_reinstatement_self_admin.py (adapted from julia_DCL_self_admin.py)
"""

import importlib
from transitions import Machine, State
from transitions.extensions.states import add_state_features, Timeout
import logging.config
import time
from datetime import datetime
from gpiozero import PWMLED
import threading

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

class ReinstatementSelfAdminLeverTask(object):
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
        self.mouse_weight = self.session_info['weight']

        # Define states and transitions (without catheter fill)
        self.states = [
            State(name='standby', on_exit=["exit_standby"]),
            State(name="reward_available", on_enter=["enter_reward_available"], on_exit=["exit_reward_available"]),
            Timeout(name='timeout', on_enter=['enter_timeout'], on_exit=['exit_timeout'], timeout=20, on_timeout=['switch_to_reward_available']),
            State(name='session_end', on_enter=["enter_session_end"]),
        ]

        self.transitions = [
            ['start_trial_logic', 'standby', 'reward_available'],
            ['switch_to_reward_available', 'timeout', 'reward_available'],
            ['switch_to_timeout', 'reward_available', 'timeout'],
            ['end_task', ['reward_available', 'timeout'], 'standby'],
            ['end_session', 'reward_available', 'session_end'],
        ]

        self.machine = TimedStateMachine(model=self, states=self.states, transitions=self.transitions, initial='standby')

        self.syringe_pump = PWMLED(17)
        self.start_time = time.time()

    def run(self):
        # Session ends after 2 hours, regardless of lever presses
        if (time.time() - self.start_time) >= 7200:  # 2 hours in seconds
            self.end_session()
            return

        if self.state == 'reward_available':
            threading.Timer(3, self.switch_to_timeout).start()  # Switch to timeout 3 seconds after lever press

    def enter_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_standby;")

    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;")

    def enter_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_reward_available;")

    def exit_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_reward_available;")

    def enter_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_timeout;")

    def exit_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_timeout;")

    def enter_session_end(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_session_end;")
        self.syringe_pump.off()

    def end_session(self):
        self.state = "session_end"
        logging.info("Session ended due to reaching the time limit.")

    def end_task(self):
        logging.info("Ending task...")

# Now you can create the new "run_julia_reinstatement_self_admin.py" script using this updated class.

if __name__ == "__main__":
    # Import session info and run the task
    from session_info_julia_IVSA import session_info

    task = ReinstatementSelfAdminLeverTask(name="julia_reinstatement_self_admin", session_info=session_info)
    task.start_trial_logic()

    # Loop until session ends
    while task.state != "session_end":
        task.run()

    # End the session
    task.end_session()
