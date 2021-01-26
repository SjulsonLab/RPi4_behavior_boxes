from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
import pysistence, collections
from icecream import ic
import logging
from datetime import datetime
import os
from gpiozero import PWMLED, LED, Button
import logging.config
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
})
# all modules above this line will have logging disabled

import behavbox

# adding timing capability to the state machine
@add_state_features(Timeout)
class TimedStateMachine(Machine):
    pass

class KellyTask(object):

    # some parameters
    timeout_length = 5  # in seconds
    reward_size    = 10 # in uL

    ########################################################################
    # Three possible states: standby, reward_available, and cue
    ########################################################################
    states = [
        State(name='standby', on_enter=['enter_standby'], on_exit=['exit_standby']),
        State(name='reward_available', on_enter=['enter_reward_available'], 
            on_exit=['exit_reward_available']),
        {'name': 'cue', 'timeout': timeout_length, 'on_timeout': 'timeup', 'on_enter': 'enter_cue', 'on_exit': 'exit_cue'}
    ]

    ########################################################################
    # list of possible transitions between states
    # format is: [event_name, source_state, destination_state]
    ########################################################################
    transitions = [
        ['trial_start', 'standby', 'reward_available'],
        ['active_poke', 'reward_available', 'cue'],
        ['timeup', 'cue', 'standby']
    ]

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
        self.trial_running = True

    def exit_reward_available(self):
        print("stop white noise")

    def enter_cue(self):
        print("deliver reward")
        self.box.reward('left', self.reward_size)
        print("start cue")
        self.box.cueLED1.on()

    def exit_cue(self):
        print("stop cue")
        self.box.cueLED1.off()

    ########################################################################
    # initialize state machine and behavior box
    ########################################################################
    def __init__(self, name, session_info):

        self.name = name
        self.machine = TimedStateMachine(model=self, states=KellyTask.states, transitions=KellyTask.transitions, 
            initial='standby')
        self.trial_running = False
        self.session_info = session_info

        # initialize behavior box
        self.box = behavbox.BehavBox(self.session_info)

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
            event_name = ''

        if self.state=='standby':
            pass

        elif self.state=='reward_available':
            if event_name=='left_poke_entry':
                self.active_poke()  # triggers state transition 

        elif self.state=='cue':
            pass

        # look for keystrokes
        self.box.check_keybd()



    ########################################################################
    # methods to start and end the behavioral session
    ########################################################################
    def start_session(self):
        ic('TODO: start video')
        self.box.video_start()

    def end_session(self):
        ic('TODO: stop video')
        self.box.video_stop()

