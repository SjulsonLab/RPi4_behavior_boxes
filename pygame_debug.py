import pygame
import time
try:
    DISPLAYSURF = pygame.display.set_mode((200, 200))
except Exception as error_message:
    print(str(error_message))
event = pygame.event.poll()
# KeyDown = 768
# KeyUp = 769
while True:
    time.sleep(0.3)
    if event.key:
        print(str(event.key))