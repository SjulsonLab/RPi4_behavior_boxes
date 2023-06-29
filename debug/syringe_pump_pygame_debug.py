import pygame
from behavbox import Pump
import numpy as np

class Pump(object):
    def __init__(self, session_info):
        self.pump1 = LED(19)
        self.pump2 = LED(20)
        self.pump3 = LED(21)
        self.pump4 = LED(7)
        self.pump_air = LED(8)
        self.pump_vacuum = LED(25)
        self.reward_list = [] # a list of tuple (pump_x, reward_amount) with information of reward history for data
        # visualization

    def reward(self, which_pump, reward_size):
        # import coefficient from the session_information
        coefficient_p1 = [0.13, 0]
        coefficient_p2 = [0.13, 0]
        coefficient_p3 = [0.13, 0]
        coefficient_p4 = [0.13, 0]
        duration_air = 1
        duration_vac = 1

        if which_pump == "1":
            duration = round((coefficient_p1[0] * (reward_size / 1000) + coefficient_p1[1]), 5)  # linear function
            self.pump1.blink(duration, 0.1, 1)
            self.reward_list.append(("pump1_reward", reward_size))
            logging.info(";" + str(time.time()) + ";[reward];pump1_reward(reward_coeff: " + str(coefficient_p1) +
                         ", reward_amount: " + str(reward_size) + "duration: " + str(duration) + ")")
        elif which_pump == "2":
            duration = round((coefficient_p2[0] * (reward_size / 1000) + coefficient_p2[1]), 5)  # linear function
            self.pump2.blink(duration, 0.1, 1)
            self.reward_list.append(("pump2_reward", reward_size))
            logging.info(";" + str(time.time()) + ";[reward];pump2_reward(reward_coeff: " + str(coefficient_p2) +
                         ", reward_amount: " + str(reward_size) + "duration: " + str(duration) + ")")
        elif which_pump == "3":
            duration = round((coefficient_p3[0] * (reward_size / 1000) + coefficient_p3[1]), 5)  # linear function
            self.pump3.blink(duration, 0.1, 1)
            self.reward_list.append(("pump3_reward", reward_size))
            logging.info(";" + str(time.time()) + ";[reward];pump3_reward(reward_coeff: " + str(coefficient_p3) +
                         ", reward_amount: " + str(reward_size) + "duration: " + str(duration) + ")")
        elif which_pump == "4":
            duration = round((coefficient_p4[0] * (reward_size / 1000) + coefficient_p4[1]), 5)  # linear function
            self.pump4.blink(duration, 0.1, 1)
            self.reward_list.append(("pump4_reward", reward_size))
            logging.info(";" + str(time.time()) + ";[reward];pump4_reward(reward_coeff: " + str(coefficient_p4) +
                         ", reward_amount: " + str(reward_size) + "duration: " + str(duration) + ")")
        elif which_pump == "air_puff":
            self.pump_air.blink(duration_air, 0.1, 1)
            self.reward_list.append(("air_puff", reward_size))
            logging.info(";" + str(time.time()) + ";[reward];pump4_reward_" + str(reward_size))
        elif which_pump == "vacuum":
            self.pump_vacuum.blink(duration_vac, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[reward];pump_vacuum" + str(duration_vac))
try:
    pump = Pump()
    pygame.init()
    DISPLAYSURF = pygame.display.set_mode((200, 200))
    pygame.display.set_caption("pygame debugging")
except Exception as error_message:
    print(str(error_message))

run = True
reward_size = float(input("Input reward_size: "))

while run:
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            run = False
        if event.type == pygame.KEYDOWN:
            # print("KeyDown: " + str(event.type) + "\n")
            if event.key == pygame.K_q:
                print("Q down: syringe pump 1")
                pump.reward("1", reward_size)
            if event.key == pygame.K_w:
                print("W down: syringe pump 2")
                pump.reward("2", reward_size)
            if event.key == pygame.K_e:
                print("E down: syringe pump 3")
                pump.reward("3", reward_size)
            if event.key == pygame.K_r:
                print("R down: syringe pump 4")
                pump.reward("4", reward_size)
            if event.key == pygame.K_a:
                print("A down: air puff on")
                pump.reward("air_puff", reward_size)
            if event.key == pygame.K_s:
                print("S down: vacuum on")
                pump.reward("vacuum", 1)