import pygame
import time
try:
    DISPLAYSURF = pygame.display.set_mode((200, 200))

event = pygame.event.poll()
# KeyDown = 768
# KeyUp = 769
while True:
    time.sleep(0.3)
    if event:
        print(str(event.key))