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

            ###################################### states for phase 0 #############################################
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
            ),

            # ITI state
            Timeout(
                name="iti",
                on_enter=["enter_iti"],
                on_exit=["exit_iti"],
            ),
            ###################################### end of states for phase 0 ########################################
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
        self.time_at_reward = time.time() - self.trial_start_time

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

    def exit_vacuum(self):
        logging.info(str(time.time()) + ", exiting vacuum")

    def enter_iti(self):
        logging.info(str(time.time()) + ", entering iti")
        self.iti_time = round(random.uniform(self.session_info["iti_length"], (self.session_info["iti_length"] + 1)), 1)
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
            self.pump.reward("1", self.session_info["solenoid_blink_duration"], 0.01, 6)

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
            self.pump.reward("1", self.session_info["solenoid_blink_duration"], 0.01, 6)
            logging.info(str(time.time()) + ", reward delivered!")
            self.start_temp1()

        elif self.state == "temp1":
            # If there is lick detected, immediately transition to reward_collection state
            # Else transition to vacuum upon timeout of 10s (indicated in session_info)
            if event_name == "left_IR_entry":
                self.start_reward_collection()  # trigger state transition to reward_collection

        elif self.state == "reward_collection":
            pass

        elif self.state == "vacuum":
            self.pump.reward("vacuum", self.session_info["vacuum_duration"], 0.1, 1)
            logging.info(str(time.time()) + ", vacuum initiated!")
            self.start_iti()

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


