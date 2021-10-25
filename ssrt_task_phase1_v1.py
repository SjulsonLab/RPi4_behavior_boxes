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
            from fake_session_info import fake_session_info

            self.session_info = fake_session_info
        else:
            self.session_info = kwargs.get("session_info", None)
        ic(self.session_info)

        ########################################################################
        # Task has four possible states: standby, initiation, stim, iti
        ########################################################################
        self.states = [
            State(name="standby", on_enter=["enter_standby"], on_exit=["exit_standby"]),
            Timeout(
                name="initiation",
                on_enter=["enter_initiation"],
                on_exit=["exit_initiation"],
                init_end=self.session_info["init_length"],
                on_init_end=["abort_init"],
            ),
            Timeout(
                name="vstim",
                on_enter=["enter_stim"],
                on_exit=["exit_stim"],
                vstim_end=self.session_info["cue_length"],
                on_vstim_end=["abort_vstim"],
            ),
            Timeout(
                name="iti",
                on_enter=["enter_iti"],
                on_exit=["exit_iti"],
                iti_end=self.session_info["iti_length"],
                on_iti_end=["abort_iti"],
            ),
        ]
        # can set later with task.machine.states['cue'].timeout etc.

        ########################################################################
        # list of possible transitions between states
        # format is: [event_name, source_state, destination_state]
        ########################################################################
        self.transitions = [
            ["trial_start", "standby", "initiation"],
            ["abort_init", "initiation", "vstim"],
            ["abort_vstim", "vstim", "iti"],
            ["abort_iti", "iti", "standby"],
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

    ########################################################################
    # functions called when state transitions occur
    ########################################################################
    def enter_standby(self):
        print("entering standby")
        self.trial_running = False

    def exit_standby(self):
        pass

    def enter_initiation(self):
        print("entering initiation")
        print("port LED ON!")
        self.box.cueLED1.on()
        self.trial_running = True

    def exit_initiation(self):
        print("port LED OFF!")
        self.box.cueLED1.off()

    def enter_vstim(self):
        print("display GO vstim")
        self.box.visualstim.show_grating("first_grating.grat")

    def exit_vstim(self):
        print("abort GO vstim")

    def enter_iti(self):
        print("entering ITI")
        pass

    def exit_iti(self):
        print("exiting ITI")
        pass

    ########################################################################
    # call the run() method repeatedly in a while loop in the run_SSRT_task_phase1_v1.py script
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