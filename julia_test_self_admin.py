# add in all the imports etc
# !/usr/bin/env python
# coding: utf-8
# In[ ]:
# python3: JB_Cocaine_Cue_Learning.py
"""
author: Julia Benville
date: 2024-08-05
name: JB_Cocaine_Cue_Learning.py (adapted from remi_self_admin_lever_task.py)
"""
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
import threading
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.figure as fg
import numpy as np

# from IPython.display import display, HTML
#
# display(HTML("<style>.container { width:100% !important; }</style>"))
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


class CocaineSelfAdminLeverTask(object):
    # Define states. States where the animals is waited to make their decision
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
            from fake_session_info import fake_session_info
            self.session_info = fake_session_info
        else:
            self.session_info = kwargs.get("session_info", None)
        ic(self.session_info)
    # initialize the state for DRUG CUE LEARNING ONLY
        self.states = [
        State(name='standby',
          on_enter=['switch_to_reward_available'],
          on_exit=["exit_standby"]),
        State(name="reward_available",
          on_enter=["enter_reward_available"],
          on_exit=["exit_reward_available"]),
        Timeout(name='timeout',
            on_enter=['enter_timeout'],
            on_exit=['exit_timeout'],
            timeout=self.session_info['timeout_time'],
            on_timeout=['switch_to_reward_available'])]
