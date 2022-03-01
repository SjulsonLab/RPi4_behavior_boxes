# python3: lick_task.py
import importlib
from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
import pysistence, collections
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


class LickTask(object):
    # Define states. States where the animals is waited to make their decision

    def __init__(self, **kwargs):  # name and task_information should be provided as kwargs

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
        try:
            logging.info(str(time.time()) + ", trying to retrieve task_information from the ~/experiment_info/*")
            full_module_name = 'task_information_lick'
            import sys
            task_info_path = '/home/pi/experiment_info/headfixed_task/'
            sys.path.insert(0, task_info_path)
            tempmod = importlib.import_module(full_module_name)
            self.task_information = tempmod.task_information
        except:
            logging.info(str(time.time()) + ", failed to retrieve task_information from the default path.\n" +
                         "Now, try to load the task_information from the local directory ...")
            from task_information_headfixed import task_information
            self.task_information = task_information

        # initialize the state machine
        self.states = [
            Timeout(name='standby',
                    on_enter=["enter_standby"],
                    on_exit=["exit_standby"],
                    timeout=self.task_information['standby_wait'],
                    on_timeout=["start_trial"]),
            Timeout(name='cue',
                    on_enter=["enter_cue"],
                    on_exit=["exit_cue"],
                    timeout=self.task_information["cue_timeout"],
                    on_timeout=["evaluate_reward"]),
            Timeout(name='reward_available',
                    on_enter=["enter_reward_available"],
                    on_exit=["exit_reward_available"],
                    timeout=self.task_information["reward_timeout"],
                    on_timeout=["restart"])
        ]
        self.transitions = [
            ['start_trial', 'standby', 'cue'],  # format: ['trigger', 'origin', 'destination']
            ['evaluate_reward', 'cue_state', 'reward_available'],
            ['restart', 'reward_available', 'standby']
        ]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='standby'
        )
        self.trial_running = False
        self.trial_number = 0
        self.restart_flag = False

        # initialize behavior box
        self.box = behavbox.BehavBox(self.session_info)
        self.pump = behavbox.Pump()
        self.treadmill = self.box.treadmill

    ########################################################################
    # functions called when state transitions occur
    ########################################################################
    def run(self):
        if self.box.event_list:
            event_name = self.box.event_list.popleft()
        else:
            event_name = ""
        if self.state == "standby":
            pass
        elif self.restart_flag:
            self.restart()
        elif self.state == "reward_available":
            # first detect the lick signal:
            side_mice = None
            if event_name == "left_IR_entry":
                side_mice = 'left'
            elif event_name == "right_IR_entry":
                side_mice = 'right'
            if side_mice:
                reward_size = self.task_information['reward_size']['small']
                self.pump.reward(side_mice, reward_size)
                self.restart()
            else:
                pass
        # look for keystrokes
        self.box.check_keybd()

    def enter_standby(self):
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", entering standby, prepare to start the trial...")
        self.trial_running = False
        if self.restart_flag:
            time.sleep(self.task_information["punishment_timeout"])
            # pass
        else:
            time.sleep(self.task_information["reward_wait"])

    def exit_standby(self):
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", exiting standby")
        self.trial_number += 1
        pass

    def enter_cue(self):
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", entering cue state")
        # pass the initial check and now officially entering the cue state step
        self.check_cue(None)

    def exit_cue(self):
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", exiting cue state")

    def enter_reward_available(self):
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", entering reward available")
        if not self.restart_flag:
            self.cue_off(None)

    def exit_reward_available(self):
        logging.info(str(time.time()) + ", " + str(self.trial_number) + ", exiting reward available")
        pass

    def check_cue(self, cue):
        if cue == 'sound':
            self.box.sound1.on()  # could be modify according to specific sound cue
            logging.info(str(time.time()) + ", " + str(self.trial_number) + ", cue sound1 on")
        elif cue == 'LED':
            self.box.cueLED1.on()
            logging.info(str(time.time()) + ", " + str(self.trial_number) + ", cueLED1 on")
        elif cue == 'sound+LED':
            self.box.sound1.on()
            self.box.cueLED1.on()
            logging.info(str(time.time()) + ", " + str(self.trial_number) + ", sound1 + cueLED1 on (free choice)")
        else:
            logging.info(str(time.time()) + ", " + str(self.trial_number) + ", silent cue (no cue)")
            pass

    def cue_off(self, cue):
        if cue == 'sound':
            self.box.sound1.off()  # could be modify according to specific sound cue
            logging.info(str(time.time()) + ", " + str(self.trial_number) + ", cue sound1 off")
        elif cue == 'LED':
            self.box.cueLED1.off()
            logging.info(str(time.time()) + ", " + str(self.trial_number) + ", cueLED1 off")
        elif cue == 'sound+LED':
            self.box.sound1.off()
            self.box.cueLED1.off()
            logging.info(str(time.time()) + ", " + str(self.trial_number) + ", sound1 + cueLED1 off (free choice)")
        else:
            logging.info(str(time.time()) + ", " + str(self.trial_number) + ", silent cue (no cue) off")
            pass

    # def check_distance(self, distance_t1, distance_t0, distance_required):
    #     distance_diff = distance_t1 - distance_t0
    #     if distance_diff >= distance_required:
    #         pass
    #     else:
    #         return False
    #     return True

    ########################################################################
    # methods to start and end the behavioral session
    ########################################################################
    def start_session(self):
        ic("TODO: start video")
        self.box.video_start()

    def end_session(self):
        ic("TODO: stop video")
        self.box.video_stop()