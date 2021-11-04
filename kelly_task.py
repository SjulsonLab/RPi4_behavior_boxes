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


class KellyTask(object):
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
        ########################################################################
        self.states = [
            State(name="standby", on_enter=["enter_standby"], on_exit=["exit_standby"]),
            Timeout(
                name="reward_available",
                on_enter=["enter_reward_available"],
                on_exit=["exit_reward_available"],
            ),
            Timeout(
                name="cue",
                on_enter=["enter_cue"],
                on_exit=["exit_cue"],
                timeout=self.session_info["timeout_length"],
                on_timeout=["timeup"],
            ),
        ]
        # can set later with task.machine.states['cue'].timeout etc.

        ########################################################################
        # list of possible transitions between states
        # format is: [event_name, source_state, destination_state]
        ########################################################################
        self.transitions = [
            ["trial_start", "standby", "reward_available"],
            ["active_poke", "reward_available", "cue"],
            ["timeup", "cue", "standby"],
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

    def enter_reward_available(self):
        print("entering reward_available")
        print("start white noise")
        self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[0])
        self.trial_running = True

    def exit_reward_available(self):
        print("stop white noise")

    def enter_cue(self):
        print("deliver reward")
        self.pump.reward("left", self.session_info["reward_size"])
        print("start cue")
        self.box.cueLED1.on()


    def exit_cue(self):
        print("stop cue")
        self.box.cueLED1.off()

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
                self.box.sound1.blink(0.5,0.1,1)
                self.active_poke()  # triggers state transition

        elif self.state == "cue":
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