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

        # establish trial_list and trial_outcome
        self.trial_list = list(range(0, self.session_info["number_of_trials"]))
        self.trial_outcome = ["" for o in range(self.session_info["number_of_trials"])]

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
        self.time_at_lick = np.array([])
        self.trial_start_time = time.time()
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
        self.time_at_vstim_on = time.time()
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
        self.time_enter_lick_count = time.time() - self.trial_start_time
        logging.info(str(time.time()) + ", entering lick_count")

    def exit_lick_count(self):
        # print("exiting lick_count")
        self.time_exit_lick_out = time.time() - self.trial_start_time
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
        self.trial_end_time = time.time() - self.trial_start_time
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

        if event_name == "left_IR_entry":
            self.time_at_lick = np.append(self.time_at_lick, time.time() - self.trial_start_time)

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
                self.time_at_reward = time.time() - self.trial_start_time
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
    # function for plotting
    ########################################################################

    # this function plots event_plot using matplotlib and pygame
    # will be updated at the end of each trial during standby period

    def plot_ssrt(self, current_trial):

        ########################################################################
        # initialize the figure
        ########################################################################
        fig = plt.figure(figsize=(13, 8))
        ax1 = fig.add_subplot(231)  # outcome
        ax2 = fig.add_subplot(212)  # eventplot
        ax3 = fig.add_subplot(232)
        ax4 = fig.add_subplot(233)

        ########################################################################
        # create an outcome plot
        ########################################################################
        lick_events = self.time_at_lick
        i, j = self.time_enter_lick_count, self.time_exit_lick_out
        self.trial_outcome[current_trial] = "Miss !!! Reward but no lick"

        if lick_events.size == 0:
            self.trial_outcome[current_trial] = "Miss !!! No lick at all"
        else:
            for ele in lick_events:
                if i < ele < j:
                    self.trial_outcome[current_trial] = "Hit! lick after reward"
                    break

        if current_trial < 15:
            textstr = '\n'.join((
                f"trial {self.trial_list[0]} : {self.trial_outcome[0]}",
                f"trial {self.trial_list[1]} : {self.trial_outcome[1]}",
                f"trial {self.trial_list[2]} : {self.trial_outcome[2]}",
                f"trial {self.trial_list[3]} : {self.trial_outcome[3]}",
                f"trial {self.trial_list[4]} : {self.trial_outcome[4]}",
                f"trial {self.trial_list[5]} : {self.trial_outcome[5]}",
                f"trial {self.trial_list[6]} : {self.trial_outcome[6]}",
                f"trial {self.trial_list[7]} : {self.trial_outcome[7]}",
                f"trial {self.trial_list[8]} : {self.trial_outcome[8]}",
                f"trial {self.trial_list[9]} : {self.trial_outcome[9]}",
                f"trial {self.trial_list[10]} : {self.trial_outcome[10]}",
                f"trial {self.trial_list[11]} : {self.trial_outcome[11]}",
                f"trial {self.trial_list[12]} : {self.trial_outcome[12]}",
                f"trial {self.trial_list[13]} : {self.trial_outcome[13]}",
                f"trial {self.trial_list[14]} : {self.trial_outcome[14]}"))
        elif current_trial >= 15:
            textstr = '\n'.join((
                f"trial {self.trial_list[0 + (current_trial - 14)]} : {self.trial_outcome[0 + (current_trial - 14)]}",
                f"trial {self.trial_list[1 + (current_trial - 14)]} : {self.trial_outcome[1 + (current_trial - 14)]}",
                f"trial {self.trial_list[2 + (current_trial - 14)]} : {self.trial_outcome[2 + (current_trial - 14)]}",
                f"trial {self.trial_list[3 + (current_trial - 14)]} : {self.trial_outcome[3 + (current_trial - 14)]}",
                f"trial {self.trial_list[4 + (current_trial - 14)]} : {self.trial_outcome[4 + (current_trial - 14)]}",
                f"trial {self.trial_list[5 + (current_trial - 14)]} : {self.trial_outcome[5 + (current_trial - 14)]}",
                f"trial {self.trial_list[6 + (current_trial - 14)]} : {self.trial_outcome[6 + (current_trial - 14)]}",
                f"trial {self.trial_list[7 + (current_trial - 14)]} : {self.trial_outcome[7 + (current_trial - 14)]}",
                f"trial {self.trial_list[8 + (current_trial - 14)]} : {self.trial_outcome[8 + (current_trial - 14)]}",
                f"trial {self.trial_list[9 + (current_trial - 14)]} : {self.trial_outcome[9 + (current_trial - 14)]}",
                f"trial {self.trial_list[10 + (current_trial - 14)]} : {self.trial_outcome[10 + (current_trial - 14)]}",
                f"trial {self.trial_list[11 + (current_trial - 14)]} : {self.trial_outcome[11 + (current_trial - 14)]}",
                f"trial {self.trial_list[12 + (current_trial - 14)]} : {self.trial_outcome[12 + (current_trial - 14)]}",
                f"trial {self.trial_list[13 + (current_trial - 14)]} : {self.trial_outcome[13 + (current_trial - 14)]}",
                f"trial {self.trial_list[14 + (current_trial - 14)]} : {self.trial_outcome[14 + (current_trial - 14)]}"))

        ax1.set_title('Trial Outcome', fontsize=12)
        ax1.text(0.05, 0.95, textstr, fontsize=9, verticalalignment='top')
        ax1.set_xticklabels([])
        ax1.set_xticks([])
        ax1.set_yticks([])
        ax1.set_yticklabels([])

        ########################################################################
        # create eventplot (vertical)
        ########################################################################
        # create a 2D array for eventplot
        events_to_plot = [self.time_at_lick, [self.time_at_reward]]

        # create vstim time data
        vstim_duration = 3  # in seconds
        vstim_bins = 70  # number of bins
        time_vstim_on = self.time_at_vstim_on - self.trial_start_time
        time_vstim_index_on = int(round(time_vstim_on * vstim_bins/7))
        time_vstim_index_off = int(time_vstim_index_on + round(vstim_duration*(vstim_bins/7)))
        vstim_plot_data_x = np.linspace(0, 7, num=vstim_bins)
        vstim_plot_data_y = np.zeros(vstim_bins)
        range_of_vstim_on = int(time_vstim_index_off - time_vstim_index_on)
        vstim_plot_data_y[time_vstim_index_on:time_vstim_index_off] = np.ones(range_of_vstim_on)

        # set different colors for each set of positions
        colors1 = ['C{}'.format(i) for i in range(2)]
        # set different line properties for each set of positions
        lineoffsets1 = np.array([7, 4])
        linelengths1 = [2, 2]
        ax2.set_title('Events', fontsize=12)
        ax2.eventplot(events_to_plot, colors=colors1, lineoffsets=lineoffsets1, linelengths=linelengths1)
        ax2.plot(vstim_plot_data_x, vstim_plot_data_y)
        ax2.set_xlim([0, 7])  # 7s total since the start of initiation until the end of iti

        ########################################################################
        # create cummulative outcome plots
        ########################################################################

        # the gamma distribution is only used fo aesthetic purposes
        data2 = np.random.gamma(4, size=[60, 50])
        # use individual values for the parameters this time
        # these values will be used for all data sets (except lineoffsets2, which
        # sets the increment between each data set in this usage)
        colors2 = 'black'
        lineoffsets2 = 1
        linelengths2 = 1
        # create a horizontal plot
        ax3.eventplot(data2, colors=colors2, lineoffsets=lineoffsets2,
                            linelengths=linelengths2)
        # create a vertical plot
        ax4.eventplot(data2, colors=colors2, lineoffsets=lineoffsets2,
                            linelengths=linelengths2, orientation='vertical')

        # Draw on canvas
        canvas = agg.FigureCanvasAgg(fig)
        canvas.draw()
        renderer = canvas.get_renderer()
        raw_data = renderer.tostring_rgb()
        pygame.init()
        window = pygame.display.set_mode((1300, 800), DOUBLEBUF)
        screen = pygame.display.get_surface()
        size = canvas.get_width_height()
        surf = pygame.image.fromstring(raw_data, size, "RGB")
        screen.blit(surf, (0, 0))
        pygame.display.flip()

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