#################################################################################
################################### Phase 1 #####################################
#################################################################################
class go_nogo_phase1(object):
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
        # stanby is the initial state, then trigger appropriate transitions depending on the type of trial
        # temp# are temporary states (used as a "place holder" for transitions to other states)
        # the go/nogo task has 2 possible types of trials
        # go trials: 45 degree drifting gratings presentation for 3s and reward is available after the 2nd second
        # normal ITI length of 3s
        # nogo trials: 135 degree drifting gratings presentation for 3s and no reward is available, if any lick is
        # detected after the 2nd second, it will consider it as False Alarm trial with longer ITI of 6.5s
        # all timeout lengths can be edited in the session_info file
        ########################################################################
        self.states = [
            State(name="standby", on_enter=["enter_standby"], on_exit=["exit_standby"]),

            ###################################### states for go trials #############################################
            # vstim_go state: initiate 45 degree drifting gratings stimulus for 3s, no need for timeout because we will
            # trigger state transition to the next state right after entering vstim_go state
            # after initiation, it will stay in this state for 2s (lockout period), then transition to reward_available
            # vstim drifting needs to be made in advance with visualstim.py code and saved to home folder of the RPi4
            # then select the vstim to display in the method enter_vstim_go
            Timeout(
                name="vstim_go",
                on_enter=["enter_vstim_go"],
                on_exit=["exit_vstim_go"],
                timeout=self.session_info["lockout_length"],
                on_timeout=["start_reward_available"],
            ),

            # reward_available state: if there is a lick, deliver reward then transition to temp1 state
            # if no lick is detected, transition to vacuum state after 1.5s
            Timeout(
                name="reward_available",
                on_enter=["enter_reward_available"],
                on_exit=["exit_reward_available"],
            ),

            # temp1 state: temporary state to wait until vstim ends then transition to vacuum state
            # no timeout because transition will be made when vstim 3s countdown is up!
            Timeout(
                name="temp1",
                on_enter=["enter_temp1"],
                on_exit=["exit_temp1"],
            ),

            # vacuum state: open vacuum for specified amount of time, then transition to assessment state
            Timeout(
                name="vacuum",
                on_enter=["enter_vacuum"],
                on_exit=["exit_vacuum"],
            ),

            # assessment state: assess trial outcomes to trigger appropriate ITI transition
            # go trials always have normal ITI
            Timeout(
                name="assessment",
                on_enter=["enter_assessment"],
                on_exit=["exit_assessment"],
            ),

            # normal iti state
            Timeout(
                name="normal_iti",
                on_enter=["enter_normal_iti"],
                on_exit=["exit_normal_iti"],
                timeout=self.session_info["normal_iti_length"],
                on_timeout=["start_extra_iti_normal"],
            ),
            ###################################### end of states for go trials ########################################
            ###########################################################################################################


            ###################################### states for nogo trials #############################################
            # same as go trial states
            # exceptions: different vstim, no reward_available state, punishment_iti

            # vstim_nogo state: does not transition to reward_available state, instead to lick_count
            Timeout(
                name="vstim_nogo",
                on_enter=["enter_vstim_nogo"],
                on_exit=["exit_vstim_nogo"],
                timeout=self.session_info["lockout_length"],
                on_timeout=["start_lick_count"],
            ),

            # lick_count state: if there is lick, transition to temp2 state
            # otherwise will transition to vacuum state after 2s
            Timeout(
                name="lick_count",
                on_enter=["enter_lick_count"],
                on_exit=["exit_lick_count"],
            ),

            # temp2 state: temporary state to wait until vstim ends and transition to vacuum state
            Timeout(
                name="temp2",
                on_enter=["enter_temp2"],
                on_exit=["exit_temp2"],
            ),

            # punishment iti state: only when trial outcome is False Alarm!
            Timeout(
                name="punishment_iti",
                on_enter=["enter_punishment_iti"],
                on_exit=["exit_punishment_iti"],
                timeout=self.session_info["punishment_iti_length"],
                on_timeout=["start_extra_iti_punishment"],
            ),

            # extra iti state: account for variable iti duration
            Timeout(
                name="extra_iti",
                on_enter=["enter_extra_iti"],
                on_exit=["exit_extra_iti"],
            ),
            ###################################### end of states for nogo trials ######################################
            ###########################################################################################################
        ]

        ########################################################################
        # list of possible transitions between states
        # format is: [event_name, source_state, destination_state]
        ########################################################################
        self.transitions = [
            # transitions for go trials
            # to trigger this transition pathway, put 'go_trial_start' in the run_go_nogo code
            ["go_trial_start", "standby", "vstim_go"],
            ["start_reward_available", "vstim_go", "reward_available"],
            ["start_vacuum_reward_available", "reward_available", "vacuum"],
            ["start_temp1", "reward_available", "temp1"],
            ["start_vacuum_temp1", "temp1", "vacuum"],
            ["start_assessment", "vacuum", "assessment"],
            ["start_normal_iti", "assessment", "normal_iti"],
            ["start_extra_iti_normal", "normal_iti", "extra_iti"],

            # transitions for nogo trials
            # to trigger this transition pathway, put 'nogo_trial_start' in the run_go_nogo code
            # transitions that are already in go pathway will not be repeated here
            ["nogo_trial_start", "standby", "vstim_nogo"],
            ["start_lick_count", "vstim_nogo", "lick_count"],
            ["start_vacuum_lick_count", "lick_count", "vacuum"],
            ["start_temp2", "lick_count", "temp2"],
            ["start_vacuum_temp2", "temp2", "vacuum"],
            ["start_punishment_iti", "assessment", "punishment_iti"],
            ["start_extra_iti_punishment", "punishment_iti", "extra_iti"],
            ["return_to_standby", "extra_iti", "standby"],
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
        self.normal_iti_length = self.session_info["normal_iti_length"]  # in seconds
        self.punishment_iti_length = self.session_info["punishment_iti_length"]  # in seconds

        # initialize behavior box
        self.box = behavbox_DT.BehavBox(self.session_info)

        # pump class is for reward delivery
        self.pump = self.box.pump

        # initialize treadmill
        self.treadmill = self.box.treadmill

        # establish parameters for plotting
        self.trial_start_time = 0
        self.time_at_vstim_ON = 0
        self.time_at_vstim_OFF = 0
        self.lick_times = np.array([])
        self.time_at_reward = -1  # default value of -1 if no reward is delivered
        # default of trial_outcome is 0
        # 1 = Hit!; 2 = Miss!!; 3 = CR!; 4 = FA!!!
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

    def enter_vstim_go(self):
        self.trial_running = True
        self.trial_type = "go"
        logging.info(str(time.time()) + ", initializing vstim_go")
        self.box.visualstim_go.show_grating(list(self.box.visualstim_go.gratings)[0])
        logging.info(str(time.time()) + ", vstim_go ON!")
        self.time_at_vstim_ON = time.time() - self.trial_start_time

    def exit_vstim_go(self):
        logging.info(str(time.time()) + ", exiting lockout period")

    def enter_vstim_nogo(self):
        self.trial_running = True
        self.trial_type = "no_go"
        logging.info(str(time.time()) + ", initializing vstim_nogo")
        self.box.visualstim_nogo.show_grating(list(self.box.visualstim_nogo.gratings)[0])
        logging.info(str(time.time()) + ", vstim_nogo ON!")
        self.time_at_vstim_ON = time.time() - self.trial_start_time

    def exit_vstim_nogo(self):
        logging.info(str(time.time()) + ", exiting lockout period")

    def enter_reward_available(self):
        logging.info(str(time.time()) + ", entering reward_available")
        self.trial_outcome = 2  # Miss!!
        self.countdown(2)

    def exit_reward_available(self):
        logging.info(str(time.time()) + ", exiting reward_available")

    def enter_lick_count(self):
        logging.info(str(time.time()) + ", entering lick_count")
        self.trial_outcome = 3  # CR!
        self.countdown(2)

    def exit_lick_count(self):
        logging.info(str(time.time()) + ", exiting lick_count")

    def enter_temp1(self):
        logging.info(str(time.time()) + ", entering temp1")
        # entering temp1 means reward was delivered immediately before the transition
        # self.trial_outcome = 1  # Hit!
        # logging.info(str(time.time()) + ", Hit!")

    def exit_temp1(self):
        logging.info(str(time.time()) + ", exiting temp1")

    def enter_temp2(self):
        logging.info(str(time.time()) + ", entering temp2")
        self.trial_outcome = 4  # FA!!!
        logging.info(str(time.time()) + ", FA!!!")

    def exit_temp2(self):
        logging.info(str(time.time()) + ", exiting temp2")

    def enter_vacuum(self):
        logging.info(str(time.time()) + ", entering vacuum")

    def exit_vacuum(self):
        logging.info(str(time.time()) + ", exiting vacuum")

    def enter_assessment(self):
        logging.info(str(time.time()) + ", entering assessment")

    def exit_assessment(self):
        logging.info(str(time.time()) + ", exiting assessment")

    def enter_normal_iti(self):
        logging.info(str(time.time()) + ", entering normal_iti")

    def exit_normal_iti(self):
        logging.info(str(time.time()) + ", exiting normal_iti")

    def enter_punishment_iti(self):
        logging.info(str(time.time()) + ", entering punishment_iti")

    def exit_punishment_iti(self):
        logging.info(str(time.time()) + ", exiting punishment_iti")

    def enter_extra_iti(self):
        logging.info(str(time.time()) + ", entering extra_iti")
        self.adding_iti_time = round(random.uniform(0, 1), 1)
        logging.info(str(time.time()) + ", " + str(self.adding_iti_time) + " added to iti length")
        self.countdown_iti(self.adding_iti_time)

    def exit_extra_iti(self):
        logging.info(str(time.time()) + ", exiting extra_iti")

    def bait_phase1(self):
        # This function asks the user to input whether they want reward delivery
        # This is used to bait the animal to lick initially
        # If y, deliver reward, if hit enter, start random reward phase
        self.deliver_reward = input("Deliver reward, else start allgo? (y or hit enter): \n")
        if self.deliver_reward == "y":
            self.pump.reward("1", self.session_info["solenoid_blink_duration"], 0.01, 6)

    ########################################################################
    # countdown methods to run when vstim starts to play, used as timers since vstim starts
    # t is the length of countdown (in seconds)
    ########################################################################
    def countdown(self, t):
        # This counts down the length of reward_available or lick_count duration (1s)
        logging.info(str(time.time()) + ", countdown starts")
        while t > 0:
            # mins, secs = divmod(t, 60)
            # timer = '{:02d}:{:02d}'.format(mins, secs)
            # print(timer, end="\r")
            time.sleep(0.5)
            t -= 0.5
        logging.info(str(time.time()) + ", countdown ends")
        self.box.event_list.append("countdown ends")

    def countdown_iti(self, t_iti):
        # This counts down iti of variable lengths
        logging.info(str(time.time()) + ", extra_iti countdown starts")
        while t_iti > 0:
            # mins, secs = divmod(t_iti, 60)
            # timer = '{:02d}:{:02d}'.format(mins, secs)
            # print(timer, end="\r")
            time.sleep(0.1)
            t_iti -= 0.1
        logging.info(str(time.time()) + ", extra_iti countdown ends")
        self.box.event_list.append("extra_iti countdown ends")

    ########################################################################
    # call the run_go() or run_nogo() method repeatedly in a while loop in the run_go_nogo script
    # it will process all detected events from the behavior box (e.g.
    # licks, reward delivery, etc.) and trigger the appropriate state transitions
    ########################################################################
    def run_go(self):

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

        elif self.state == "vstim_go":
            pass

        elif self.state == "reward_available":
            # this task only uses 1 port (left port) and 1 pump (left pump)
            # deliver reward from left pump if there is a lick detected on the left IR port
            # if lick is detected, delivery reward then transition to temp1 immediately
            # otherwise transition to vacuum after 1s
            self.pump.reward("1", self.session_info["solenoid_blink_duration"], 0.01, 6)
            logging.info(str(time.time()) + ", reward delivered!")
            self.time_at_reward = time.time() - self.trial_start_time
            self.start_temp1()  # trigger state transition to temp1

        elif self.state == "temp1":
            if event_name == "left_IR_entry":
                self.trial_outcome = 1  # Hit!
            # transition to vacuum state when vstim 3s countdown ends
            elif event_name == "countdown ends":
                self.time_at_vstim_OFF = time.time() - self.trial_start_time
                self.start_vacuum_temp1()

        elif self.state == "vacuum":
            self.pump.reward("vacuum", self.session_info["vacuum_duration"], 0.1, 1)
            logging.info(str(time.time()) + ", vacuum initiated!")
            self.start_assessment()

        elif self.state == "assessment":
            self.start_normal_iti()

        elif self.state == "normal_iti":
            pass

        elif self.state == "extra_iti":
            if event_name == "extra_iti countdown ends":
                self.return_to_standby()

    def run_nogo(self):

        # read in name of an event the box has detected
        if self.box.event_list:
            event_name = self.box.event_list.popleft()
        else:
            event_name = ""

        if event_name == "left_IR_entry":
            self.lick_times = np.append(self.lick_times, time.time() - self.trial_start_time)

        if self.state == "standby":
            pass

        elif self.state == "vstim_nogo":
            pass

        elif self.state == "lick_count":
            # if lick is detected, transition to temp2
            # otherwise, transition to vacuum after 2s
            if event_name == "left_IR_entry":
                self.start_temp2()
            elif event_name == "countdown ends":
                self.start_vacuum_lick_count()  # trigger transition to vacuum state

        elif self.state == "temp2":
            if event_name == "countdown ends":
                self.time_at_vstim_OFF = time.time() - self.trial_start_time
                self.start_vacuum_temp2()

        elif self.state == "vacuum":
            logging.info(str(time.time()) + ", no vacuum!")
            self.start_assessment()

        elif self.state == "assessment":
            # if trial_outcome is CR!, transition to normal_iti
            # else transition to punishment_iti
            if self.trial_outcome == 3:
                self.start_normal_iti()
            elif self.trial_outcome == 4:
                self.start_punishment_iti()

        elif self.state == "normal_iti":
            pass

        elif self.state == "punishment_iti":
            pass

        elif self.state == "extra_iti":
            if event_name == "extra_iti countdown ends":
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
        self.box.visualstim_go.myscreen.close()