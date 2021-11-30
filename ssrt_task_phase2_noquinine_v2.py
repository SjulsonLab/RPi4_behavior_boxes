from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
from icecream import ic
import logging
import os
from colorama import Fore, Style
import logging.config
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.backends.backend_agg as agg
import matplotlib.pyplot as plt
import pygame
from pygame.locals import *
import numpy as np
import multiprocessing

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
        # Insert neutral states whenever is needed to transition between 2 possible types of trials
        ########################################################################
        self.states = [
            State(name="standby", on_enter=["enter_standby"], on_exit=["exit_standby"]),

            # initiation state: LED light is turned ON for 1s
            Timeout(
                name="initiation_go",
                on_enter=["enter_initiation_go"],
                on_exit=["exit_initiation_go"],
            ),
            Timeout(
                name="initiation_ss",
                on_enter=["enter_initiation_ss"],
                on_exit=["exit_initiation_ss"],
            ),

            # astim state: serves as a stop signal, ON 1s before vstim, but right after init LED
            # lasts until end of vstim
            Timeout(
                name="astim",
                on_enter=["enter_astim"],
                on_exit=["exit_astim"],
                timeout=self.session_info["delay_time"],
                on_timeout=["start_vstim_astim"],
            ),

            # vstim state: start vstim display (automatic once start, can move on to the next state)
            # visual stim is initiated at the exit of initation state, vstim state is actually lockout state (200ms)
            Timeout(
                name="vstim",
                on_enter=["enter_vstim"],
                on_exit=["exit_vstim"],
                timeout=self.session_info["lockout_length"],
                on_timeout=["start_reward_available"],
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
            ),

            # vacuum state: open vacuum for specified amount of time (right before trial ends)
            Timeout(
                name="vacuum",
                on_enter=["enter_vacuum"],
                on_exit=["exit_vacuum"],
                timeout=self.session_info["vacuum_length"],
                on_timeout=["start_assessment"],
            ),

            # assessment state: assess trial outcomes
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
                on_timeout=["return_to_standby_normal_iti"],
            ),
            # punishment iti state
            Timeout(
                name="punishment_iti",
                on_enter=["enter_punishment_iti"],
                on_exit=["exit_punishment_iti"],
                timeout=self.session_info["punishment_iti_length"],
                on_timeout=["return_to_standby_punishment_iti"],
            ),

        ]
        # can set later with task.machine.states['cue'].timeout etc.

        ########################################################################
        # list of possible transitions between states
        # format is: [event_name, source_state, destination_state]
        ########################################################################
        self.transitions = [
            # possible transitions
            ["trial_start_go", "standby", "initiation_go"],
            ["trial_start_ss", "standby", "initiation_ss"],
            ["start_vstim", "initiation_go", "vstim"],
            ["start_astim", "initiation_ss", "astim"],
            ["start_vstim_astim", "astim", "vstim"],
            ["start_reward_available", "vstim", "reward_available"],
            ["start_lick_count", "reward_available", "lick_count"],
            ["start_vacuum_from_reward_available", "reward_available", "vacuum"],
            ["start_vacuum_from_lick_count", "lick_count", "vacuum"],
            ["start_assessment", "vacuum", "assessment"],
            ["start_normal_iti", "assessment", "normal_iti"],
            ["start_punishment_iti", "assessment", "punishment_iti"],
            ["return_to_standby_normal_iti", "normal_iti", "standby"],
            ["return_to_standby_punishment_iti", "punishment_iti", "standby"],
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

        # establish parameters for plotting
        self.trial_list = list(range(0, self.session_info["number_of_trials"]))
        self.trial_outcome = ["" for o in range(self.session_info["number_of_trials"])]
        self.hit_count = [0 for o in range(self.session_info["number_of_trials"])]
        self.miss_count = [0 for o in range(self.session_info["number_of_trials"])]
        self.cr_count = [0 for o in range(self.session_info["number_of_trials"])]
        self.fa_count = [0 for o in range(self.session_info["number_of_trials"])]

    ########################################################################
    # functions called when state transitions occur
    ########################################################################
    def enter_standby(self):
        logging.info(str(time.time()) + ", entering standby")
        self.trial_running = False

    def exit_standby(self):
        logging.info(str(time.time()) + ", exiting standby")

    def enter_initiation_go(self):
        self.trial_running = True
        self.time_at_lick = np.array([])
        self.time_at_reward = -1  # default value of -1 if no reward is delivered
        self.trial_start_time = time.time()

        logging.info(str(time.time()) + ", entering initiation")
        self.time_enter_lick_count = -2  # default
        self.time_exit_lick_count = -1  # default

    def exit_initiation_go(self):
        logging.info(str(time.time()) + ", exiting initiation")

    def enter_initiation_ss(self):
        self.trial_running = True
        self.time_at_lick = np.array([])
        self.time_at_reward = -1  # default value of -1 if no reward is delivered
        self.trial_start_time = time.time()

        logging.info(str(time.time()) + ", entering initiation")
        self.time_enter_lick_count = -2  # default
        self.time_exit_lick_count = -1  # default

    def exit_initiation_ss(self):
        logging.info(str(time.time()) + ", exiting initiation")

    def enter_astim(self):
        logging.info(str(time.time()) + ", entering astim")
        self.box.sound1.on()
        time.sleep(0.01)
        self.box.sound1.off()
        self.time_astim_ON = time.time() - self.trial_start_time
        logging.info(str(time.time()) + ", astim ON")
        print("Stop signal ON!")

    def exit_astim(self):
        logging.info(str(time.time()) + ", exiting astim")

    def enter_vstim(self):
        logging.info(str(time.time()) + ", entering vstim")
        self.box.visualstim.show_grating(list(self.box.visualstim.gratings)[0])
        self.time_at_vstim_on = time.time() - self.trial_start_time
        # start the countdown of time since display of vstim, this is used as timeup to transition lick_count to vacuum
        self.countdown(3)

    def exit_vstim(self):
        logging.info(str(time.time()) + ", exiting vstim")

    def enter_reward_available(self):
        logging.info(str(time.time()) + ", entering reward_available")

    def exit_reward_available(self):
        logging.info(str(time.time()) + ", exiting reward_available")

    def enter_lick_count(self):
        self.time_enter_lick_count = time.time() - self.trial_start_time
        logging.info(str(time.time()) + ", entering lick_count")

    def exit_lick_count(self):
        self.time_exit_lick_count = time.time() - self.trial_start_time
        logging.info(str(time.time()) + ", exiting lick_count")

    def enter_vacuum(self):
        logging.info(str(time.time()) + ", entering vacuum")
        self.box.vacuum_on()
        self.time_at_vacON = time.time() - self.trial_start_time

    def exit_vacuum(self):
        logging.info(str(time.time()) + ", exiting vacuum")
        self.box.vacuum_off()
        self.time_at_vacOFF = time.time() - self.trial_start_time

    def enter_assessment(self):
        logging.info(str(time.time()) + ", entering assessment")

    def exit_assessment(self):
        logging.info(str(time.time()) + ", exiting assessment")

    def enter_normal_iti(self):
        logging.info(str(time.time()) + ", entering normal_iti")

    def exit_normal_iti(self):
        self.trial_end_time = time.time() - self.trial_start_time
        logging.info(str(time.time()) + ", exiting normal_iti")

    def enter_punishment_iti(self):
        logging.info(str(time.time()) + ", entering punishment_iti")

    def exit_punishment_iti(self):
        self.trial_end_time = time.time() - self.trial_start_time
        logging.info(str(time.time()) + ", exiting punishment_iti")

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

        print('vstim 3s countdown is up!')
        self.box.event_list.append("vstim 3s countdown is up!")

    ########################################################################
    # call the run() method repeatedly in a while loop in the run_ssrt_task_phase1_v1.py script
    # it will process all detected events from the behavior box (e.g.
    # licks, reward delivery, etc.) and trigger the appropriate state transitions
    ########################################################################
    def run_go_trial(self):

        # read in name of an event the box has detected
        if self.box.event_list:
            event_name = self.box.event_list.popleft()
        else:
            event_name = ""

        if event_name == "left_IR_entry":
            self.time_at_lick = np.append(self.time_at_lick, time.time() - self.trial_start_time)

        if self.state == "standby":
            pass

        elif self.state == "initiation_go":
            self.start_vstim()

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

        elif self.state == "assessment":
            self.start_normal_iti()

        elif self.state == "normal_iti":
            pass

        # look for keystrokes
        # self.box.check_keybd()


    def run_ss_trial(self):

        # read in name of an event the box has detected
        if self.box.event_list:
            event_name = self.box.event_list.popleft()
        else:
            event_name = ""

        if event_name == "left_IR_entry":
            self.time_at_lick = np.append(self.time_at_lick, time.time() - self.trial_start_time)

        if self.state == "standby":
            pass

        elif self.state == "initiation_ss":
            self.start_astim()

        elif self.state == "astim":
            pass

        elif self.state == "vstim":
            pass

        elif self.state == "reward_available":
            if event_name == "left_IR_entry":
                self.temp_outcome = "FA !!!"
                self.start_lick_count()
            else:
                self.temp_outcome = "CR!"
                pass

        elif self.state == "lick_count":
            if event_name == "vstim 3s countdown is up!":
                self.start_vacuum_from_lick_count()

        elif self.state == "vacuum":
            pass

        elif self.state == "assessment":
            if self.temp_outcome == "FA !!!":
                self.start_punishment_iti()
            elif self.temp_outcome == "CR!":
                self.start_normal_iti()

        elif self.state == "normal_iti":
            pass

        elif self.state == "punishment_iti":
            pass
    ########################################################################
    # function for plotting
    ########################################################################

    # this function plots event_plot using matplotlib and pygame
    # will be updated at the end of each trial during standby period

    # call this method to launch plotting in a separate process

    def plot_ssrt_phase2(self, current_trial, trial_ident):

        ########################################################################
        # initialize the figure
        ########################################################################
        fig = plt.figure(figsize=(11, 7))
        ax1 = fig.add_subplot(231)  # outcome
        ax2 = fig.add_subplot(212)  # eventplot
        ax3 = fig.add_subplot(232)
        ax4 = fig.add_subplot(233)

        ########################################################################
        # create an outcome plot
        ########################################################################
        if trial_ident == "stop_signal_trial":
            self.trial_outcome[current_trial] = self.temp_outcome
            lick_events = self.time_at_lick
        elif trial_ident == "go_trial":
            lick_events = self.time_at_lick
            i, j = self.time_enter_lick_count, self.time_exit_lick_count
            self.trial_outcome[current_trial] = "Miss !!!"
            if lick_events.size == 0:
                self.trial_outcome[current_trial] = "Miss !!!"
            else:
                for ele in lick_events:
                    if i < ele < j:
                        self.trial_outcome[current_trial] = "Hit!"
                        break

        self.hit_count[current_trial] = self.trial_outcome.count("Hit!")
        self.miss_count[current_trial] = self.trial_outcome.count("Miss !!!")
        self.cr_count[current_trial] = self.trial_outcome.count("CR!")
        self.fa_count[current_trial] = self.trial_outcome.count("FA !!!")

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
                f"trial {self.trial_list[14]} : {self.trial_outcome[14]}",
                f" "))

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
                f"trial {self.trial_list[14 + (current_trial - 14)]} : {self.trial_outcome[14 + (current_trial - 14)]}",
                f" "))

        ax1.set_title('Trial Outcome', fontsize=11)
        ax1.text(0.05, 0.95, textstr, fontsize=9, verticalalignment='top')
        ax1.set_xticklabels([])
        ax1.set_xticks([])
        ax1.set_yticks([])
        ax1.set_yticklabels([])

        ########################################################################
        # create eventplot (vertical)
        ########################################################################
        # create a 2D array for eventplot
        events_to_plot = [lick_events, [self.time_at_reward]]
        plot_bin_number = 800  # bin number for plotting vstim, init, and astim
        plot_period = 8  # in seconds, plot for _s since the start of trial

        # create vstim time data
        vstim_duration = 3  # in seconds, pre-generated
        vstim_bins = plot_bin_number  # number of bins
        time_vstim_on = self.time_at_vstim_on
        time_vstim_index_on = int(round(time_vstim_on * vstim_bins/plot_period))
        time_vstim_index_off = int(time_vstim_index_on + round(vstim_duration*(vstim_bins/plot_period)))
        vstim_plot_data_x = np.linspace(0, plot_period, num=vstim_bins)
        vstim_plot_data_y = np.zeros(vstim_bins) - 1
        range_of_vstim_on = int(time_vstim_index_off - time_vstim_index_on)
        vstim_plot_data_y[time_vstim_index_on:time_vstim_index_off] = np.zeros(range_of_vstim_on) - 0.2

        # create astim time data
        astim_duration = 4  # in seconds, pre-generated
        astim_bins = plot_bin_number  # number of bins
        if trial_ident == "go_trial":
            astim_plot_data_x = np.linspace(0, plot_period, num=astim_bins)
            astim_plot_data_y = np.zeros(astim_bins)
        elif trial_ident == "stop_signal_trial":
            time_astim_on = self.time_astim_ON
            time_astim_index_on = int(round(time_astim_on * astim_bins / plot_period))
            time_astim_index_off = int(time_astim_index_on + round(astim_duration * (astim_bins / plot_period)))
            astim_plot_data_x = np.linspace(0, plot_period, num=astim_bins)
            astim_plot_data_y = np.zeros(astim_bins)
            range_of_astim_on = int(time_astim_index_off - time_astim_index_on)
            astim_plot_data_y[time_astim_index_on:time_astim_index_off] = np.zeros(range_of_astim_on) + 0.8

        # create vacuum time data
        vac_bins = plot_bin_number  # number of bins
        time_vac_on = self.time_at_vacON
        time_vac_off = self.time_at_vacOFF
        time_vac_index_on = int(round(time_vac_on * vac_bins / plot_period))
        time_vac_index_off = int(time_vac_index_on + round((time_vac_off - time_vac_on) * (vac_bins / plot_period)))
        vac_plot_data_x = np.linspace(0, plot_period, num=vac_bins)
        vac_plot_data_y = np.zeros(vac_bins) - 2
        range_of_vac_on = int(time_vac_index_off - time_vac_index_on)
        vac_plot_data_y[time_vac_index_on:time_vac_index_off] = np.zeros(range_of_vac_on) - 1.2

        # set different colors for each set of positions
        colors1 = ['C{}'.format(i) for i in range(2)]
        # set different line properties for each set of positions
        lineoffsets1 = np.array([3, 2])
        linelengths1 = [0.8, 0.8]
        ax2.eventplot(events_to_plot, colors=colors1, lineoffsets=lineoffsets1, linelengths=linelengths1)
        ax2.plot(vstim_plot_data_x, vstim_plot_data_y)
        ax2.plot(vac_plot_data_x, vac_plot_data_y)
        ax2.plot(astim_plot_data_x, astim_plot_data_y)
        ax2.set_xlim([-0.5, 8.5])  # 8s total to show (trial duration)
        ax2.set_xlabel('Time since trial start (s)', fontsize=9)
        ax2.set_yticks((-2, -1, 0.4, 2, 3))
        ax2.set_yticklabels(('vac', 'vstim', 'astim', 'reward', 'lick'))

        ########################################################################
        # create cummulative outcome plot
        ########################################################################
        # Get data to plot for current trial
        outcome_xvalue = np.linspace(0, current_trial, num=current_trial+1)
        outcome_hit_count_yvalue = self.hit_count[0:current_trial+1]
        outcome_miss_count_yvalue = self.miss_count[0:current_trial+1]
        outcome_cr_count_yvalue = self.cr_count[0:current_trial + 1]
        outcome_fa_count_yvalue = self.fa_count[0:current_trial + 1]

        # Plot
        ax3.plot(outcome_xvalue, outcome_hit_count_yvalue, 'r-')
        ax3.lines[-1].set_label('Hit')
        ax3.plot(outcome_xvalue, outcome_miss_count_yvalue, 'b-')
        ax3.lines[-1].set_label('Miss')
        ax3.plot(outcome_xvalue, outcome_cr_count_yvalue, 'c-')
        ax3.lines[-1].set_label('CR')
        ax3.plot(outcome_xvalue, outcome_fa_count_yvalue, 'm-')
        ax3.lines[-1].set_label('FA')

        ax3.set_title('Cummulative outcome', fontsize=11)
        ax3.set_xlim([0, current_trial+1])
        ax3.set_xlabel('Current trial', fontsize=9)
        ax3.set_ylabel('Number of trials', fontsize=9)
        ax3.legend()

        ########################################################################
        # create the fourth figure
        ########################################################################



        ########################################################################
        # draw on canvas
        ########################################################################
        canvas = agg.FigureCanvasAgg(fig)
        canvas.draw()
        renderer = canvas.get_renderer()
        raw_data = renderer.tostring_rgb()
        pygame.init()
        window = pygame.display.set_mode((1100, 700), DOUBLEBUF)
        screen = pygame.display.get_surface()
        size = canvas.get_width_height()
        surf = pygame.image.fromstring(raw_data, size, "RGB")
        screen.blit(surf, (0, 0))
        pygame.display.flip()

        # Reset self.time_at_reward to be out of range of plotting
        # This prevents the time_at_reward to be carried over to the next trial
        self.time_at_reward = -1
        self.time_enter_lick_count = -2
        self.time_exit_lick_count = -1
        plt.close(fig)

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