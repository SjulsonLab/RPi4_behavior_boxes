import pygame
from behavbox import Pump

try:
    pump = Pump()
    pygame.init()
    DISPLAYSURF = pygame.display.set_mode((200, 200))
    pygame.display.set_caption("pygame debugging")
except Exception as error_message:
    print(str(error_message))

run = True
reward_size = 100
while run:
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            run = False
        if event.type == pygame.KEYDOWN:
            # print("KeyDown: " + str(event.type) + "\n")
            if event.key == pygame.K_q:
                print("Q down: syringe pump 1 moves")
                pump.reward("1", reward_size)
            if event.key == pygame.K_w:
                print("W down: syringe pump 2 moves")
                pump.reward("2", reward_size)
            if event.key == pygame.K_e:
                print("E down: syringe pump 3 moves")
                pump.reward("3", reward_size)
            if event.key == pygame.K_r:
                print("R down: syringe pump 4 moves")
                pump.reward("4", reward_size)
        # elif event.type == pygame.KEYUP:
        #     if event.key == pygame.K_q:
        #         print("Q up: syringe pump 1 moves")
        #     if event.key == pygame.K_w:
        #         print("W up: syringe pump 2 moves")
        #     if event.key == pygame.K_e:
        #         print("E up: syringe pump 3 moves")
        #     if event.key == pygame.K_r:
        #         print("R up: syringe pump 4 moves")