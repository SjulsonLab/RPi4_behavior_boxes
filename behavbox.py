#!/usr/bin/env python3

# contains the behavior box class, which includes pin numbers and whether DIO pins are
# configured as input or output

from gpiozero import PWMLED, LED, Button
import os
import time


# this is for the cue LEDs. BoxLED.value is the intensity value (PWM duty cycle, from 0 to 1)
# currently. BoxLED.set_value is the saved intensity value that determines how bright the 
# LED will be if BoxLED.on() is called
class BoxLED(PWMLED):
    set_value = 1  # the intensity value, ranging from 0-1
    def on(self):  # unlike PWMLED, here the on() function sets the intensity to set_value,
                   # not to full intensity
        self.value = self.set_value



# class BehavBox(mouse_name, dir_name, config):
class BehavBox():

    # if config==something:  <- the configuration determines the hardware pin config, in case there
    # is more than one hardware configuration
    config='freely_moving1'
    mouse_name='fakemouse'
    dir_name='/home/pi/fakedata'

    # below are all the pin numbers for Yi's breakout board
    # cue LEDs - setting PWM frequency of 200 Hz
    cueLED1 = BoxLED(22, frequency=200)
    cueLED2 = BoxLED(18, frequency=200)
    cueLED3 = BoxLED(17, frequency=200)
    cueLED4 = BoxLED(14, frequency=200)

    # digital I/O's (all are configured as output here)
    DIO1 = LED(7)
    DIO2 = LED(8)
    DIO3 = LED(9)
    DIO4 = LED(10)
    DIO5 = LED(11)

    # nosepokes (the "True" as 3rd argument inverts the signal so poke=True, no-poke=False)
    poke1 = Button(5, None, True)  
    poke2 = Button(6, None, True)
    poke3 = Button(12, None, True)
    poke4 = Button(13, None, True)
    poke5 = Button(16, None, True)

    # syringe pumps - will configure these as LEDs for now until new class is written
    pump1   = LED(19)
    pump2   = LED(20)
    pump3   = LED(21)
    pump4   = LED(23)
    pump5   = LED(24)
    pump_en = LED(25) # pump enable

    # lick detectors
    lick1 = Button(26)
    lick2 = Button(27)
    lick3 = Button(15)

    # camera strobe signal
    camera_strobe = Button(4)


    # TODO: auditory stimuli - maybe using DIO's??


    # TODO: visual stimuli - unsure if better to put that here or somewhere else


    # TODO: test these methods to start and stop 
    def video_start(self):
        if self.config=='head_fixed1':
            # untested - this assumes the second RPi has the same hostname except with a "b"
            # appended, e.g. bumbrlik02b instead of bumbrlik02
            tempstr = "ssh pi@`hostname`b \'/home/pi/RPi4_behavior_boxes/record_video.py " + self.mouse_name + " &\' "
            print(tempstr)
            os.system(tempstr)

        if self.config=='freely_moving1':
            # untested - for freely-moving box
            tempstr = "/home/pi/RPi4_behavior_boxes/record_video.py " + self.mouse_name + " & "
            print(tempstr)
            os.system(tempstr)
            
    def video_stop(self):
        if self.config=='head_fixed1':
            # sends SIGINT to record_video.py, telling it to exit
            os.system("ssh pi@`hostname`b \'kill -1 `ps ax | grep -v grep | grep record_video | cut -d \" \" -f 1` \' ")
            time.sleep(1)
            os.system("rsync --delete-source-files pi@`hostname`b:Videos/*.avi " + self.dir_name + " & ") 
            os.system("rsync --delete-source-files pi@`hostname`b:Videos/*.log " + self.dir_name + " & ")

        if self.config=='freely_moving1':
            l1 = "ssh pi@`hostname`b \'kill -1 `ps uax | grep -v grep | grep record_video | tr -s \" \" | cut -d \" \" -f 2` \' "
            print(l1)
            os.system(l1)
            time.sleep(1)
            os.system("mv /home/pi/Videos/*.avi " + self.dir_name + " & ")
            os.system("mv /home/pi/Videos/*.log " + self.dir_name + " & ")


            

box = BehavBox()
box.video_start()
time.sleep(5)
box.video_stop()




