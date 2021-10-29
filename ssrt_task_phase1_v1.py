from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
import pysistence, collections
from icecream import ic
import logging
from datetime import datetime
import os
from gpiozero import PWMLED, LED, Button
from colorama import Fore, Style
import logging.config
import time
import numpy as np
# from matplotlib import pyplot as plt
# from matplotlib.animation import FuncAnimation

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
    }
)
# all modules above this line will have logging disabled

import behavbox_DT

# adding timing capability to the state machine
@add_state_features(Timeout)
class TimedStateMachine(Machine):
    pass


class ssrt_task(object):
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
            from fake_ssrt_session_info import fake_ssrt_session_info

            self.session_info = fake_ssrt_session_info
        else:
            self.session_info = kwargs.get("session_info", None)
        ic(self.session_info)

        ########################################################################
        # Task has many possible states
        ########################################################################
        self.states = [
            State(name="standby", on_enter=["enter_standby"], on_exit=["exit_standby"]),
            # initiation state: LED light is turned ON for 1s
            Timeout(
                name="initiation",
                on_enter=["enter_initiation"],
                on_exit=["exit_initiation"],
                timeout=self.session_info["init_length"],
                on_timeout=["start_vstim"],
            ),
            # vstim state: start vstim display (automatic once start, can move on to the next state)
            Timeout(
                name="vstim",
                on_enter=["enter_vstim"],
                on_exit=["exit_vstim"],
                timeout=self.session_info["lockout_length"],
                on_timeout=["start_reward"],
            ),
            # reward_available state: if there is a lick, deliver water then transition to the next state
            Timeout(
                name="reward_available",
                on_enter=["enter_reward_available"],
                on_exit=["exit_reward_available"],
                timeout=self.session_info["reward_available_length"],
                on_timeout=["start_vacuum_from_reward_available"],
            ),
            # lick_count state: licks are logged
            Timeout(
                name="lick_count",
                on_enter=["enter_lick_count"],
                on_exit=["exit_lick_count"],
                timeout=self.session_info["lick_count_length"],
                on_timeout=["start_vacuum_from_lick_count"],
            ),
            # vacuum state: open vacuum for specified amount of time (right before trial ends)
            Timeout(
                name="vacuum",
                on_enter=["enter_vacuum"],
                on_exit=["exit_vacuum"],
                timeout=self.session_info["vacuum_length"],
                on_timeout=["start_iti"],
            ),
            # iti state
            Timeout(
                name="iti",
                on_enter=["enter_iti"],
                on_exit=["exit_iti"],
                timeout=self.session_info["iti_length"],
                on_timeout=["return_to_standby"],
            ),
        ]
        # can set later with task.machine.states['cue'].timeout etc.

        ########################################################################
        # list of possible transitions between states
        # format is: [event_name, source_state, destination_state]
        ########################################################################
        self.transitions = [
            ["trial_start", "standby", "initiation"],
            ["start_vstim", "initiation", "vstim"],
            ["start_reward", "vstim", "reward_available"],
            ["start_lick_count", "reward_available", "lick_count"],
            ["start_vacuum_from_reward_available", "reward_available", "vacuum"],
            ["start_vacuum_from_lick_count", "lick_count", "vacuum"],
            ["start_iti", "vacuum", "iti"],
            ["return_to_standby", "iti", "standby"],
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
        self.box = behavbox_DT.BehavBox(self.session_info)
        self.pump = behavbox_DT.Pump()

    ########################################################################
    # functions called when state transitions occur
    ########################################################################
    def enter_standby(self):
        print("entering standby")
        self.trial_running = False

    def exit_standby(self):
        print("exiting standby")

    def enter_initiation(self):
        self.trial_running = True
        print("entering initiation")
        self.box.cueLED1.on()
        print("LED ON!")

    def exit_initiation(self):
        print("LED OFF!")
        self.box.cueLED1.off()

    def enter_vstim(self):
        print("displaying vstim")
        self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[0])

    def exit_vstim(self):
        print("transitioning to reward_available")

    def enter_reward_available(self):
        self.time_enter_reward_available = time.time()
        print("entering reward_available")

    def exit_reward_available(self):
        self.time_exit_reward_available = time.time()
        self.time_elapsed = self.time_exit_reward_available - self.time_enter_reward_available
        print("exiting reward_available")

    def enter_lick_count(self):
        print("entering lick_count")

    def exit_lick_count(self):
        print("exiting lick_count")

    def enter_vacuum(self):
        self.box.vacuum_on()
        print("entering vacuum")

    def exit_vacuum(self):
        self.box.vacuum_off()
        print("exiting vacuum")

    def enter_iti(self):
        print("entering ITI")

    def exit_iti(self):
        print("exiting ITI")

    ########################################################################
    # call the run() method repeatedly in a while loop in the run_ssrt_task_phase1_v1.py script
    # it will process all detected events from the behavior box (e.g.
    # licks, reward delivery, etc.) and trigger the appropriate state transitions
    ########################################################################
    def run(self):

        # read in name of an event the box has detected
        if self.box.event_list:
            event_name = self.box.event_list.popleft()
        else:
            event_name = ""

        if self.state == "standby":
            pass

        elif self.state == "initiation":
            pass

        elif self.state == "vstim":
            pass

        elif self.state == "reward_available":
            # Deliver reward from left pump if there is a lick detected on the left port
            if event_name == "left_IR_entry":
                self.pump.reward("left", self.session_info["reward_size"])
                print("delivering reward!!")
                self.start_lick_count()  # trigger state transition to lick_count
            else:
                pass

        elif self.state == "lick_count":
            self.machine.states['lick_count'].timeout = self.session_info["reward_available_length"] - self.time_elapsed

        elif self.state == "vacuum":
            pass

        elif self.state == "iti":
            pass

        # look for keystrokes
        self.box.check_keybd()

    # def plot_animation(self):
    #     w = 0
    #     start_time = time.time()
    #
    #     while w < 1:
    #         if self.box.event_list:
    #             event_plot = self.box.event_list.popleft()
    #         else:
    #             event_plot = ""
    #
    #         if event_plot == "left_IR_entry":
    #             time_elapsed_at_left_IR_entry = round(time.time() - start_time)
    #
    #         if event_plot == "left_IR_exit":
    #             time_elapsed_at_left_IR_exit = round(time.time() - start_time)
    #
    #
    #
    #         x1 = np.linspace(0, 10, 1000)
    #         y1 = np.zeros(1000)





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