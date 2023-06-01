import pygame
from behavbox import Pump
import numpy as np
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