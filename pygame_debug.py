import pygame
import time
try:
    DISPLAYSURF = pygame.display.set_mode((200, 200))
except Exception as error_message:
    print(str(error_message))
event = pygame.event.poll()
KeyDown = 768
KeyUp = 769
if event:
    if event.type == KeyDown:
        print("KeyDown: " + str(event.key))
    elif event.type == KeyUp:
        print("KeyUp: " + str(event.key))