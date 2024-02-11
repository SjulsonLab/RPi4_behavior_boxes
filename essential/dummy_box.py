import logging
import time


class LED:
    def __init__(self, pin: int = 0):
        self.is_on: bool = False
        self.pin: int = pin

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

    def reward(self, which_pump, reward_size):
        if which_pump == "1":
            duration = round((self.coefficient_p1[0] * (reward_size / 1000) + self.coefficient_p1[1]),
                             5)  # linear function
            logging.info(";" + str(time.time()) + ";[reward];pump1_reward(reward_coeff: " + str(self.coefficient_p1) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ")")
        elif which_pump == "2":
            duration = round((self.coefficient_p2[0] * (reward_size / 1000) + self.coefficient_p2[1]),
                             5)  # linear function
            logging.info(";" + str(time.time()) + ";[reward];pump2_reward(reward_coeff: " + str(self.coefficient_p2) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ")")
        elif which_pump == "3":
            duration = round((self.coefficient_p3[0] * (reward_size / 1000) + self.coefficient_p3[1]),
                             5)  # linear function
            logging.info(";" + str(time.time()) + ";[reward];pump3_reward(reward_coeff: " + str(self.coefficient_p3) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ")")
        elif which_pump == "4":
            duration = round((self.coefficient_p4[0] * (reward_size / 1000) + self.coefficient_p4[1]),
                             5)  # linear function
            self.pump4.blink(duration, 0.1, 1)
            self.reward_list.append(("pump4_reward", reward_size))
            logging.info(";" + str(time.time()) + ";[reward];pump4_reward(reward_coeff: " + str(self.coefficient_p4) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ")")
        elif which_pump == "air_puff":
            self.pump_air.blink(self.duration_air, 0.1, 1)
            self.reward_list.append(("air_puff", reward_size))
            logging.info(";" + str(time.time()) + ";[reward];pump4_reward_" + str(reward_size))
        elif which_pump == "vacuum":
            self.pump_vacuum.blink(self.duration_vac, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[reward];pump_vacuum" + str(self.duration_vac))
        elif which_pump == "key_1":
            duration = round((self.coefficient_p1[0] * (reward_size / 1000) + self.coefficient_p1[1]),
                             5)  # linear function
            self.pump1.blink(duration, 0.1, 1)
            self.reward_list.append(("pump1_reward", reward_size))
            logging.info(";" + str(time.time()) + ";[key];pump1_reward(reward_coeff: " + str(self.coefficient_p1) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ")")
        elif which_pump == "key_2":
            duration = round((self.coefficient_p2[0] * (reward_size / 1000) + self.coefficient_p2[1]),
                             5)  # linear function
            self.pump2.blink(duration, 0.1, 1)
            self.reward_list.append(("pump2_reward", reward_size))
            logging.info(";" + str(time.time()) + ";[key];pump2_reward(reward_coeff: " + str(self.coefficient_p2) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ")")
        elif which_pump == "key_3":
            duration = round((self.coefficient_p3[0] * (reward_size / 1000) + self.coefficient_p3[1]),
                             5)  # linear function
            self.pump3.blink(duration, 0.1, 1)
            self.reward_list.append(("pump3_reward", reward_size))
            logging.info(";" + str(time.time()) + ";[key];pump3_reward(reward_coeff: " + str(self.coefficient_p3) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ")")
        elif which_pump == "key_4":
            duration = round((self.coefficient_p4[0] * (reward_size / 1000) + self.coefficient_p4[1]),
                             5)  # linear function
            self.pump4.blink(duration, 0.1, 1)
            self.reward_list.append(("pump4_reward", reward_size))
            logging.info(";" + str(time.time()) + ";[key];pump4_reward(reward_coeff: " + str(self.coefficient_p4) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ")")
        elif which_pump == "key_air_puff":
            self.pump_air.blink(self.duration_air, 0.1, 1)
            self.reward_list.append(("air_puff", reward_size))
            logging.info(";" + str(time.time()) + ";[key];pump4_reward_" + str(reward_size))
        elif which_pump == "key_vacuum":
            self.pump_vacuum.blink(self.duration_vac, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[key];pump_vacuum" + str(self.duration_vac))
