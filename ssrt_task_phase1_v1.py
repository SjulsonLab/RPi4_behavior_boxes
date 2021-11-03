from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
import pysistence, collections
from icecream import ic
import logging
import datetime as dt
import os
from gpiozero import PWMLED, LED, Button
from colorama import Fore, Style
import logging.config
import time
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.backends.backend_agg as agg
import matplotlib.pyplot as plt

import pygame
from pygame.locals import *
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
            # visual stim is initiated at the exit of initation state, vstim state is actually lockout state (200ms)
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
                # timeout=self.session_info["lick_count_length"],
                # on_timeout=["start_vacuum_from_lick_count"],
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
        # print("entering standby")
        logging.info(str(time.time()) + ", entering standby")
        self.trial_running = False

    def exit_standby(self):
        # print("exiting standby")
        logging.info(str(time.time()) + ", exiting standby")

    def enter_initiation(self):
        self.trial_running = True
        # print("entering initiation")
        logging.info(str(time.time()) + ", entering initiation")
        self.box.cueLED1.on()
        print("LED ON!")

    def exit_initiation(self):
        logging.info(str(time.time()) + ", exiting initiation")
        self.box.cueLED1.off()
        print("LED OFF!")

    def enter_vstim(self):
        # print("displaying vstim")
        logging.info(str(time.time()) + ", entering vstim")
        # start to load vstim and display it
        self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[0])
        # start the countdown of time since display of vstim, this is used as timeup to transition lick_count to vacuum
        self.countdown(3)

    def exit_vstim(self):
        # print("transitioning to reward_available")
        logging.info(str(time.time()) + ", exiting vstim")

    def enter_reward_available(self):
        # print("entering reward_available")
        logging.info(str(time.time()) + ", entering reward_available")

    def exit_reward_available(self):
        # print("exiting reward_available")
        logging.info(str(time.time()) + ", exiting reward_available")

    def enter_lick_count(self):
        # print("entering lick_count")
        logging.info(str(time.time()) + ", entering lick_count")

    def exit_lick_count(self):
        # print("exiting lick_count")
        logging.info(str(time.time()) + ", exiting lick_count")

    def enter_vacuum(self):
        # print("entering vacuum")
        logging.info(str(time.time()) + ", entering vacuum")
        self.box.vacuum_on()

    def exit_vacuum(self):
        # print("exiting vacuum")
        logging.info(str(time.time()) + ", exiting vacuum")
        self.box.vacuum_off()

    def enter_iti(self):
        # print("entering ITI")
        logging.info(str(time.time()) + ", entering iti")

    def exit_iti(self):
        # print("exiting ITI")
        logging.info(str(time.time()) + ", exiting iti")

    ########################################################################
    # countdown function to run when vstim starts to play
    # t is the length of countdown (in seconds)
    ########################################################################
    def countdown(self, t):
        while t:
            mins, secs = divmod(t, 60)
            timer = '{:02d}:{:02d}'.format(mins, secs)
            print(timer, end="\r")
            time.sleep(1)
            t -= 1

        print('vstim time up!')
        self.box.event_list.append("vstim 3s countdown is up!")

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
            if event_name == "vstim 3s countdown is up!":
                self.start_vacuum_from_lick_count()

        elif self.state == "vacuum":
            pass

        elif self.state == "iti":
            pass

        # look for keystrokes
        # self.box.check_keybd()

    ########################################################################
    # define function called for baiting
    ########################################################################
    def bait(self):

        # read for input trigger for reward (1 is the input trigger)
        self.value = input("Please enter 'r' for reward delivery, 'phase1' to start the task: \n")
        if self.value == "r":
            print(f'You entered {self.value}, delivering reward')
            self.pump.reward("left", self.session_info["reward_size"])

    ########################################################################
    # define functions called when plotting
    ########################################################################

    # create a function to output lick data
    def lick_detector(self):

        if self.box.event_list:
            detected_events = self.box.event_list.popleft()
        else:
            detected_events = ""

        while detected_events == "left_IR_entry":
            return 1
        else:
            return 0

    # this function plots event_plot using matplotlib and pygame
    # will be updated at the end of each trial during standby period

    def plot_ssrt(self):

        # establish trial_list and trial_outcome
        # trial_list = list(range(0, self.session_info["number_of_trials"]))
        # trial_outcome = ["" for o in range(self.session_info["number_of_trials"])]

        # Plot the figure
        fig, axs = plt.subplots(2, 2)
        matplotlib.rcParams['font.size'] = 3.0
        # create random data
        data1 = np.random.random([4, 50])
        # set different colors for each set of positions
        colors1 = ['C{}'.format(i) for i in range(6)]
        # set different line properties for each set of positions
        # note that some overlap
        lineoffsets1 = np.array([-15, -3, 1, 1.5])
        linelengths1 = [5, 2, 1, 1]
        # create a horizontal plot
        axs[0, 0].eventplot(data1, colors=colors1, lineoffsets=lineoffsets1,
                            linelengths=linelengths1)
        # create a vertical plot
        axs[1, 0].eventplot(data1, colors=colors1, lineoffsets=lineoffsets1,
                            linelengths=linelengths1, orientation='vertical')
        # create another set of random data.
        # the gamma distribution is only used fo aesthetic purposes
        data2 = np.random.gamma(4, size=[60, 50])
        # use individual values for the parameters this time
        # these values will be used for all data sets (except lineoffsets2, which
        # sets the increment between each data set in this usage)
        colors2 = 'black'
        lineoffsets2 = 1
        linelengths2 = 1
        # create a horizontal plot
        axs[0, 1].eventplot(data2, colors=colors2, lineoffsets=lineoffsets2,
                            linelengths=linelengths2)
        # create a vertical plot
        axs[1, 1].eventplot(data2, colors=colors2, lineoffsets=lineoffsets2,
                            linelengths=linelengths2, orientation='vertical')

        # Draw on canvas
        canvas = agg.FigureCanvasAgg(fig)
        canvas.draw()
        renderer = canvas.get_renderer()
        raw_data = renderer.tostring_rgb()
        pygame.init()
        window = pygame.display.set_mode((1000, 800), DOUBLEBUF)
        screen = pygame.display.get_surface()
        size = canvas.get_width_height()
        surf = pygame.image.fromstring(raw_data, size, "RGB")
        screen.blit(surf, (0, 0))
        pygame.display.flip()

        # Close figure when pygame quit
        show = True
        while show:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # Stop showing when quit
                    show = False
            pygame.display.update()

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