#!/usr/bin/env python3

# contains the behavior box class, which includes pin numbers and whether DIO pins are
# configured as input or output

from gpiozero import PWMLED, LED, Button
import os
import time
from collections import deque
from icecream import ic

# this is for the cue LEDs. BoxLED.value is the intensity value (PWM duty cycle, from 0 to 1)
# currently. BoxLED.set_value is the saved intensity value that determines how bright the 
# LED will be if BoxLED.on() is called. This is better than the original PWMLED class.
class BoxLED(PWMLED):
    set_value = 1  # the intensity value, ranging from 0-1
    def on(self):  # unlike PWMLED, here the on() function sets the intensity to set_value,
                   # not to full intensity
        self.value = self.set_value



# class BehavBox(mouse_name, dir_name, config):
class BehavBox():

    # if config==something:  <- the configuration determines the hardware pin config, in case there
    # is more than one hardware configuration
    # config='freely_moving1'
    config='head_fixed1'
    mouse_name='fakemouse'
    dir_name='/home/pi/fakedata'
    event_list = deque() # all detected events are added to this queue

    ###############################################################################################
    # below are all the pin numbers for Yi's breakout board
    # cue LEDs - setting PWM frequency of 200 Hz
    ###############################################################################################
    cueLED1 = BoxLED(22, frequency=200)
    cueLED2 = BoxLED(18, frequency=200)
    cueLED3 = BoxLED(17, frequency=200)
    cueLED4 = BoxLED(14, frequency=200)

    ###############################################################################################
    # digital I/O's - TODO: use for audio??
    ###############################################################################################
#    DIO1 = LED(7) # for testing, using pin 7 for syringe pump
    DIO2 = LED(8)
    DIO3 = LED(9)
    DIO4 = LED(10)
    DIO5 = LED(11)

    ###############################################################################################
    # nosepokes 
    ###############################################################################################
    poke1 = Button(5, None, True)  # None, True inverts the signal so poke=True, no-poke=False 
    poke2 = Button(6, None, True)
    poke3 = Button(12, None, True)
    #poke4 = Button(13, None, True)  # won't define pokes 4-5 right now
    #poke5 = Button(16, None, True)

    poke1.when_pressed  = left_poke_entry # link nosepokes to callback functions
    poke2.when_pressed  = center_poke_entry
    poke3.when_pressed  = right_poke_entry
    poke1.when_released = left_poke_exit
    poke2.when_released = center_poke_exit
    poke3.when_released = right_poke_exit

    def left_poke_entry(self): 
        self.event_list.append('left_poke_entry')
        ic('left_poke_entry')
    def center_poke_entry(self): 
        self.event_list.append('center_poke_entry')
        ic('center_poke_entry')
    def right_poke_entry(self): 
        self.event_list.append('right_poke_entry')
        ic('right_poke_entry')

    def left_poke_exit(self): 
        self.event_list.append('left_poke_exit')
        ic('left_poke_exit')
    def center_poke_exit(self): 
        self.event_list.append('center_poke_exit')
        ic('center_poke_exit')
    def right_poke_exit(self): 
        self.event_list.append('right_poke_exit')
        ic('right_poke_exit')

    
    ###############################################################################################
    # lick detectors
    ###############################################################################################
    lick1 = Button(26)
    lick2 = Button(27)
    lick3 = Button(15)

    lick1.when_pressed  = left_lick_start # link licks to callback functions
    lick2.when_pressed  = center_lick_start
    lick3.when_pressed  = right_lick_start
    lick1.when_released = left_lick_stop
    lick2.when_released = center_lick_stop
    lick3.when_released = right_lick_stop

    def left_lick_start(self): 
        self.event_list.append('left_lick_start')
        ic('left_lick_start')
    def center_lick_start(self): 
        self.event_list.append('center_lick_start')
        ic('center_lick_start')
    def right_lick_start(self): 
        self.event_list.append('right_lick_start')
        ic('right_lick_start')

    def left_lick_stop(self): 
        self.event_list.append('left_lick_stop')
        ic('left_lick_stop')
    def center_lick_stop(self): 
        self.event_list.append('center_lick_stop')
        ic('center_lick_stop')
    def right_lick_stop(self): 
        self.event_list.append('right_lick_stop')
        ic('right_lick_stop')

    ###############################################################################################
    # syringe pumps - will configure these as LEDs for now until new class is written
    ###############################################################################################
    pump1   = LED(7)  # for testing only - the correct pin number is 19
    # pump1   = LED(19)
    pump2   = LED(20)
    pump3   = LED(21)
    pump4   = LED(23)
    pump5   = LED(24)
    pump_en = LED(25) # pump enable

    def reward(self, which_pump, reward_size):
        if which_pump=='left':
            self.pump1.blink(0.2, 0.2, reward_size)  # need to replace this with syringepump class
        elif which_pump=='center':
            self.pump2.blink(0.2, 0.2, reward_size)
        elif which_pump=='right':
            self.pump3.blink(0.2, 0.2, reward_size)


    ###############################################################################################
    # camera strobe signal
    ###############################################################################################
    camera_strobe = Button(4)
    # TODO: write code so that rising and falling edges are detected and logged in a separate video file



    ###############################################################################################
    # TODO: visual stimuli - unsure if better to put that here or somewhere else
    ###############################################################################################





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


# # stuff for testing - won't be in final version            
# box = BehavBox()
# box.video_start()
# print("video started")
# time.sleep(5)
# box.video_stop()
# print("video stopped")



