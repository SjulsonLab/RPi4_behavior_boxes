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

        if kwargs.get("task_session_info", None) is None:
            print(
                Fore.RED
                + Style.BRIGHT
                + "Warning: no task_session_info supplied; making fake one"
                + Style.RESET_ALL
            )
            from task_information_headfixed import task_information

            self.task_information = task_information
        else:
            self.task_information = kwargs.get("task_information", None)
        ic(self.task_information)

        # import task information for the condition setup
        # from task_information_headfixed import task_information

        # self.task_information = task_information # when initiated, task_information generates a shuffled deck
        self.error_repeat = self.task_information['error_repeat']
        self.error_count_max = self.task_information['error_repeat_max']

        # setup condition for the treadmill signal
        self.distance_initiation = self.task_information['distance_initiation'] #cm
        self.distance_short = self.task_information['distance_short']
        self.distance_max = self.task_information['distance_max']

        # initialize the state machine
        self.states = [
            State(name = 'standby',
                  on_enter = ["enter_standby"],
                  on_exit = ["exit_standby"]),
            Timeout(name = "initiate",
                    on_enter = ["enter_initiate"],
                    on_exit = ["exit_initiate"],
                    timeout = self.task_information["initiation_timeout"],
                    on_timeout = ["start_cue"]),
            Timeout(name = 'cue_state',
                    on_enter = ["enter_cue_state"],
                    on_exit = ["exit_cue_state"],
                    timeout = self.task_information["cue_timeout"],
                    on_timeout = ["evaluate_reward"]),
            Timeout(name = 'reward_available',
                    on_enter = ["enter_reward_available"],
                    on_exit = ["exit_reward_available"],
                    timeout = self.task_information["reward_timeout"],
                    on_timeout = ["restart"])
        ]
        self.transitions = [
            ['start_trial', 'standby', 'initiate'], # format: ['trigger', 'origin', 'destination']
            ['start_cue', 'initiate','cue_state'],
            ['evaluate_reward', 'cue_state', 'reward_available'],
            ['restart', ['initiate', 'cue_state', 'reward_available'], 'standby']
        ]

        self.machine = TimedStateMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial='standby'
        )
        self.trial_running = True
        self.restart_flag = False

        self.error_count = 0
        self.card_count = 0
        self.deck = self.task_information["deck"]
        self.current_card = None

        # initialize behavior box
        self.box = behavbox.BehavBox(self.session_info)
        self.pump = behavbox.Pump()
        self.treadmill = self.box.treadmill
        self.distance_initiation = task_information['treadmill_setup']['distance_initiation']
        self.distance_short = task_information['treadmill_setup']['distance_short']

    ########################################################################
    # functions called when state transitions occur
    ########################################################################
    def run(self):
        if self.box.event_list:
            event_name = self.box.event_list.popleft()
        else:
            event_name = ""

        if self.state == "reward_available":
            # first detect the lick signal:
            side_choice = self.task_information['choice'][self.current_card[1]]
            # question: do we want entry mark as lick?
            if event_name == "left_IR_entry": side_correct = 'left'
            elif event_name == "right_IR_entry": side_correct = 'right'
            if side_choice == side_correct:
                self.pump.reward(side_correct, self.task_information["reward_size"])

        # look for keystrokes
        self.box.check_keybd()

    def enter_standby(self):
        logging.info(str(time.time()) + ", entering standby")
        self.trial_running = False

    def exit_standby(self):
        logging.info(str(time.time()) + ", exiting standby")
        pass

    def enter_initiate(self):
        # check error_repeat
        logging.info(str(time.time()) + ", entering initiate")
        if self.card_count > self.task_information["total_block_length"]:
            self.trial_running = False # terminate the state machine, end the session
        elif self.error_repeat and (self.error_count_max < self.error_count_max):
            self.restart_flag = True
            self.trial_running = True
        else:
            self.restart_flag = False
            self.trial_running = True

    def exit_initiate(self):
        # check the flag to see whether to shuffle or keep the original card
        logging.info(str(time.time()) + ", exiting initiate")
        if self.restart_flag:
            self.error_count += 1
        else:
            self.current_card = self.deck[self.card_count]
            self.card_count += 1

    def enter_cue_state(self, wait_time):
        # turn on the cue according to the current card
        logging.info(str(time.time()) + ", entering cue state")
        self.check_cue(self.current_card[0])
        # wait for treadmill signal and process the treadmill signal
        distance_start = self.treadmill.distance()
        logging.info(str(time.time()) + ", treadmill distance t0: " + str(distance_start))
        sleep(wait_time)
        distance_end = self.treadmill.distance()
        logging.info(str(time.time()) + ", treadmill distance tend: " + str(distance_end))
        distance_pass = self.check_distance(distance_end - distance_start, self.distance_initiation)
        if not distance_pass: self.restart_flag = True
        else: self.restart_flag = False

    def exit_cue_state(self):
        logging.info(str(time.time()) + ", exiting cue state")
        if self.restart_flag:
            self.error_count += 1
            self.restart()


    def enter_reward_available(self):
        logging.info(str(time.time()) + ", entering reward available")
        pass

    def exit_reward_available(self):
        logging.info(str(time.time()) + ", exiting reward available")
        self.restart()

    def check_cue(self, cue):
        if cue == 'sound':
            self.sound1.on() # could be modify according to specific sound cue
            logging.info(str(time.time()) + ", cue sound1 on")
        elif cue == 'LED':
            self.cueLED1.on()
            logging.info(str(time.time()) + ", cueLED1 on")
        else:
            print("Not valid cue: " + cue)

    def check_distance(self, distance_now, distance_required):
        if distance_now >= distance_required:
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
        self.box.visualstim.myscreen.close()

    # def check_lick(self, side_index):
    #     # first detect the lick signal:
    #     side = self.task_information['choice'][side_index]
    #     event_name = self.box.event_list.popleft()
    #     if side == 'right':
    #
    #     elif side == 'left':
    #
    #     else:
    #         print(str(side) + " is not allowed")
    #         self.restart_flag == False
    #
    # def check_reward(self, index):
    #     reward = self.task_information['reward'][index]
    #     reward_size = self.task_information['reward_size'][reward]
    #     self.pump.reward()

    # def initiate(self):
    #
    #
    # def short_distance(self):
    #     """
    #     only if animal walked equal or less than x2
    #     else throw error + callback
    #     """
    #     print("the animal walked a short distance(x2 cm)")
    #     print("Cue off")
    #
    # def long_distance(self):
    #     """
    #     only if animal walked more than x2 distance
    #     else transition to short_distance and throw error callback
    #     """
    #     print("the animal walked a long distance(>x2 cm)")
    #     print('Cue off')
    #
    # def lick_detected(self):
    #     print("entering reward_delivery")
    #
    # def run(self):
    #     """
    #     if enter from state_short:
    #         if animal licked left:
    #             pump deliver higher reward
    #         if animal licked right:
    #             pump deliver lower reward
    #         else(not licked within required time):
    #             time out
    #     if enter from state_long:
    #         if animal licked left:
    #             pump deliver lower reward
    #         if animal licked right:
    #             pump deliver higher reward
    #         else:
    #             time out
    #     """
    #     if self.box.event_list:
    #         event_name = self.box.event_list.popleft()
    #     else:
    #         event_name = ""
    #
    #     if self.state == "standby":
    #         distance_start = self.treadmill.running_speed
    #         while True:
    #             distance_buffer = self.treadmill.running_speed - distance_start
    #             if distance_buffer > self.dist_init:
    #                 break
    #     if self.state == "cue":
    #         if self.session_info['initial_state'] == 'sound_long':
    #             # sound on: long distance = large reward; short distance = smalle reward
    #             if event_name == "left_IR_entry":
    #                 ic("large reward")
    #                 # question: which pump gives the larger reward, which is not?
    #                 self.pump.reward("left", self.session_info["reward_size"])
    #             if event_name == "right_IR_entry":
    #                 ic("small reward")
    #                 self.pump_reward("right", self.session_info["reward_size"])
    #         if self.session_info['initial_state'] == 'sound_short':
    #             if event_name == "left_IR_entry":
    #                 ic("small reward")
    #                 # question: which pump gives the larger reward, which is not?
    #                 self.pump.reward("right", self.session_info["reward_size"])
    #             if event_name == "right_IR_entry":
    #                 ic("large reward")
    #                 self.pump_reward("left", self.session_info["reward_size"])


