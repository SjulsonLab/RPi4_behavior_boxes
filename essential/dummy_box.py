from typing import Protocol
import logging
import time


class LED:
    def __init__(self):
        self.is_on: bool = False

    def blink(self, on_time: float, off_time: float, iteration: int):
        pass

    def on(self):
        self.is_on = True

    def off(self):
        self.is_on = False


class BehavBox:

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


class Pump(object):
    def __init__(self, session_info):
        pass

    def reward(self, which_pump, reward_size):
        duration = "n/a"
        coefficient = "n/a"
        duration_vac = "n/a"

        if which_pump == "1":
            logging.info(";" + str(time.time()) + ";[reward];pump1_reward(reward_coeff: " + str(coefficient) +
                         ", reward_amount: " + str(reward_size) + "duration: " + str(duration) + ")")
        elif which_pump == "2":
            logging.info(";" + str(time.time()) + ";[reward];pump2_reward(reward_coeff: " + str(coefficient) +
                         ", reward_amount: " + str(reward_size) + "duration: " + str(duration) + ")")
        elif which_pump == "3":
            logging.info(";" + str(time.time()) + ";[reward];pump3_reward(reward_coeff: " + str(coefficient) +
                         ", reward_amount: " + str(reward_size) + "duration: " + str(duration) + ")")
        elif which_pump == "4":
            logging.info(";" + str(time.time()) + ";[reward];pump4_reward(reward_coeff: " + str(coefficient) +
                         ", reward_amount: " + str(reward_size) + "duration: " + str(duration) + ")")
        elif which_pump == "air_puff":
            logging.info(";" + str(time.time()) + ";[reward];pump4_reward_" + str(reward_size))
        elif which_pump == "vacuum":
            logging.info(";" + str(time.time()) + ";[reward];pump_vacuum" + str(duration_vac))
        elif which_pump == "key_1":
            logging.info(";" + str(time.time()) + ";[key];pump1_reward(reward_coeff: " + str(coefficient) +
                         ", reward_amount: " + str(reward_size) + "duration: " + str(duration) + ")")
        elif which_pump == "key_2":
            logging.info(";" + str(time.time()) + ";[key];pump2_reward(reward_coeff: " + str(coefficient) +
                         ", reward_amount: " + str(reward_size) + "duration: " + str(duration) + ")")
        elif which_pump == "key_3":
            logging.info(";" + str(time.time()) + ";[key];pump3_reward(reward_coeff: " + str(coefficient) +
                         ", reward_amount: " + str(reward_size) + "duration: " + str(duration) + ")")
        elif which_pump == "key_4":
            logging.info(";" + str(time.time()) + ";[key];pump4_reward(reward_coeff: " + str(coefficient) +
                         ", reward_amount: " + str(reward_size) + "duration: " + str(duration) + ")")
        elif which_pump == "key_air_puff":
            logging.info(";" + str(time.time()) + ";[key];pump4_reward_" + str(reward_size))
        elif which_pump == "key_vacuum":
            logging.info(";" + str(time.time()) + ";[key];pump_vacuum" + str(duration_vac))