import logging
import time
from typing import List, Tuple, Union, Dict
from abc import ABC, abstractmethod
from icecream import ic
from transitions import State, Machine
from transitions.extensions.states import add_state_features, Timeout
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines
import collections
import pygame
import threading
from multiprocessing import Process, Queue
from threading import Thread


class PumpBase(ABC):

    @abstractmethod
    def reward(self, pump_key: str, reward_size: float):
        ...

    @abstractmethod
    def blink(self, pump_key: str, on_time: float):
        ...

    @abstractmethod
    def toggle(self, pump_key: str):
        ...


class PerformanceFigure(ABC):
    figure: plt.Figure
    correct_line: matplotlib.lines.Line2D
    error_line: matplotlib.lines.Line2D
    reward_line: matplotlib.lines.Line2D
    state_text: plt.Text
    stimulus_text: plt.Text


class GUI(ABC):
    figure_window: PerformanceFigure

    @abstractmethod
    def check_plot(self, figure: plt.Figure=None, FPS: int=144, savefig: bool=False):
        ...


class VisualStimBase(ABC):

    gratings_on = False
    presenter_commands: Union[List[str], Queue]
    active_process: Union[Thread, Process, None]

    @abstractmethod
    def show_grating(self, grating_name: str):
        ...

    @abstractmethod
    def loop_grating(self, grating_name: str, duration: float):
        ...

    @abstractmethod
    def display_default_greyscale(self):
        ...

    def end_gratings_process(self):
        if self.active_process is not None:
            self.active_process.join()
        self.gratings_on = False


class Box(ABC):

    visualstim: VisualStimBase
    presenter_commands: List[str]
    # sound1: LED
    # sound2: LED

    @abstractmethod
    def video_start(self):
        ...

    @abstractmethod
    def video_stop(self):
        ...


# probably remove this
@add_state_features(Timeout)
class TimedStateMachine(Machine):
    pass


