#!/usr/bin/env python3

# contains the behavior box class, which includes pin numbers and whether DIO pins are
# configured as input or output

from gpiozero import PWMLED, LED, Button
import os
import time
from collections import deque
from icecream import ic
import pygame
import logging


# class BehavBox(mouse_name, dir_name, config):
class BehavBox():

    # if config==something:  <- the configuration determines the hardware pin config, in case there
    # is more than one hardware configuration
    # config='freely_moving1'
    config='head_fixed1'
    mouse_name='fakemouse'
    dir_name='/home/pi/fakedata'
    event_list = deque() # all detected events are added to this queue

    # TODO: this is a fake reward delivery function
    def reward(self, which_pump, reward_size):
        if which_pump=='left':
            self.pump1.blink(0.2, 0.2, reward_size)  # need to replace this with syringepump class
        elif which_pump=='center':
            self.pump2.blink(0.2, 0.2, reward_size)
        elif which_pump=='right':
            self.pump3.blink(0.2, 0.2, reward_size)

    def __init__(self):

        logging.info("behavior_box_initialized")

        ###############################################################################################
        # below are all the pin numbers for Yi's breakout board
        # cue LEDs - setting PWM frequency of 200 Hz
        ###############################################################################################
        self.cueLED1 = BoxLED(22, frequency=200)
        self.cueLED2 = BoxLED(18, frequency=200)
        self.cueLED3 = BoxLED(17, frequency=200)
        self.cueLED4 = BoxLED(14, frequency=200)

        ###############################################################################################
        # digital I/O's - TODO: use for audio??
        ###############################################################################################
        #    self.DIO1 = LED(7) # for testing, using pin 7 for syringe pump
        self.DIO2 = LED(8)
        self.DIO3 = LED(9)
        self.DIO4 = LED(10)
        self.DIO5 = LED(11)

        ###############################################################################################
        # nosepokes 
        ###############################################################################################
        self.poke1 = Button(5, None, True)  # None, True inverts the signal so poke=True, no-poke=False 
        self.poke2 = Button(6, None, True)
        self.poke3 = Button(12, None, True)
        #self.poke4 = Button(13, None, True)  # won't define pokes 4-5 right now, but those are the
        #self.poke5 = Button(16, None, True)  # pin numbers

        # link nosepoke event detections to callbacks
        self.poke1.when_pressed  = self.left_poke_entry 
        self.poke2.when_pressed  = self.center_poke_entry
        self.poke3.when_pressed  = self.right_poke_entry
        self.poke1.when_released = self.left_poke_exit
        self.poke2.when_released = self.center_poke_exit
        self.poke3.when_released = self.right_poke_exit

        
        ###############################################################################################
        # lick detectors
        ###############################################################################################
        self.lick1 = Button(26)
        self.lick2 = Button(27)
        self.lick3 = Button(15)

        # link licks to callback functions
        self.lick1.when_pressed  = self.left_lick_start 
        self.lick2.when_pressed  = self.center_lick_start
        self.lick3.when_pressed  = self.right_lick_start
        self.lick1.when_released = self.left_lick_stop
        self.lick2.when_released = self.center_lick_stop
        self.lick3.when_released = self.right_lick_stop


        ###############################################################################################
        # syringe pumps - will configure these as LEDs for now until new class is written
        ###############################################################################################
        self.pump1   = LED(7)  # for testing only - the correct pin number is 19
        # self.pump1   = LED(19)
        self.pump2   = LED(20)
        self.pump3   = LED(21)
        self.pump4   = LED(23)
        self.pump5   = LED(24)
        self.pump_en = LED(25) # pump enable


        ###############################################################################################
        # camera strobe signal
        ###############################################################################################
        self.camera_strobe = Button(4)
        # TODO: write code so that rising and falling edges are detected and logged in a separate video file



        ###############################################################################################
        # TODO: visual stimuli - unsure if better to put that here or somewhere else
        ###############################################################################################





        ###############################################################################################
        # TODO: treadmill 
        ###############################################################################################


        ###############################################################################################
        # Keystroke handler
        ###############################################################################################
        DISPLAYSURF = pygame.display.set_mode((200, 200)) 
        print("\nKeystroke handler initiated. In order for keystrokes to register, the pygame window")
        print("must be in the foreground. Keys are as follows:")
        print("         1: left poke            2: center poke            3: right poke")
        print("         Q: left lick            W: center lick            E: right lick\n")

    ###############################################################################################
    # check for key presses - uses pygame window to simulate nosepokes and licks
    ###############################################################################################
    def check_keybd(self):
        event = pygame.event.poll()
        KeyDown = 2  # event type numbers
        KeyUp   = 3
        if event:
            if event.type == KeyDown and event.key == 49:   # 1 key
                self.left_poke_entry()
            elif event.type == KeyUp and event.key == 49:
                self.left_poke_exit()
            elif event.type == KeyDown and event.key == 50:   # 2 key
                self.center_poke_entry()
            elif event.type == KeyUp and event.key == 50:
                self.center_poke_exit()
            elif event.type == KeyDown and event.key == 51:   # 3 key
                self.right_poke_entry()
            elif event.type == KeyUp and event.key == 51:
                self.right_poke_exit()
            elif event.type == KeyDown and event.key == 113:  # Q key
                self.left_lick_start()
            elif event.type == KeyUp and event.key == 113:    
                self.left_lick_stop()
            elif event.type == KeyDown and event.key == 119:  # W key
                self.center_lick_start()
            elif event.type == KeyUp and event.key == 119:
                self.center_lick_stop()
            elif event.type == KeyDown and event.key == 101:  # E key
                self.right_lick_start()
            elif event.type == KeyUp and event.key == 101:
                self.right_lick_stop()



    ###############################################################################################
    # methods to start and stop video
    # These work with fake video files but haven't been tested with real ones
    ###############################################################################################
    def video_start(self):
        if self.config=='head_fixed1':
            # this assumes the second RPi has the same hostname except with a "b"
            # appended, e.g. bumbrlik02b instead of bumbrlik02
            os.system("ssh pi@`hostname`b 'date >> ~/Videos/videolog.log ' ")
            tempstr = "ssh pi@`hostname`b \'nohup /home/pi/RPi4_behavior_boxes/record_video.py " + self.mouse_name + " >> ~/Videos/videolog.log 2>&1 & \' "
            # print(tempstr)
            os.system(tempstr)

        if self.config=='freely_moving1':
            # for freely-moving box
            os.system("date >> ~/Videos/videolog.txt")
            tempstr = "nohup /home/pi/RPi4_behavior_boxes/record_video.py " + self.mouse_name + " >> ~/Videos/videolog.log 2>&1 & "
            # print(tempstr)
            os.system(tempstr)
            
    def video_stop(self):
        if self.config=='head_fixed1':
            # sends SIGINT to record_video.py, telling it to exit
            os.system("ssh pi@`hostname`b /home/pi/RPi4_behavior_boxes/stop_video")
            time.sleep(1)
            os.system("rsync --remove-source-files pi@`hostname`b:Videos/*.avi " + self.dir_name + " & ") 
            os.system("rsync --remove-source-files pi@`hostname`b:Videos/*.log " + self.dir_name + " & ")

        if self.config=='freely_moving1':
            # sends SIGINT to record_video.py, telling it to exit
            os.system("/home/pi/RPi4_behavior_boxes/stop_video")
            time.sleep(1)
            os.system("mv /home/pi/Videos/*.avi " + self.dir_name + " & ")
            os.system("mv /home/pi/Videos/*.log " + self.dir_name + " & ")


    ###############################################################################################
    # callbacks
    ###############################################################################################
    def left_poke_entry(self): 
        self.event_list.append('left_poke_entry')
        logging.info('left_poke_entry')
    def center_poke_entry(self): 
        self.event_list.append('center_poke_entry')
        logging.info('center_poke_entry')
    def right_poke_entry(self): 
        self.event_list.append('right_poke_entry')
        logging.info('right_poke_entry')

    def left_poke_exit(self): 
        self.event_list.append('left_poke_exit')
        logging.info('left_poke_exit')
    def center_poke_exit(self): 
        self.event_list.append('center_poke_exit')
        logging.info('center_poke_exit')
    def right_poke_exit(self): 
        self.event_list.append('right_poke_exit')
        logging.info('right_poke_exit')

    def left_lick_start(self): 
        self.event_list.append('left_lick_start')
        logging.info('left_lick_start')
    def center_lick_start(self): 
        self.event_list.append('center_lick_start')
        logging.info('center_lick_start')
    def right_lick_start(self): 
        self.event_list.append('right_lick_start')
        logging.info('right_lick_start')

    def left_lick_stop(self): 
        self.event_list.append('left_lick_stop')
        logging.info('left_lick_stop')
    def center_lick_stop(self): 
        self.event_list.append('center_lick_stop')
        logging.info('center_lick_stop')
    def right_lick_stop(self): 
        self.event_list.append('right_lick_stop')
        logging.info('right_lick_stop')


# this is for the cue LEDs. BoxLED.value is the intensity value (PWM duty cycle, from 0 to 1)
# currently. BoxLED.set_value is the saved intensity value that determines how bright the 
# LED will be if BoxLED.on() is called. This is better than the original PWMLED class.
class BoxLED(PWMLED):
    set_value = 1  # the intensity value, ranging from 0-1
    def on(self):  # unlike PWMLED, here the on() function sets the intensity to set_value,
                   # not to full intensity
        self.value = self.set_value


