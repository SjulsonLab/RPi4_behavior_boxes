import logging
import time
from typing import List, Tuple, Union
from essential.base_classes import Box, PumpBase, Presenter, Model, GUI
from threading import Timer, Thread
from icecream import ic


class LED:
    def __init__(self, pin: int = 0):
        self.is_on: bool = False
        self.pin: int = pin
        self.blink_thread = None
        self.blinking = False

    def blink_loop(self, on_time: float, off_time: float, n: int = None):
        """
        A while loop that blinks the LED on and off. If n is not None, it will blink n times.
        If n is None, it will blink indefinitely until a separate thread turns it off.
        """
        self.blinking = True
        while self.blinking:
            self.is_on = True
            time.sleep(on_time)
            self.is_on = False
            time.sleep(off_time)

            if n is not None:
                n -= 1

            if n == 0:
                self.blinking = False

    def blink(self, on_time: float, off_time: float, n: int):
        if self.blinking:
            ic("already blinking")
            return

        ic("starting blink")
        self.blink_thread = Thread(target=self.blink_loop, args=(on_time, off_time, n))
        self.blink_thread.start()

    def on(self):
        self.is_on = True

    def off(self):
        self.is_on = False
        self.blinking = False


class BehavBox(Box):

    cueLED1 = LED()
    cueLED2 = LED()

    def __init__(self, session_info):
        pass

    def set_callbacks(self, presenter):
        pass

    def video_start(self):
        pass

    def video_stop(self):
        pass


class Pump(PumpBase):
    def __init__(self, session_info):
        self.pump1 = LED(19)
        self.pump2 = LED(20)
        self.pump3 = LED(21)
        self.pump4 = LED(7)
        self.pump_air = LED(8)
        self.pump_vacuum = LED(25)

        # this needs to move to the controller
        # is this even used?
        self.reward_list = []  # a list of tuple (pump_x, reward_amount) with information of reward history for data

        self.coefficient_p1 = session_info["calibration_coefficient"]['1']
        self.coefficient_p2 = session_info["calibration_coefficient"]['2']
        self.coefficient_p3 = session_info["calibration_coefficient"]['3']
        self.coefficient_p4 = session_info["calibration_coefficient"]['4']
        self.duration_air = session_info['air_duration']
        self.duration_vac = session_info["vacuum_duration"]

    def reward(self, which_pump: str, reward_size: float) -> None:
        if which_pump in ["1", "key_1"]:
            duration = round((self.coefficient_p1[0] * (reward_size / 1000) + self.coefficient_p1[1]),
                             5)  # linear function
            logging.info(";" + str(time.time()) + ";[reward];pump1_reward(reward_coeff: " + str(self.coefficient_p1) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ")")
        elif which_pump in ["2", "key_2"]:
            duration = round((self.coefficient_p2[0] * (reward_size / 1000) + self.coefficient_p2[1]),
                             5)  # linear function
            logging.info(";" + str(time.time()) + ";[reward];pump2_reward(reward_coeff: " + str(self.coefficient_p2) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ")")
        elif which_pump in ["3", "key_3"]:
            duration = round((self.coefficient_p3[0] * (reward_size / 1000) + self.coefficient_p3[1]),
                             5)  # linear function
            logging.info(";" + str(time.time()) + ";[reward];pump3_reward(reward_coeff: " + str(self.coefficient_p3) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ")")
        elif which_pump in ["4", "key_4"]:
            duration = round((self.coefficient_p4[0] * (reward_size / 1000) + self.coefficient_p4[1]),
                             5)  # linear function
            logging.info(";" + str(time.time()) + ";[reward];pump4_reward(reward_coeff: " + str(self.coefficient_p4) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ")")
        elif which_pump in ["air_puff", "key_air_puff"]:
            logging.info(";" + str(time.time()) + ";[reward];pump_air" + str(reward_size))
        elif which_pump in ["vacuum", "key_vacuum"]:
            logging.info(";" + str(time.time()) + ";[reward];pump_vacuum" + str(self.duration_vac))

    def blink(self, pump_key: str, on_time: float) -> None:
        """Blink a pump-port once for testing purposes."""
        if pump_key in ["1", "key_1"]:
            self.pump1.blink(on_time=on_time, off_time=0.1, n=1)
            logging.info(";" + str(time.time()) + ";[reward];pump1_blink, duration: " + str(on_time) + ")")
        elif pump_key in ["2", "key_2"]:
            self.pump2.blink(on_time=on_time, off_time=0.1, n=1)
            logging.info(";" + str(time.time()) + ";[reward];pump2_blink, duration: " + str(on_time) + ")")
        elif pump_key in ["3", "key_3"]:
            self.pump3.blink(on_time=on_time, off_time=0.1, n=1)
            logging.info(";" + str(time.time()) + ";[reward];pump3_blink, duration: " + str(on_time) + ")")
        elif pump_key in ["4", "key_4"]:
            self.pump4.blink(on_time=on_time, off_time=0.1, n=1)
            logging.info(";" + str(time.time()) + ";[reward];pump4_blink, duration: " + str(on_time) + ")")
        elif pump_key in ["air_puff", "key_air_puff"]:
            self.pump_air.blink(on_time, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[reward];pump_air, duration: " + str(self.duration_air) + ")")
        elif pump_key in ["vacuum", "key_vacuum"]:
            self.pump_vacuum.blink(on_time, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[reward];pump_vacuum, duration: " + str(self.duration_vac) + ")")
