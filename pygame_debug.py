import pygame
import time

pygame.init()
try:
    DISPLAYSURF = pygame.display.set_mode((200, 200))
    pygame.display.set_caption("pygame debugging")

except Exception as error_message:
    print(str(error_message))
# event = pygame.event.poll()
# KeyDown = 768 # for raspberry pi from linux machine
# KeyUp = 769 # for raspberry pi from linux machine
# KeyDown = 771 # for macOS
# KeyUp = 769 # for macOS
run = True
while run:
    # time.sleep(0.3)
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            run = False
        if event.type == pygame.KEYDOWN:
            # print("KeyDown: " + str(event.type) + "\n")
            if event.key == pygame.K_w:
                print("key W down")
            # print("KeyDown: " + str(event.key))
            # print(event)
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_w:
                print("key W up")
            # print(event)