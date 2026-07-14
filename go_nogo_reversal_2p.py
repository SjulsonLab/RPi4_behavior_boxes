##########################################################################################################
################################### GO/NO-GO TASK REVERSAL ################################################
# Edited 6/22/2025
# Duy Tran
# Renamed compatibility copy for 2P workflow.
# This is the same structure as the go_nogo_reversal.py code but imports the renamed
# behavior-box module so it works with behavbox_DT_2p.py.
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

import behavbox_DT_2p as behavbox_DT

# adding timing capability to the state machine
@add_state_features(Timeout)
class TimedStateMachine(Machine):
    pass

#################################################################################
################################### Reversal #####################################
#################################################################################
class go_nogo_reversal(object):
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
        # go trials: reversed identity relative to first-rule task
        # nogo trials: reversed identity relative to first-rule task
        # all timeout lengths can be edited in the session_info file
        ########################################################################
        self.states = [
            State(name="standby", on_enter=["enter_standby"], on_exit=["exit_standby"]),

            ###################################### states for go trials #############################################
            Timeout(
                name="vstim_go",
                on_enter=["enter_vstim_go"],
                on_exit=["exit_vstim_go"],
                timeout=self.session_info["lockout_length"],
                on_timeout=["start_reward_available"],
            ),
            Timeout(
                name="reward_available",
                on_enter=["enter_reward_available"],
                on_exit=["exit_reward_available"],
            ),
            Timeout(
                name="temp1",
                on_enter=["enter_temp1"],
                on_exit=["exit_temp1"],
            ),
            Timeout(
                name="reward_lockout",
                on_enter=["enter_reward_lockout"],
                on_exit=["exit_reward_lockout"],
                timeout=0.2,
                on_timeout=["start_vacuum_reward_lockout"],
            ),
            Timeout(
                name="vacuum",
                on_enter=["enter_vacuum"],
                on_exit=["exit_vacuum"],
            ),
            Timeout(
                name="assessment",
                on_enter=["enter_assessment"],
                on_exit=["exit_assessment"],
            ),
            Timeout(
                name="normal_iti",
                on_enter=["enter_normal_iti"],
                on_exit=["exit_normal_iti"],
                timeout=self.session_info["normal_iti_length"],
                on_timeout=["start_extra_iti_normal"],
            ),
            ###################################### end of states for go trials ########################################

            ###################################### states for nogo trials #############################################
            Timeout(
                name="vstim_nogo",
                on_enter=["enter_vstim_nogo"],
                on_exit=["exit_vstim_nogo"],
                timeout=self.session_info["lockout_length"],
                on_timeout=["start_lick_count"],
            ),
            Timeout(
                name="lick_count",
                on_enter=["enter_lick_count"],
                on_exit=["exit_lick_count"],
            ),
            Timeout(
                name="temp2",
                on_enter=["enter_temp2"],
                on_exit=["exit_temp2"],
            ),
            Timeout(
                name="punishment_iti",
                on_enter=["enter_punishment_iti"],
                on_exit=["exit_punishment_iti"],
                timeout=self.session_info["punishment_iti_length"],
                on_timeout=["start_extra_iti_punishment"],
            ),
            Timeout(
                name="extra_iti",
                on_enter=["enter_extra_iti"],
                on_exit=["exit_extra_iti"],
            ),
            ###################################### end of states for nogo trials ######################################
        ]

        ########################################################################
        # list of possible transitions between states
        ########################################################################
        self.transitions = [
            ["go_trial_start", "standby", "vstim_go"],
            ["start_reward_available", "vstim_go", "reward_available"],
            ["start_reward_lockout_reward_available", "reward_available", "reward_lockout"],
            ["start_temp1", "reward_available", "temp1"],
            ["start_reward_lockout_temp1", "temp1", "reward_lockout"],
            ["start_vacuum_reward_lockout", "reward_lockout", "vacuum"],
            ["start_assessment", "vacuum", "assessment"],
            ["start_normal_iti", "assessment", "normal_iti"],
            ["start_extra_iti_normal", "normal_iti", "extra_iti"],
            ["nogo_trial_start", "standby", "vstim_nogo"],
            ["start_lick_count", "vstim_nogo", "lick_count"],
            ["start_vacuum_lick_count", "lick_count", "vacuum"],
            ["start_temp2", "lick_count", "temp2"],
            ["start_vacuum_temp2", "temp2", "vacuum"],
            ["start_punishment_iti", "assessment", "punishment_iti"],
            ["start_extra_iti_punishment", "punishment_iti", "extra_iti"],
            ["return_to_standby", "extra_iti", "standby"],
        ]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial="standby",
        )

        self.trial_running = False
        self.normal_iti_length = self.session_info["normal_iti_length"]
        self.punishment_iti_length = self.session_info["punishment_iti_length"]

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
        self.time_at_reward = -1
        self.trial_outcome = 0

    ########################################################################
    # functions called when state transitions occur
    ########################################################################
    def enter_standby(self):
        logging.info(str(time.time()) + ", entering standby")
        self.trial_running = False

    def exit_standby(self):
        logging.info(str(time.time()) + ", exiting standby")
        self.trial_start_time = time.time()
        self.lick_times = np.array([])
        self.time_at_reward = -1
        self.trial_outcome = 0

    def enter_vstim_go(self):
        self.trial_running = True
        self.trial_type = "go"
        logging.info(str(time.time()) + ", initializing vstim_go")
        self.box.visualstim_nogo.show_grating(list(self.box.visualstim_nogo.gratings)[0])
        logging.info(str(time.time()) + ", vstim_nogo ON!")
        self.time_at_vstim_ON = time.time() - self.trial_start_time
        self.box.sound2.on()
        logging.info(str(time.time()) + ", sound_nogo ON!")

    def exit_vstim_go(self):
        logging.info(str(time.time()) + ", exiting lockout period")

    def enter_vstim_nogo(self):
        self.trial_running = True
        self.trial_type = "no_go"
        logging.info(str(time.time()) + ", initializing vstim_nogo")
        self.box.visualstim_go.show_grating(list(self.box.visualstim_go.gratings)[0])
        logging.info(str(time.time()) + ", vstim_go ON!")
        self.time_at_vstim_ON = time.time() - self.trial_start_time
        self.box.sound1.on()
        logging.info(str(time.time()) + ", sound_go ON!")

    def exit_vstim_nogo(self):
        logging.info(str(time.time()) + ", exiting lockout period")

    def enter_reward_available(self):
        logging.info(str(time.time()) + ", entering reward_available")
        self.countdown_trial(1.8)

    def exit_reward_available(self):
        logging.info(str(time.time()) + ", exiting reward_available")

    def enter_lick_count(self):
        logging.info(str(time.time()) + ", entering lick_count")
        self.trial_outcome = 3
        self.countdown_trial(2)

    def exit_lick_count(self):
        logging.info(str(time.time()) + ", exiting lick_count")

    def enter_temp1(self):
        logging.info(str(time.time()) + ", entering temp1")

    def exit_temp1(self):
        logging.info(str(time.time()) + ", exiting temp1")

    def enter_temp2(self):
        logging.info(str(time.time()) + ", entering temp2")
        self.trial_outcome = 4
        logging.info(str(time.time()) + ", FA!!!")

    def exit_temp2(self):
        logging.info(str(time.time()) + ", exiting temp2")

    def enter_reward_lockout(self):
        logging.info(str(time.time()) + ", entering reward_lockout")
        self.pump.reward("vacuum", self.session_info["vacuum_duration"], 0.1, 1)
        logging.info(str(time.time()) + ", vacuum initiated!")

    def exit_reward_lockout(self):
        logging.info(str(time.time()) + ", exiting reward_lockout")

    def enter_vacuum(self):
        logging.info(str(time.time()) + ", entering vacuum")

    def exit_vacuum(self):
        logging.info(str(time.time()) + ", exiting vacuum")

    def enter_assessment(self):
        logging.info(str(time.time()) + ", entering assessment")
        logging.info(str(time.time()) + "," + str(self.trial_outcome))

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

    def bait_reversal(self):
        self.deliver_reward = input("Hit enter to deliver reward, or hit y then enter to start allgo: \n")
        if self.deliver_reward == "":
            self.pump.reward("1", self.session_info["solenoid_blink_duration"], 0.01, 6)

    ########################################################################
    # countdown methods to run when vstim starts to play, used as timers since vstim starts
    ########################################################################
    def countdown_trial(self, t):
        logging.info(str(time.time()) + ", countdown starts")
        while t > 0:
            time.sleep(0.1)
            t -= 0.1
        logging.info(str(time.time()) + ", trial countdown ends")
        self.box.event_list.append("trial countdown ends")

    def countdown_iti(self, t_iti):
        logging.info(str(time.time()) + ", extra_iti countdown starts")
        while t_iti > 0:
            time.sleep(0.1)
            t_iti -= 0.1
        logging.info(str(time.time()) + ", extra_iti countdown ends")
        self.box.event_list.append("extra_iti countdown ends")

    ########################################################################
    # main trial-running methods
    ########################################################################
    def run_go(self):
        if self.box.event_list:
            event_name = self.box.event_list.popleft()
        else:
            event_name = ""

        if event_name == "left_entry":
            lick_time = time.time() - self.trial_start_time
            self.lick_times = np.append(self.lick_times, lick_time)
            logging.info(
                str(time.time())
                + ", left_entry, trial_elapsed, "
                + "{:.3f}".format(lick_time)
                + " s, state, "
                + str(self.state)
                + ", trial_type, go"
            )

        if self.state == "standby":
            pass
        elif self.state == "vstim_go":
            pass
        elif self.state == "reward_available":
            if event_name == "left_entry":
                self.trial_outcome = 1
                self.pump.reward("1", self.session_info["solenoid_blink_duration"], 0.01, 6)
                logging.info(str(time.time()) + ", reward delivered!")
                self.time_at_reward = time.time() - self.trial_start_time
                self.start_temp1()
            elif event_name == "trial countdown ends":
                self.time_at_vstim_OFF = time.time() - self.trial_start_time + 0.2
                self.start_reward_lockout_reward_available()
        elif self.state == "temp1":
            if event_name == "trial countdown ends":
                self.time_at_vstim_OFF = time.time() - self.trial_start_time + 0.2
                self.start_reward_lockout_temp1()
        elif self.state == "reward_lockout":
            pass
        elif self.state == "vacuum":
            self.box.sound2.off()
            logging.info(str(time.time()) + ", sound_go OFF!")
            self.start_assessment()
        elif self.state == "assessment":
            if self.time_at_reward == -1:
                self.trial_outcome = 2
                logging.info(str(time.time()) + ", Miss! in assessment")
                self.start_normal_iti()
            else:
                self.start_normal_iti()
        elif self.state == "normal_iti":
            pass
        elif self.state == "extra_iti":
            if event_name == "extra_iti countdown ends":
                self.return_to_standby()

    def run_nogo(self):
        if self.box.event_list:
            event_name = self.box.event_list.popleft()
        else:
            event_name = ""

        if event_name == "left_entry":
            lick_time = time.time() - self.trial_start_time
            self.lick_times = np.append(self.lick_times, lick_time)
            logging.info(
                str(time.time())
                + ", left_entry, trial_elapsed, "
                + "{:.3f}".format(lick_time)
                + " s, state, "
                + str(self.state)
                + ", trial_type, nogo"
            )

        if self.state == "standby":
            pass
        elif self.state == "vstim_nogo":
            pass
        elif self.state == "lick_count":
            if event_name == "left_entry":
                self.start_temp2()
            elif event_name == "trial countdown ends":
                self.start_vacuum_lick_count()
        elif self.state == "temp2":
            if event_name == "trial countdown ends":
                self.time_at_vstim_OFF = time.time() - self.trial_start_time
                self.start_vacuum_temp2()
        elif self.state == "vacuum":
            self.box.sound1.off()
            logging.info(str(time.time()) + ", sound_nogo OFF!")
            logging.info(str(time.time()) + ", no vacuum!")
            self.start_assessment()
        elif self.state == "assessment":
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

    def calibrate(self):
        for iteration in range(100):
            self.pump.reward("1", self.session_info["solenoid_blink_duration"], 0.01, 6)
            time.sleep(0.5)

    ########################################################################
    # methods to start and end the behavioral session
    ########################################################################
    def _call_shutdown_method(self, object_label, target_object, method_name):
        """
        Safely call a zero-argument shutdown method during normal or emergency cleanup.

        Parameters
        ----------
        object_label : str
            Human-readable name for the object being shut down. Used only for logging.
        target_object : object or None
            Object that may expose the requested shutdown method. No shape or unit conventions apply.
        method_name : str
            Name of the zero-argument method to call on target_object.

        Returns
        -------
        bool
            True if the method existed and completed without raising an exception; False otherwise.
        """
        if target_object is None:
            return False

        shutdown_method = getattr(target_object, method_name, None)
        if not callable(shutdown_method):
            return False

        try:
            shutdown_method()
            logging.info(str(time.time()) + ", shutdown called: " + object_label + "." + method_name + "()")
            return True
        except Exception as shutdown_error:
            logging.warning(
                str(time.time())
                + ", shutdown failed: "
                + object_label
                + "."
                + method_name
                + "(): "
                + repr(shutdown_error)
            )
            return False

    def _close_visualstim(self, object_label, visualstim_object):
        """
        Safely close a visual stimulus object and its display screen.

        Parameters
        ----------
        object_label : str
            Human-readable name for the visual stimulus object. Used only for logging.
        visualstim_object : object or None
            Visual stimulus object from behavbox_DT_2p. No shape or unit conventions apply.

        Returns
        -------
        bool
            True if at least one close/stop call completed without raising an exception; False otherwise.
        """
        shutdown_completed = False

        for method_name in ("stop", "off", "close", "quit"):
            shutdown_completed = (
                self._call_shutdown_method(object_label, visualstim_object, method_name)
                or shutdown_completed
            )

        myscreen = getattr(visualstim_object, "myscreen", None) if visualstim_object is not None else None
        for method_name in ("close", "quit"):
            shutdown_completed = (
                self._call_shutdown_method(object_label + ".myscreen", myscreen, method_name)
                or shutdown_completed
            )

        return shutdown_completed

    def emergency_stop_all_cues(self):
        """
        Immediately turn off all task cues and stop the active trial.

        Parameters
        ----------
        None

        Returns
        -------
        None
            This method is used for side effects only. It turns off auditory cues, closes visual
            stimulus screens, and marks the trial as no longer running. No physical units apply.
        """
        logging.warning(str(time.time()) + ", emergency_stop_all_cues called")
        self.trial_running = False

        box = getattr(self, "box", None)
        if box is None:
            return

        # Auditory cues can otherwise remain on if Ctrl+C interrupts before the vacuum state.
        self._call_shutdown_method("box.sound1", getattr(box, "sound1", None), "off")
        self._call_shutdown_method("box.sound2", getattr(box, "sound2", None), "off")

        # Close both visual stimuli; the previous cleanup only closed visualstim_go.
        self._close_visualstim("box.visualstim_go", getattr(box, "visualstim_go", None))
        self._close_visualstim("box.visualstim_nogo", getattr(box, "visualstim_nogo", None))

    def start_session(self):
        ic("TODO: start video")
        self.box.video_start()

    def end_session(self):
        """
        Safely end the behavioral session.

        Parameters
        ----------
        None

        Returns
        -------
        None
            This method is used for side effects only. It stops all cues and video hardware.
            No physical units apply.
        """
        self.emergency_stop_all_cues()
        ic("TODO: stop video")
        self._call_shutdown_method("box", getattr(self, "box", None), "video_stop")