"""
consecutive control
    same condition can not be repeated for more than 3 trials
correction trial
    repeat the mistaken trial the animal until they are correct


block = 1
    force choice condition (LED - large, sound - small)
        LED - short right, reward = large
        LED - long left, reward = large
        
        sound - short left, reward = small
        sound - long right, reward = small
        
        if free choice condition
            LED, sound - short
                if choose right: reward = large
                if choose left: reward = small
            LED, sound - long
                if choose left: reward = large
                if choose right: reward = small
                
                
block = 2
    force choice condition (LED - small, sound - large)
        LED - short right, reward = small
        LED - long left, reward = small
        
        sound - short left, reward = large
        sound - long right, reward = large
        
        if free choice condition
            LED, sound - short
                if choose right: reward = small
                if choose left: reward = large
            LED, sound - long
                if choose left: reward = small
                if choose right: reward = large
            
"""

"""
State machine structure
State machine states:
    "standby" - the beginning of each trial, initiate the psudo-random trial content (shuffle)
    "cue_state" - initiate by the x1 distance and turn on the appropriate cue according to the pre-configured trial context
    "cue_off" - triggered by the satisfaction of treadmill signal x1, and turn off the cue. detect x2 or x3 from treadmill signal
    "detect_reward" - detect lick spot signal and deliver corresponding reward or punishment
    
State machine transition:
    enter_standby
        if previous trial wrong + error_repeat == True + error_repeat_count <= error_repeat_max:
            don't change the condition parameters
        else:
            error_repeat_count = 0
            psudo-shuffle - in fact extract trial information from pre-set psudo-randomize deck
                shuffle += 1
                trial_deck[shuffle] # a dictionary contains condition parameters
    exit_standyby
        wait for the treadmill signal fullfill x1 amount of distance
        no_respond more than a set amount of time:
            error_repeat_count += 1
            timeout(_seconds)
            enter_standby
        else:
            pass
    enter_cue_state
        pass
    exit_cue_state
        play cue
        pass
    enter_cue_off
        wait for the treadmill signal fullfill x2 or x3 amount of distance (according to the specific trial requirement)
        if fullfilled, turn off the cue or return to the beginning of the trial if longer than delay or detect wrong
        response
    exit_cue_off
        pass
    enter_detect_reward
        detect lick spot
    exit_detect_reward
        if wrong:
            if allow_switch == False:
                error_repeat_count += 1
                enter_standby
        if right:
            deliver the appropriate reward
            error_repeat_count = 0
            enter_standby
    
"""


"""
# within the run_file
def shuffle_conditions:
    create a list of conditon
    condition index(row_number);        cue;        state;      lick_side;
    create a list of cue
        block_1_forced_choice: {
            'cue': [TRUE, TRUE, FALSE, FALSE], # TRUE: LED, FALSE: sound
            'state': [FALSE, TRUE, FALSE, TRUE], # TRUE: long, FALSE: short
            'lick_side': [FALSE, TRUE, TRUE, FALSE], # TRUE: left, FALSE: right
            'reward_size': [TRUE, TRUE, FALSE, FALSE] # TRUE: large, FALSE: small
        }
        
        block_2_forced_choice = block_1_forced_choice
        block_2_forced_choice['reward_size'] = not block_1_forced_choice['reward_size']
        
        block_1_free_choice: {
            'cue': None
            'state': [FALSE, FALSE, TRUE, TRUE], # TRUE: long, FALSE: short
            'lick_side': [FALSE, TRUE, FALSE, TRUE], # TRUE: left, FALSE: right
            'reward_size': [TRUE, FALSE, FALSE, TRUE] # TRUE: large, FALSE: small
        }
        
        block_2_free_choice = block_1_free_choice
        block_2_free_choice['reward_size'] = not block_1_free_choice['reward_size']
"""