class Model(ABC):
    automate_training_rewards: bool
    give_training_reward: bool
    state: str

    event_list: List[str] = collections.deque()
    trial_choice_list: List[int] = []
    trial_correct_list: List[bool] = []
    trial_choice_times: List[float] = []
    trial_reward_given: List[bool] = []

    # Lick detection
    lick_threshold: int = 2
    lick_side_buffer: np.ndarray = np.zeros(2)
    error_count: int = 0
    rewards_earned_in_block: int = 0
    rewards_available_in_block: int = 0
    ITI: float
    ITI_active: bool
    ITI_thread: threading.Timer
    t_ITI_start: float

    presenter_commands: List[str] = []

    def determine_choice(self) -> str:
        """Determine whether there has been a choice to the left ports, right ports, or a switch."""

        sides_licked = np.sum(self.lick_side_buffer.astype(bool))  # get nonzero sides
        if sides_licked > 1:
            # made a switch, reset the counter
            self.lick_side_buffer *= 0
            choice = 'switch'
        elif np.amax(self.lick_side_buffer) >= self.lick_threshold:
            choice_ix = np.argmax(self.lick_side_buffer)  # either 0 or 1
            choice = ['right', 'left'][choice_ix]
            self.lick_side_buffer *= 0
        else:
            choice = ''  # no choice made/not enough licks
        return choice

    def log_correct_choice(self, choice: int, event_time: float, choice_side: str, reward_given: bool) -> None:
        logging.info(";" + str(time.time()) + ";[transition];correct_choice_{}_patch;reward_{}".format(choice_side, reward_given))
        self.trial_choice_list.append(choice)
        self.trial_choice_times.append(event_time)
        self.trial_correct_list.append(True)
        self.error_count = 0

    def log_incorrect_choice(self, choice: int, event_time: float, choice_side: str, reward_given: bool) -> None:
        logging.info(";" + str(time.time()) + ";[transition];wrong_choice_{}_patch;reward_{}".format(choice_side, reward_given))
        self.trial_choice_list.append(choice)
        self.trial_choice_times.append(event_time)
        self.trial_correct_list.append(False)
        self.error_count += 1

    def log_training_reward(self, choice_ix: int, event_time: float) -> None:
        self.trial_choice_list.append(choice_ix)
        self.trial_choice_times.append(event_time)
        self.trial_correct_list.append(False)
        self.error_count = 0

    def reset_counters(self) -> None:
        self.lick_side_buffer *= 0
        self.rewards_earned_in_block = 0
        self.error_count = 0
        self.event_list.clear()

    def activate_ITI(self):
        self.lick_side_buffer *= 0
        self.ITI_active = True
        t = threading.Timer(interval=self.ITI, function=self.end_ITI)
        self.t_ITI_start = time.perf_counter()
        t.start()
        self.ITI_thread = t

    def end_ITI(self):
        # ic(time.perf_counter() - self.t_ITI_start)
        self.lick_side_buffer *= 0
        self.ITI_active = False

    def enter_standby(self):  # This function should also call for updating the plot???
        logging.info(";" + str(time.time()) + ";[transition];enter_standby;" + str(""))
        self.event_list.clear()

    def exit_standby(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_standby;" + str(""))
        self.reset_counters()

    def exit_right_patch(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_right_active;" + str(""))

    def exit_left_patch(self):
        logging.info(";" + str(time.time()) + ";[transition];exit_left_active;" + str(""))

    def enter_right_patch(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_right_patch;" + str(""))
        print('entering right active')

    def enter_left_patch(self):
        logging.info(";" + str(time.time()) + ";[transition];enter_left_patch;" + str(""))
        print('entering left active')

    @abstractmethod
    def give_correct_reward(self) -> bool:
        ...

    @abstractmethod
    def give_incorrect_reward(self) -> bool:
        ...

    @abstractmethod
    def run_event_loop(self):
        ...

    @abstractmethod
    def start_task(self):
        ...


class Presenter(ABC):
    keyboard_active: bool = True
    # interact_list: List[Tuple[float, str]]
    pump: PumpBase
    task: Model
    gui: GUI
    session_info: Dict
    box: Box

    def deliver_reward(self, pump_key: str, reward_size: int) -> None:
        self.pump.reward(pump_key, reward_size)
        # self.task.switch_to_timeout()

    def left_entry(self) -> None:
        self.task.event_list.append("left_entry")
        logging.info(";" + str(time.time()) + ";[action];left_entry;")

    def center_entry(self) -> None:
        self.task.event_list.append("center_entry")
        logging.info(";" + str(time.time()) + ";[action];center_entry;")

    def right_entry(self) -> None:
        self.task.event_list.append("right_entry")
        logging.info(";" + str(time.time()) + ";[action];right_entry;")

    def left_exit(self) -> None:
        self.task.event_list.append("left_exit")
        logging.info(";" + str(time.time()) + ";[action];left_exit;")

    def center_exit(self) -> None:
        self.task.event_list.append("center_exit;")
        logging.info(";" + str(time.time()) + ";[action];center_exit;")

    def right_exit(self) -> None:
        self.task.event_list.append("right_exit")
        logging.info(";" + str(time.time()) + ";[action];right_exit;")

    def IR_1_entry(self) -> None:
        self.task.event_list.append("IR_1_entry")
        logging.info(str(time.time()) + ", IR_1_entry;")

    def IR_2_entry(self) -> None:
        self.task.event_list.append("IR_2_entry")
        logging.info(str(time.time()) + ", IR_2_entry;")

    def IR_3_entry(self) -> None:
        self.task.event_list.append("IR_3_entry")
        logging.info(str(time.time()) + ", IR_3_entry;")

    def IR_4_entry(self) -> None:
        self.task.event_list.append("IR_4_entry")
        logging.info(str(time.time()) + ", IR_4_entry;")

    def IR_5_entry(self) -> None:
        self.task.event_list.append("IR_5_entry")
        logging.info(str(time.time()) + ", IR_5_entry;")

    def IR_1_exit(self) -> None:
        self.task.event_list.append("IR_1_exit")
        logging.info(str(time.time()) + ", IR_1_exit;")

    def IR_2_exit(self) -> None:
        self.task.event_list.append("IR_2_exit")
        # self.cueLED2.off()
        logging.info(str(time.time()) + ", IR_2_exit;")

    def IR_3_exit(self) -> None:
        self.task.event_list.append("IR_3_exit")
        logging.info(str(time.time()) + ", IR_3_exit;")

    def IR_4_exit(self) -> None:
        self.task.event_list.append("IR_4_exit")
        logging.info(str(time.time()) + ", IR_4_exit;")

    def IR_5_exit(self) -> None:
        self.task.event_list.append("IR_5_exit")
        logging.info(str(time.time()) + ", IR_5_exit;")

    def K_escape_callback(self) -> None:
        pass
        # self.gui.keyboard_active = False

    def K_1_down_callback(self) -> None:
        # left entry
        logging.info(";" + str(time.time()) + ";[action];key_pressed_left_entry();")
        self.left_entry()

    def K_2_down_callback(self) -> None:
        # center entry
        logging.info(";" + str(time.time()) + ";[action];key_pressed_center_entry();")
        self.center_entry()

    def K_3_down_callback(self) -> None:
        # right entry
        logging.info(";" + str(time.time()) + ";[action];key_pressed_right_entry();")
        self.right_entry()

    def K_1_up_callback(self) -> None:
        logging.info(";" + str(time.time()) + ";[action];key_released_left_entry();")
        self.left_exit()

    def K_2_up_callback(self) -> None:
        logging.info(";" + str(time.time()) + ";[action];key_released_center_entry();")
        self.center_exit()

    def K_3_up_callback(self) -> None:
        logging.info(";" + str(time.time()) + ";[action];key_released_right_entry();")
        self.right_exit()

    def K_q_callback(self) -> None:
        # print("Q down: syringe pump 1 moves")
        logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump1;")
        self.pump.reward("key_1", self.session_info["key_reward_amount"])

    def K_w_callback(self) -> None:
        # print("W down: syringe pump 2 moves")
        logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump2;")
        self.pump.reward("key_2", self.session_info["key_reward_amount"])

    def K_e_callback(self) -> None:
        # print("E down: syringe pump 3 moves")
        logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump3;")
        self.pump.reward("key_3", self.session_info["key_reward_amount"])

    def K_r_callback(self) -> None:
        # print("R down: syringe pump 4 moves")
        logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump4;")
        self.pump.reward("key_4", self.session_info["key_reward_amount"])

    def K_t_callback(self) -> None:
        # print("T down: vacuum on")
        logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump_vacuum;")
        self.pump.reward("key_vacuum", 1)

    def K_a_callback(self) -> None:
        # toggle automated training rewards
        self.task.automate_training_rewards = not self.task.automate_training_rewards

    def K_g_callback(self) -> None:
        # give training reward
        self.task.give_training_reward = True
        logging.info(";" + str(time.time()) + ";[action];set_give_reward_true;")

    def K_l_callback(self) -> None:
        pass

    def K_z_callback(self) -> None:
        pass

    def K_x_callback(self) -> None:
        pass

    def K_b_callback(self) -> None:
        pass

    def K_v_callback(self) -> None:
        pass

    def K_d_callback(self) -> None:
        pass

    def K_f_callback(self) -> None:
        pass

    def print_controls(self) -> None:
        print("[***] KEYBOARD CONTROLS [***]")
        print("1, 2, 3: left/center/right nosepoke entry")
        print("q, w, e, r: pump 1/2/3/4 reward delivery")
        print("t: vacuum activation")
        print("a: toggle automated training rewards")
        print("g: give training reward")

    def check_keyboard(self):
        if self.keyboard_active:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.K_escape_callback()

                    # lick port interaction buttons
                    elif event.key == pygame.K_1:
                        self.K_1_down_callback()
                    elif event.key == pygame.K_2:
                        self.K_2_down_callback()
                    elif event.key == pygame.K_3:
                        self.K_3_down_callback()

                    # interactive training functions
                    elif event.key == pygame.K_q:
                        self.K_q_callback()
                    elif event.key == pygame.K_w:
                        self.K_w_callback()
                    elif event.key == pygame.K_e:
                        self.K_e_callback()
                    elif event.key == pygame.K_r:
                        self.K_r_callback()
                    elif event.key == pygame.K_t:
                        self.K_t_callback()
                    elif event.key == pygame.K_a:
                        self.K_a_callback()
                    elif event.key == pygame.K_g:
                        self.K_g_callback()
                    elif event.key == pygame.K_l:
                        self.K_l_callback()
                    elif event.key == pygame.K_z:
                        self.K_z_callback()
                    elif event.key == pygame.K_x:
                        self.K_x_callback()
                    elif event.key == pygame.K_b:
                        self.K_b_callback()
                    elif event.key == pygame.K_v:
                        self.K_v_callback()
                    elif event.key == pygame.K_d:
                        self.K_d_callback()
                    elif event.key == pygame.K_f:
                        self.K_f_callback()

                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_1:
                        self.K_1_up_callback()
                    elif event.key == pygame.K_2:
                        self.K_2_up_callback()
                    elif event.key == pygame.K_3:
                        self.K_3_up_callback()

    def start_session(self) -> None:
        ic("TODO: start video")
        self.box.video_start()

    def end_session(self) -> None:
        ic("TODO: stop video")
        self.box.video_stop()
        if self.gui:
            self.update_plot(save_fig=True)

    def update_plot(self, save_fig=False, n_plot=20) -> None:
        if self.task.trial_choice_list:
            correct_ix = np.array(self.task.trial_correct_list)[-n_plot:]
            reward_ix = np.array(self.task.trial_reward_given)[-n_plot:]
            choices = np.array(self.task.trial_choice_list)[-n_plot:]
            times = np.array(self.task.trial_choice_times)[-n_plot:]

            correct_trials = choices[correct_ix]
            correct_times = times[correct_ix]

            incorrect_trials = choices[~correct_ix]
            incorrect_times = times[~correct_ix]

            reward_trials = choices[reward_ix]
            reward_times = times[reward_ix]

            self.gui.figure_window.correct_line.set_data(correct_times, correct_trials)
            self.gui.figure_window.error_line.set_data(incorrect_times, incorrect_trials)
            self.gui.figure_window.reward_line.set_data(reward_times, reward_trials)

            # update this to show the last 20-ish trials
            if times.size > 1:
                T = [times[-n_plot:][0], times[-1]]
            else:
                T = [times[-1] - .5, times[-1] + .5]
            plt.xlim(T)

        self.gui.figure_window.state_text.set_text('State: {}; ITI: {}'.format(self.task.state,
                                                                               self.task.ITI_active))
        self.gui.check_plot(figure=self.gui.figure_window.figure, savefig=save_fig)

    @abstractmethod
    def run(self) -> None:
        ...
