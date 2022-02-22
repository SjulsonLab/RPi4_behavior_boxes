# python3: soyoun_task.py
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


class SoyounTask(object):
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

        from task_information_headfixed import task_information
        self.task_information = task_information

        self.error_repeat = self.task_information['error_repeat']
        self.error_count_max = self.task_information['error_repeat_max']

        # initialize the state machine
        self.states = [
            State(name='standby',
                  on_enter=["enter_standby"],
                  on_exit=["exit_standby"]),
            Timeout(name='draw',
                    on_enter=["enter_draw"],
                    on_exit=["exit_draw"],
                    timeout=0,
                    on_timeout=["play_game"]
                    ),
            Timeout(name="initiate",
                    on_enter=["enter_initiate"],
                    on_exit=["exit_initiate"],
                    timeout=self.task_information["initiation_timeout"],
                    on_timeout=["start_cue"]),
            Timeout(name='cue_state',
                    on_enter=["enter_cue_state"],
                    on_exit=["exit_cue_state"],
                    timeout=self.task_information["cue_timeout"],
                    on_timeout=["evaluate_reward"]),
            Timeout(name='reward_available',
                    on_enter=["enter_reward_available"],
                    on_exit=["exit_reward_available"],
                    timeout=self.task_information["reward_timeout"],
                    on_timeout=["restart"]
                    )
        ]
        self.transitions = [
            ['start_trial', 'standby', 'draw'],  # format: ['trigger', 'origin', 'destination']
            ['play_game', 'draw', 'initiate'],
            ['start_cue', 'initiate', 'cue_state'],
            ['evaluate_reward', 'cue_state', 'reward_available'],
            ['restart', ['initiate', 'cue_state', 'reward_available'], 'standby']
        ]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='standby'
        )
        self.session_length = len(self.task_information["block_list"])
        self.trial_running = False
        self.restart_flag = False

        self.error_count = 0
        self.card_count = -1
        self.deck = self.task_information["deck"]
        self.current_card = None

        # initialize behavior box
        self.box = behavbox.BehavBox(self.session_info)
        self.pump = behavbox.Pump()
        self.treadmill = self.box.treadmill
        self.distance_initiation = task_information['treadmill_setup']['distance_initiation']
        self.distance_buffer = None

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
        elif self.state == "draw":
            self.play_game()
        elif self.restart_flag:
            self.restart()
        elif self.state == "initiate":
            pass
        elif self.state == "cue_state":
            pass
        elif self.state == "reward_available":
            # first detect the lick signal:
            side_choice = self.task_information['choice'][self.current_card[1]]
            # question: do we want entry mark as lick?
            side_correct = None
            if event_name == "left_IR_entry":
                side_correct = 'left'
            elif event_name == "right_IR_entry":
                side_correct = 'right'
            if side_correct:
                if side_choice == side_correct:
                    self.pump.reward(side_correct, self.task_information["reward_size"])
                else:
                    self.error_count += 1
                    self.restart_flag = True
            else:
                # print("no lick detected")
                self.error_count += 1
                self.restart_flag = True
        # look for keystrokes
        self.box.check_keybd()

    def enter_standby(self):
        logging.info(str(time.time()) + ", entering standby")
        self.trial_running = False
        # self.restart_flag = False

    def exit_standby(self):
        logging.info(str(time.time()) + ", exiting standby")
        pass

    def enter_draw(self):
        logging.info(str(time.time()) + ", entering draw")
        if self.card_count >= self.session_length:
            self.trial_running = False  # terminate the state machine, end the session
        elif self.error_repeat and (self.error_count_max < self.error_count_max):
            self.restart_flag = True
            self.trial_running = True
        else:
            self.restart_flag = False
            self.trial_running = True

    def exit_draw(self):
        logging.info(str(time.time()) + ", exiting draw")
        if self.restart_flag:
            self.error_count += 1
            self.restart_flag = False
        else:
            self.card_count += 1
        # print(str(self.card_count))
        self.current_card = self.deck[self.card_count]

        print(str(self.current_card))
        card_cue = self.task_information['cue'][self.current_card[0]]
        card_state = self.task_information['state'][self.current_card[1]]
        card_choice = self.task_information['choice'][self.current_card[2]]
        card_reward = self.task_information['reward'][self.current_card[3]]
        print("****************************\n" +
              "Current card condition: \n" +
              "****************************\n" +
              "*Cue: " + str(card_cue) + "\n" +
              "*State: " + str(card_state) + "\n" +
              "*Choice: " + str(card_choice) + "\n" +
              "*Reward: " + str(card_reward) + "\n")

    def enter_initiate(self):
        # check error_repeat
        logging.info(str(time.time()) + ", entering initiate")
        # wait for treadmill signal and process the treadmill signal
        self.distance_buffer = self.treadmill.distance_cm
        logging.info(str(time.time()) + ", treadmill distance t0: " + str(self.distance_buffer))

    def exit_initiate(self):
        # check the flag to see whether to shuffle or keep the original card
        logging.info(str(time.time()) + ", exiting initiate")
        pass

    def enter_cue_state(self):
        logging.info(str(time.time()) + ", entering cue state")
        # turn on the cue according to the current card
        distance_now = self.treadmill.distance_cm
        logging.info(str(time.time()) + ", treadmill distance tend: " + str(distance_now))
        distance_pass = self.check_distance(distance_now, self.distance_buffer, self.distance_initiation)
        if not distance_pass:
            logging.info(str(time.time()) + ", initiation distance: not satisfied, restart now.")
            self.error_count += 1
            self.restart_flag = True
            self.error_count += 1
        else:
            # pass the initial check and now officially entering the cue state step
            self.check_cue(self.task_information['cue'][self.current_card[0]])
            # wait for treadmill signal and process the treadmill signal
            self.distance_buffer = self.treadmill.distance_cm
            logging.info(str(time.time()) + ", treadmill distance t0: " + str(self.distance_buffer))

    def exit_cue_state(self):
        logging.info(str(time.time()) + ", exiting cue state: turning off the cue now.")
        self.cue_off(self.task_information['cue'][self.current_card[0]])
        # if self.restart_flag:
        #     self.error_count += 1

    def enter_reward_available(self):
        logging.info(str(time.time()) + ", entering reward available")
        distance_now = self.treadmill.distance_cm
        logging.info(str(time.time()) + ", treadmill distance tend: " + str(distance_now))
        distance_required = self.task_information['treadmill_setup'][self.task_information["state"][self.current_card[1]]]
        distance_pass = self.check_distance(distance_now, self.distance_buffer, distance_required)
        if not distance_pass:
            logging.info(str(time.time()) + ", treadmill state distance did not pass: " + str(distance_now))
            self.error_count += 1
            self.restart_flag = True
        else:
            self.restart_flag = False

    def exit_reward_available(self):
        logging.info(str(time.time()) + ", exiting reward available")
        pass

    def check_cue(self, cue):
        if cue == 'sound':
            # self.box.sound1.on()  # could be modify according to specific sound cue
            logging.info(str(time.time()) + ", cue sound1 on")
        elif cue == 'LED':
            # self.box.cueLED1.on()
            logging.info(str(time.time()) + ", cueLED1 on")
        else:
            # self.box.sound1.on()
            # self.box.cueLED1.on()
            logging.info(str(time.time()) + "sound1 + cueLED1 on (free choice)")

    def cue_off(self, cue):
        if cue == 'sound':
            self.box.sound1.off()  # could be modify according to specific sound cue
            logging.info(str(time.time()) + ", cue sound1 off")
        elif cue == 'LED':
            self.box.cueLED1.off()
            logging.info(str(time.time()) + ", cueLED1 off")
        else:
            self.box.sound1.off()
            self.box.cueLED1.off()
            logging.info(str(time.time()) + "sound1 + cueLED1 off (free choice)")

    def check_distance(self, distance_t1, distance_t0, distance_required):
        # bit_low = 100; bit_high = 200
        # distance_low = bit_low/self.treadmill.treadmill_calibrate
        # distance_high = bit_high/self.treadmill.treadmill_calibrate
        # if distance_t1 <= distance_low & distance_t0 >= distance_high:
        #     distance_diff = (distance_t1 + 255) - distance_t0
        # else:
        distance_diff = distance_t1 - distance_t0
        if distance_diff >= distance_required:
            pass
        else:
            return False
        return True

    ########################################################################
    # methods to start and end the behavioral session
    ########################################################################
    def start_session(self):
        ic("TODO: start video")
        self.box.video_start()

    def end_session(self):
        ic("TODO: stop video")
        self.box.video_stop()