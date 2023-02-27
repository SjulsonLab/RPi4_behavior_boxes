##########################################################################################################
########################################## GO/NO-GO TASK #################################################
##########################################################################################################

# import packages for the task
import random

from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
from icecream import ic
import logging
import os
from colorama import Fore, Style
import logging.config
import time
import numpy as np

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

#################################################################################
################################### Phase 0 #####################################
#################################################################################
class go_nogo_phase0(object):
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
        # Write details of the task here!
        ########################################################################
        self.states = [
            State(name="standby", on_enter=["enter_standby"], on_exit=["exit_standby"]),

            ###################################### states for go trials #############################################
            # Reward is delivered immediately after entering this state
            # Then immediately transition to temp1
            Timeout(
                name="reward_available",
                on_enter=["enter_reward_available"],
                on_exit=["exit_reward_available"],
            ),

            # temp1 state: if the animal licks, transition to reward_collection state
            # else wait 10s and transition to vacuum state
            Timeout(
                name="temp1",
                on_enter=["enter_temp1"],
                on_exit=["exit_temp1"],
                timeout=self.session_info["RR_temp1_length"],
                on_timeout=["start_vacuum_from_temp1"],
            ),

            # reward_collection state: timeout of 2s for animal to collect reward
            # then transition to vacuum
            Timeout(
                name="reward_collection",
                on_enter=["enter_reward_collection"],
                on_exit=["exit_reward_collection"],
                timeout=self.session_info["RR_reward_collection_length"],
                on_timeout=["start_vacuum_from_reward_collection"],
            ),

            # vacuum state: open vacuum for specified amount of time, then transition to assessment state
            Timeout(
                name="vacuum",
                on_enter=["enter_vacuum"],
                on_exit=["exit_vacuum"],
                timeout=self.session_info["vacuum_length"],
                on_timeout=["start_iti"],
            ),

            # ITI state
            Timeout(
                name="iti",
                on_enter=["enter_iti"],
                on_exit=["exit_iti"],
            ),
            ###################################### end of states for go trials ########################################
            ###########################################################################################################
        ]

        ########################################################################
        # list of possible transitions between states
        # format is: [event_name, source_state, destination_state]
        ########################################################################
        self.transitions = [
            # transitions
            ["start_random_reward", "standby", "reward_available"],
            ["start_temp1", "reward_available", "temp1"],
            ["start_vacuum_from_temp1", "temp1", "vacuum"],
            ["start_reward_collection", "temp1", "reward_collection"],
            ["start_vacuum_from_reward_collection", "reward_collection", "vacuum"],
            ["start_iti", "vacuum", "iti"],
            ["return_to_standby", "iti", "standby"],
        ]

        ########################################################################
        # initialize state machine, behavbox, and parameters for plotting
        ########################################################################
        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial="standby",
        )

        # default is task not running
        self.trial_running = False

        # initialize behavior box
        self.box = behavbox_DT.BehavBox(self.session_info)

        # pump class is for reward delivery
        self.pump = self.box.pump

        # initialize treadmill
        self.treadmill = self.box.treadmill

        # establish parameters for plotting
        self.trial_start_time = 0
        self.lick_times = np.array([])
        self.time_at_reward = -1  # default value of -1 if no reward is delivered
        # default of trial_outcome is 0
        # 1 = Hit!; 2 = Miss!!
        self.trial_outcome = 0

    ########################################################################
    # functions called when state transitions occur
    ########################################################################
    def enter_standby(self):
        logging.info(str(time.time()) + ", entering standby")
        self.trial_running = False

    def exit_standby(self):
        logging.info(str(time.time()) + ", exiting standby")
        # set all plotting parameters to default values
        self.trial_start_time = time.time()
        self.lick_times = np.array([])
        self.time_at_reward = -1

    def enter_reward_available(self):
        self.trial_running = True
        logging.info(str(time.time()) + ", entering reward_available")
        self.trial_outcome = 2  # Miss!!

    def exit_reward_available(self):
        logging.info(str(time.time()) + ", exiting reward_available")

    def enter_temp1(self):
        logging.info(str(time.time()) + ", entering temp1")

    def exit_temp1(self):
        logging.info(str(time.time()) + ", exiting temp1")

    def enter_reward_collection(self):
        logging.info(str(time.time()) + ", entering reward_collection")
        self.trial_outcome = 1  # Hit!
        logging.info(str(time.time()) + ", Hit!")

    def exit_reward_collection(self):
        logging.info(str(time.time()) + ", exiting reward_collection")

    def enter_vacuum(self):
        logging.info(str(time.time()) + ", entering vacuum")
        self.pump.pump_vacuum.on()
        logging.info(str(time.time()) + ", vacuum ON!")

    def exit_vacuum(self):
        logging.info(str(time.time()) + ", exiting vacuum")
        self.pump.pump_vacuum.off()
        logging.info(str(time.time()) + ", vacuum OFF!")

    def enter_iti(self):
        logging.info(str(time.time()) + ", entering iti")
        self.iti_time = round(random.uniform(3, 4), 1)
        logging.info(str(time.time()) + ", " + str(self.iti_time) + "s iti length")
        self.countdown_iti(self.iti_time)

    def exit_iti(self):
        logging.info(str(time.time()) + ", exiting iti")

    def bait_phase0(self):
        # This function asks the user to input whether they want reward delivery
        # This is used to bait the animal to lick initially
        # If y, deliver reward, if hit enter, start random reward phase
        self.deliver_reward = input("Deliver reward, else Start random_reward? (y or hit enter): \n")
        if self.deliver_reward == "y":
            self.pump.reward("1", self.session_info["reward_size"])

    ########################################################################
    # countdown method to generate variable ITI length
    ########################################################################
    def countdown_iti(self, t_iti):
        # This counts down iti of variable lengths
        logging.info(str(time.time()) + ", ITI countdown starts...")
        while t_iti > 0:
            # mins, secs = divmod(t_iti, 60)
            # timer = '{:02d}:{:02d}'.format(mins, secs)
            # print(timer, end="\r")
            time.sleep(0.1)
            t_iti -= 0.1
        logging.info(str(time.time()) + ", ITI countdown ends...")
        self.box.event_list.append("ITI countdown ends...")

    ########################################################################
    # Call the run_random_reward() method repeatedly in a while loop in a separate script
    ########################################################################
    def run_random_reward(self):

        # read in name of an event the box has detected
        if self.box.event_list:
            event_name = self.box.event_list.popleft()
        else:
            event_name = ""

        if event_name == "left_IR_entry":
            self.lick_times = np.append(self.lick_times, time.time() - self.trial_start_time)

        # in standby state, get the shared memory variables of the task to be used by the plot function
        # in a separate process
        if self.state == "standby":
            pass

        elif self.state == "reward_available":
            # this task only uses 1 IR port (left port) and 1 selenoid valve (pump1)
            # Immediately deliver reward from pump1 when entering this state
            # Then transition to temp1 state
            self.pump.reward("1", self.session_info["RR_reward_size"])
            logging.info(str(time.time()) + ", reward delivered!")
            self.time_at_reward = time.time() - self.trial_start_time
            self.start_temp1()  # trigger state transition to temp1

        elif self.state == "temp1":
            # If there is lick detected, immediately transition to reward_collection state
            # Else transition to vacuum upon timeout of 10s (indicated in session_info)
            if event_name == "left_IR_entry":
                self.start_reward_collection()  # trigger state transition to reward_collection

        elif self.state == "reward_collection":
            pass

        elif self.state == "vacuum":
            pass

        elif self.state == "iti":
            if event_name == "ITI countdown ends...":
                self.return_to_standby()

    ########################################################################
    # methods to start and end the behavioral session
    ########################################################################
    def start_session(self):
        ic("TODO: start video")
        self.box.video_start()

    def end_session(self):
        ic("TODO: stop video")
        self.box.video_stop()