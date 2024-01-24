import logging
import time
from typing import List, Tuple, Protocol
from abc import ABC, abstractmethod
from icecream import ic
from transitions import State, Machine
from transitions.extensions.states import add_state_features, Timeout

"""
Abstract base class for use with the Presenter of the behavbox model-view-presenter.
"""


class Pump(Protocol):
    def reward(self, pump_key: str, reward_size: float):
        ...


class Task(Protocol):
    event_list: List[str]
    automate_training_rewards: bool
    give_training_reward: bool

    def switch_to_timeout(self):
        ...


class GUI(Protocol):
    keyboard_active: bool


class Box(Protocol):
    def video_start(self):
        ...

    def video_stop(self):
        ...


@add_state_features(Timeout)
class TimedStateMachine(Machine):
    pass


class Presenter(ABC):

    interact_list: List[Tuple[float, str]]
    pump: Pump
    task: Task
    gui: GUI
    session_info: dict
    box: Box

    def deliver_reward(self, pump_key: str, reward_size: int) -> None:
        self.pump.reward(pump_key, reward_size)
        # self.task.switch_to_timeout()

    def left_entry(self) -> None:
        self.task.event_list.append("left_entry")
        self.interact_list.append((time.time(), "left_entry"))
        logging.info(";" + str(time.time()) + ";[action];left_entry")

    def center_entry(self) -> None:
        self.task.event_list.append("center_entry")
        self.interact_list.append((time.time(), "center_entry"))
        logging.info(";" + str(time.time()) + ";[action];center_entry")

    def right_entry(self) -> None:
        self.task.event_list.append("right_entry")
        self.interact_list.append((time.time(), "right_entry"))
        logging.info(";" + str(time.time()) + ";[action];right_entry")

    def left_exit(self) -> None:
        self.task.event_list.append("left_exit")
        self.interact_list.append((time.time(), "left_exit"))
        logging.info(";" + str(time.time()) + ";[action];left_exit")

    def center_exit(self) -> None:
        self.task.event_list.append("center_exit")
        self.interact_list.append((time.time(), "center_exit"))
        logging.info(";" + str(time.time()) + ";[action];center_exit")

    def right_exit(self) -> None:
        self.task.event_list.append("right_exit")
        self.interact_list.append((time.time(), "right_exit"))
        logging.info(";" + str(time.time()) + ";[action];right_exit")

    def IR_1_entry(self) -> None:
        self.task.event_list.append("IR_1_entry")
        logging.info(str(time.time()) + ", IR_1_entry")

    def IR_2_entry(self) -> None:
        self.task.event_list.append("IR_2_entry")
        logging.info(str(time.time()) + ", IR_2_entry")

    def IR_3_entry(self) -> None:
        self.task.event_list.append("IR_3_entry")
        logging.info(str(time.time()) + ", IR_3_entry")

    def IR_4_entry(self) -> None:
        self.task.event_list.append("IR_4_entry")
        logging.info(str(time.time()) + ", IR_4_entry")

    def IR_5_entry(self) -> None:
        self.task.event_list.append("IR_5_entry")
        logging.info(str(time.time()) + ", IR_5_entry")

    def IR_1_exit(self) -> None:
        self.task.event_list.append("IR_1_exit")
        logging.info(str(time.time()) + ", IR_1_exit")

    def IR_2_exit(self) -> None:
        self.task.event_list.append("IR_2_exit")
        # self.cueLED2.off()
        logging.info(str(time.time()) + ", IR_2_exit")

    def IR_3_exit(self) -> None:
        self.task.event_list.append("IR_3_exit")
        logging.info(str(time.time()) + ", IR_3_exit")

    def IR_4_exit(self) -> None:
        self.task.event_list.append("IR_4_exit")
        logging.info(str(time.time()) + ", IR_4_exit")

    def IR_5_exit(self) -> None:
        self.task.event_list.append("IR_5_exit")
        logging.info(str(time.time()) + ", IR_5_exit")

    def K_escape_callback(self) -> None:
        self.gui.keyboard_active = False

    def K_1_down_callback(self) -> None:
        # left entry
        logging.info(";" + str(time.time()) + ";[action];key_pressed_left_entry()")
        self.left_entry()

    def K_2_down_callback(self) -> None:
        # center entry
        logging.info(";" + str(time.time()) + ";[action];key_pressed_center_entry()")
        self.center_entry()

    def K_3_down_callback(self) -> None:
        # right entry
        logging.info(";" + str(time.time()) + ";[action];key_pressed_right_entry()")
        self.right_entry()

    def K_1_up_callback(self) -> None:
        logging.info(";" + str(time.time()) + ";[action];key_released_left_entry()")
        self.left_exit()

    def K_2_up_callback(self) -> None:
        logging.info(";" + str(time.time()) + ";[action];key_released_center_entry()")
        self.center_exit()

    def K_3_up_callback(self) -> None:
        logging.info(";" + str(time.time()) + ";[action];key_released_right_entry()")
        self.right_exit()

    def K_q_callback(self) -> None:
        # print("Q down: syringe pump 1 moves")
        logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump1")
        self.pump.reward("key_1", self.session_info["key_reward_amount"])

    def K_w_callback(self) -> None:
        # print("W down: syringe pump 2 moves")
        logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump2")
        self.pump.reward("key_2", self.session_info["key_reward_amount"])

    def K_e_callback(self) -> None:
        # print("E down: syringe pump 3 moves")
        # logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump3")
        # self.pump.reward("key_3", self.session_info["key_reward_amount"])
        pass

    def K_r_callback(self) -> None:
        # print("R down: syringe pump 4 moves")
        # logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump4")
        # self.pump.reward("key_4", self.session_info["key_reward_amount"])
        pass

    def K_t_callback(self) -> None:
        # print("T down: vacuum on")
        # logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump_vacuum")
        # self.pump.reward("key_vacuum", 1)
        pass

    def K_a_callback(self) -> None:
        # toggle automated training rewards
        self.task.automate_training_rewards = not self.task.automate_training_rewards

    def K_g_callback(self) -> None:
        # give training reward
        self.task.give_training_reward = True
        logging.info(";" + str(time.time()) + ";[action];set_give_reward_true")

    def print_controls(self) -> None:
        print("[***] KEYBOARD CONTROLS [***]")
        print("1, 2, 3: left/center/right nosepoke entry")
        print("q, w, e, r, t: pump 1/2/3/4 reward delivery")
        print("a: toggle automated training rewards")
        print("g: give training reward")

    def start_session(self) -> None:
        ic("TODO: start video")
        self.box.video_start()

    def end_session(self) -> None:
        ic("TODO: stop video")
        self.box.video_stop()
        self.update_plot(save_fig=True)

    @abstractmethod
    def run(self) -> None:
        ...

    @abstractmethod
    def update_plot(self, save_fig=False) -> None:
        ...