# kept these the same unclear how to edit?
        self.transitions = [
    ['start_trial_logic', 'standby', 'reward_available'],  # format: ['trigger', 'origin', 'destination']
    ['switch_to_standby', 'reward_available', 'standby'],
    ['switch_to_reward_available', ['standby', 'timeout'], 'reward_available'],
    ['switch_to_timeout', 'reward_available', 'timeout'],
    ['end_task', ['reward_available', 'timeout'], 'standby']]
        self.machine = TimedStateMachine(
    model=self,
    states=self.states,
    transitions=self.transitions,
    initial='standby')

        # trial statistics
        self.trial_running = False
        self.innocent = True
        self.trial_number = 0
        self.error_count = 0
        self.error_list = []
        self.error_repeat = False
        self.entry_time = 0.0
        self.entry_interval = self.session_info[
            "entry_interval"]  # update lever_press_interval to entry_interval--make this 3s instead of 1s
        self.reward_time = 10
        self.reward_times_up = False
        self.reward_pump1 = self.session_info["reward_pump1"]
        self.reward_pump2 = self.session_info['reward_pump2']
        self.DCL_time = 0  # changed from two contexts to this? just drug cue learning
        self.active_press = 0
        self.inactive_press = 0
        self.timeline_active_press = []
        self.active_press_count_list = []
        self.timeline_inactive_press = []
        self.inactive_press_count_list = []
        self.timeline_left_poke = []
        self.timeline_right_poke = []
        # initialize behavior box
        self.box = behavbox.BehavBox(self.session_info)
        self.pump = self.box.pump
        self.syringe_pump = LED(17)
        self.treadmill = self.box.treadmill
        # for refining the lick detection REMOVING
        self.reward_list = []
        self.left_poke_count_list = []
        self.right_poke_count_list = []
        # session_statistics
        self.total_reward = 0

    def reward(self):  # prototype mouse weight equals 30
        infusion_duration = (self.session_info['weight'] / 30) #6.25 uL for a 30g mouse
        self.syringe_pump.blink(2*infusion_duration, 0.1, 1) #2 second infusion duration for 6.25 ul (hence 2*)
        self.reward_list.append(("syringe_pump_reward", 2*infusion_duration))
        logging.info(";" + str(time.time()) + ";[reward];syringe_pump_reward" + str(2*infusion_duration))

    def fill_cath(self):
        self.syringe_pump.blink(3.76, 0.1, 1) #3.125ul/second, calculated cath holds ~11.74ul; 3.76 seconds delivers ~12ul into cath; will need to update based on instech catheters
        logging.info(";" + str(time.time()) + ";[reward];catheter_filled_with_~12ul;" + '3.76_second_infusion')

    def run(self):
        if self.state == "standby" or self.state == 'timeout':
            pass
        elif self.state == 'reward_available':
            if self.box.event_list:
                self.event_name = self.box.event_list.popleft()
            else:
                self.event_name = ''
            if self.event_name == 'right_entry' or 'reserved_rx1_pressed':
                self.reward()
                self.switch_to_timeout()
        self.box.check_keybd()

    def enter_standby(self):
        # self.error_repeat = False
        logging.info(";" + str(time.time()) + ";[transition];enter_standby;")
        self.trial_running = False
        self.box.event_list.clear()

    def exit_standby(self):
        # self.error_repeat = False
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;")
        self.box.event_list.clear()
        self.fill_cath()

    def enter_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_reward_available;")
        self.box.cueLED2.on()
        self.trial_running = True

    def exit_reward_available(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_reward_available;")
        self.box.cueLED2.off()
        self.box.event_list.clear()

    def enter_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_timeout;")
        self.trial_running = False
        self.box.sound2.on()
        self.box.event_list.clear()

    def exit_timeout(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_timeout;")
        self.box.sound2.off()
        self.box.event_list.clear()

    #duy_visualization code commented out below#
    # # import packages for starting a new process and plotting trial progress in real time
    # # RPi4 does not have a graphical interface, we use pygame with backends for plotting
    # import matplotlib
    # matplotlib.use("Agg")
    # import matplotlib.backends.backend_agg as agg
    # import matplotlib.pyplot as plt
    # import pygame
    # from pygame.locals import *
    # import numpy as np
    # from multiprocessing import Process, Value
    #
    # # all modules above this line will have logging disabled
    # logging.config.dictConfig({
    #     'version': 1,
    #     'disable_existing_loggers': True,
    # })
    #
    # if debug_enable:
    #     # enabling debugger
    #     from IPython import get_ipython
    #     ipython = get_ipython()
    #     ipython.magic("pdb on")
    #     ipython.magic("xmode Verbose")
    #
    # # import the go_nogo_task task class here
    # from go_nogo_task_phase2_final import go_nogo_phase2
    #
    # # define the plotting function here
    # def plot_trial_progress(current_trial, trial_list, combine_trial_outcome, hit_count, miss_count,
    #                         cr_count, fa_count, lick_times, vstimON_time, plot_dprime, dprimebinp):
    #     ########################################################################
    #     # initialize the figure
    #     ########################################################################
    #     fig = plt.figure(figsize=(14, 9))
    #     ax1 = fig.add_subplot(231)  # outcome
    #     ax2 = fig.add_subplot(212)  # eventplot
    #     ax3 = fig.add_subplot(232)
    #     ax4 = fig.add_subplot(233)
    #
    #     ########################################################################
    #     # create an outcome plot
    #     ########################################################################
    #     if current_trial < 14:
    #         textstr = '\n'.join((
    #             f"trial {trial_list[0]} : {combine_trial_outcome[0]}",
    #             f"trial {trial_list[1]} : {combine_trial_outcome[1]}",
    #             f"trial {trial_list[2]} : {combine_trial_outcome[2]}",
    #             f"trial {trial_list[3]} : {combine_trial_outcome[3]}",
    #             f"trial {trial_list[4]} : {combine_trial_outcome[4]}",
    #             f"trial {trial_list[5]} : {combine_trial_outcome[5]}",
    #             f"trial {trial_list[6]} : {combine_trial_outcome[6]}",
    #             f"trial {trial_list[7]} : {combine_trial_outcome[7]}",
    #             f"trial {trial_list[8]} : {combine_trial_outcome[8]}",
    #             f"trial {trial_list[9]} : {combine_trial_outcome[9]}",
    #             f"trial {trial_list[10]} : {combine_trial_outcome[10]}",
    #             f"trial {trial_list[11]} : {combine_trial_outcome[11]}",
    #             f"trial {trial_list[12]} : {combine_trial_outcome[12]}",
    #             f"trial {trial_list[13]} : {combine_trial_outcome[13]}",
    #             f" ",
    #             f"percent hit : {round(((hit_count[current_trial] / (hit_count[current_trial] + miss_count[current_trial])) * 100), 1)}%",
    #             f" "))
    #
    #     elif current_trial >= 14:
    #         textstr = '\n'.join((
    #             f"trial {trial_list[0 + (current_trial - 13)]} : {combine_trial_outcome[0 + (current_trial - 13)]}",
    #             f"trial {trial_list[1 + (current_trial - 13)]} : {combine_trial_outcome[1 + (current_trial - 13)]}",
    #             f"trial {trial_list[2 + (current_trial - 13)]} : {combine_trial_outcome[2 + (current_trial - 13)]}",
    #             f"trial {trial_list[3 + (current_trial - 13)]} : {combine_trial_outcome[3 + (current_trial - 13)]}",
    #             f"trial {trial_list[4 + (current_trial - 13)]} : {combine_trial_outcome[4 + (current_trial - 13)]}",
    #             f"trial {trial_list[5 + (current_trial - 13)]} : {combine_trial_outcome[5 + (current_trial - 13)]}",
    #             f"trial {trial_list[6 + (current_trial - 13)]} : {combine_trial_outcome[6 + (current_trial - 13)]}",
    #             f"trial {trial_list[7 + (current_trial - 13)]} : {combine_trial_outcome[7 + (current_trial - 13)]}",
    #             f"trial {trial_list[8 + (current_trial - 13)]} : {combine_trial_outcome[8 + (current_trial - 13)]}",
    #             f"trial {trial_list[9 + (current_trial - 13)]} : {combine_trial_outcome[9 + (current_trial - 13)]}",
    #             f"trial {trial_list[10 + (current_trial - 13)]} : {combine_trial_outcome[10 + (current_trial - 13)]}",
    #             f"trial {trial_list[11 + (current_trial - 13)]} : {combine_trial_outcome[11 + (current_trial - 13)]}",
    #             f"trial {trial_list[12 + (current_trial - 13)]} : {combine_trial_outcome[12 + (current_trial - 13)]}",
    #             f"trial {trial_list[13 + (current_trial - 13)]} : {combine_trial_outcome[13 + (current_trial - 13)]}",
    #             f" ",
    #             f"percent hit : {round(((hit_count[current_trial] / (hit_count[current_trial] + miss_count[current_trial])) * 100), 1)}%",
    #             f" "))
    #
    #     ax1.set_title('Trial Outcome', fontsize=11)
    #     ax1.text(0.05, 0.95, textstr, fontsize=11, verticalalignment='top')
    #     ax1.set_xticklabels([])
    #     ax1.set_xticks([])
    #     ax1.set_yticks([])
    #     ax1.set_yticklabels([])
    #
    #     ########################################################################
    #     # create eventplot (vertical)
    #     ########################################################################
    #     # create a 2D array for eventplot
    #     events_to_plot = [lick_times, [reward_time]]
    #     if combine_trial_outcome[current_trial] == "FA !!!":
    #         plot_period = 7  # in seconds, how long to plot since the start of trial
    #         plot_bin_number = 800
    #     else:
    #         plot_period = 7
    #         plot_bin_number = 800
    #
    #     # create vstim time data
    #     vstim_duration = 3  # in seconds, pre-generated
    #     vstim_bins = plot_bin_number  # number of bins
    #     time_vstim_on = vstimON_time
    #     time_vstim_index_on = int(round(time_vstim_on * vstim_bins / plot_period))
    #     time_vstim_index_off = int(time_vstim_index_on + round(vstim_duration * (vstim_bins / plot_period)))
    #     vstim_plot_data_x = np.linspace(0, plot_period, num=vstim_bins)
    #     vstim_plot_data_y = np.zeros(vstim_bins) - 1
    #     range_of_vstim_on = int(time_vstim_index_off - time_vstim_index_on)
    #     vstim_plot_data_y[time_vstim_index_on:time_vstim_index_off] = np.zeros(range_of_vstim_on) - 0.2
    #
    #     # set different colors for each set of positions
    #     colors1 = ['C{}'.format(c) for c in range(2)]
    #     # set different line properties for each set of positions
    #     lineoffsets1 = np.array([3, 2])
    #     linelengths1 = [0.8, 0.8]
    #     ax2.eventplot(events_to_plot, colors=colors1, lineoffsets=lineoffsets1, linelengths=linelengths1)
    #     ax2.plot(vstim_plot_data_x, vstim_plot_data_y)
    #     ax2.set_xlim([-0.5, 7])  # 8s total to show (trial duration)
    #     ax2.set_xlabel('Time since trial start (s)', fontsize=9)
    #     ax2.set_yticks((-1, 2, 3))
    #     ax2.set_yticklabels(('vstim', 'reward', 'lick'))
    #
    #     ########################################################################
    #     # create cumulative outcome plot
    #     ########################################################################
    #     # Get data to plot for current trial
    #     outcome_xvalue = np.linspace(0, current_trial, num=current_trial + 1)
    #     outcome_hit_count_yvalue = hit_count[0:current_trial + 1]
    #     outcome_miss_count_yvalue = miss_count[0:current_trial + 1]
    #     outcome_cr_count_yvalue = cr_count[0:current_trial + 1]
    #     outcome_fa_count_yvalue = fa_count[0:current_trial + 1]
    #
    #     # Plot
    #     ax3.plot(outcome_xvalue, outcome_hit_count_yvalue, 'r-')
    #     ax3.lines[-1].set_label('Hit')
    #     ax3.plot(outcome_xvalue, outcome_miss_count_yvalue, 'b-')
    #     ax3.lines[-1].set_label('Miss')
    #     ax3.plot(outcome_xvalue, outcome_cr_count_yvalue, 'c-')
    #     ax3.lines[-1].set_label('CR')
    #     ax3.plot(outcome_xvalue, outcome_fa_count_yvalue, 'm-')
    #     ax3.lines[-1].set_label('FA')
    #
    #     ax3.set_title('Cummulative outcome', fontsize=11)
    #     ax3.set_xlim([0, current_trial + 1])
    #     ax3.set_xlabel('Current trial', fontsize=9)
    #     ax3.set_ylabel('Number of trials', fontsize=9)
    #     ax3.legend()
    #
    #     ########################################################################
    #     # create the d' figure
    #     ########################################################################
    #
    #     if plot_dprime == True:
    #         ax4_x_values = np.linspace(0, current_trial, num=current_trial + 1)
    #         ax4_y_values = dprimebinp[0:current_trial + 1]
    #         ax4.plot(ax4_x_values, ax4_y_values, 'r-')
    #         ax4.set_title('D-prime', fontsize=11)
    #         ax4.set_xlim([0, current_trial + 1])
    #         ax4.set_xlabel('Current trial', fontsize=9)
    #
    #     ########################################################################
    #     # draw on canvas to display via pygame
    #     ########################################################################
    #     canvas = agg.FigureCanvasAgg(fig)
    #     canvas.draw()
    #     renderer = canvas.get_renderer()
    #     raw_data = renderer.tostring_rgb()
    #     pygame.init()
    #     window = pygame.display.set_mode((1400, 900), DOUBLEBUF)
    #     screen = pygame.display.get_surface()
    #     size = canvas.get_width_height()
    #     surf = pygame.image.fromstring(raw_data, size, "RGB")
    #     screen.blit(surf, (0, 0))
    #     pygame.display.flip()
    #     plt.close(fig)
    #     time.sleep(3)  # sleep for 3 seconds for pygame to remain displayed
    #     pygame.quit()

    def update_plot(self):
        fig, axes = plt.subplots(1, 1, )
        axes.plot([1, 2], [1, 2], color='green', label='test')
        self.box.check_plot(fig)

    def update_plot_error(self):
        error_event = self.error_list
        labels, counts = np.unique(error_event, return_counts=True)
        ticks = range(len(counts))
        fig, ax = plt.subplots(1, 1, )
        ax.bar(ticks, counts, align='center', tick_label=labels)
        # plt.xticks(ticks, labels)
        # plt.title(session_name)
        ax = plt.gca()
        ax.set_xticks(ticks, labels)
        ax.set_xticklabels(labels=labels, rotation=70)
        self.box.check_plot(fig)


    def update_plot_choice(self, save_fig=False):
        trajectory_active = self.left_poke_count_list
        time_active = self.timeline_left_poke
        trajectory_inactive = self.right_poke_count_list
        time_inactive = self.timeline_right_poke
        fig, ax = plt.subplots(1, 1, )
        print(type(fig))
        ax.plot(time_active, trajectory_active, color='b', marker="o", label='active_trajectory')
        ax.plot(time_inactive, trajectory_inactive, color='r', marker="o", label='inactive_trajectory')
        if save_fig:
            plt.savefig(self.session_info['basedir'] + "/" + self.session_info['basename'] + "/" + self.session_info[
                'basename'] + "_lever_choice_plot" + '.png')
        self.box.check_plot(fig)
        ## not sure if the above is right with the licks?


    def integrate_plot(self, save_fig=False):
        fig, ax = plt.subplots(2, 1)
        trajectory_left = self.active_press
        time_active_press = self.timeline_active_press
        trajectory_right = self.right_poke_count_list
        time_inactive_press = self.timeline_inactive_press
        print(type(fig))
        ax[0].plot(time_active_press, trajectory_left, color='b', marker="o", label='left_lick_trajectory')
        ax[0].plot(time_inactive_press, trajectory_right, color='r', marker="o", label='right_lick_trajectory')
        error_event = self.error_list
        labels, counts = np.unique(error_event, return_counts=True)
        ticks = range(len(counts))
        ax[1].bar(ticks, counts, align='center', tick_label=labels)
        # plt.xticks(ticks, labels)
        # plt.title(session_name)
        ax[1] = plt.gca()
        ax[1].set_xticks(ticks, labels)
        ax[1].set_xticklabels(labels=labels, rotation=70)
        ########################################################################
        # methods to start and end the behavioral session
        ########################################################################

    def start_session(self):
        ic("TODO: start video")
        self.box.video_start()

    def end_session(self):
        ic("TODO: stop video")
        self.update_plot_choice(save_fig=True)
        self.box.video_stop()
        self.box.cueLED2.off()
        ##also unsure if the things above are correct with the licks?
        if save_fig:
            plt.savefig(self.session_info['basedir'] + "/" + self.session_info['basename'] + "/" + self.session_info[
                'basename'] + "_summery" + '.png')
        self.box.check_plot(fig)