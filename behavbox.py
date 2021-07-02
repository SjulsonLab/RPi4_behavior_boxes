# contains the behavior box class, which includes pin numbers and whether DIO pins are
# configured as input or output

from gpiozero import PWMLED, LED, Button
import os
import socket
import time
from collections import deque
from icecream import ic
import pygame
import logging
from colorama import Fore, Style
import pysistence, collections
from visualstim import VisualStim

#############
import Treadmill
# import Adafruit_ADS1x15
import adafruit_ads1x15

class BehavBox(object):

    event_list = (
        deque()
    )  # all detected events are added to this queue to be read out by the behavior class

    # TODO: write this up in a syringe pump class
    def reward(self, which_pump, reward_size):
        print("TODO: calibrate and test syringe pump code in BehavBox.reward()")
        diameter_mm = 12.06  # for 5 mL syringe
        # diameter_mm = 14.5   # for 10 mL syringe
        volPerRevolution_uL = (
            0.8 * (diameter_mm / 2) * (diameter_mm / 2) * 3.1415926535898
        )  # thread is 0.8 mm per turn
        howManyRevolutions = reward_size / volPerRevolution_uL
        # // determine total steps needed to reach desired revolutions, @200 steps/revolution
        # // use *4 as a multiplier because it's operating at 1/4 microstep mode.
        # // round to nearest int
        totalSteps = round(200 * howManyRevolutions * 4)
        reward_duration = 1  # delivery reward over 300 ms
        cycle_length = (
            reward_duration / totalSteps
        )  # need to know what the minimum value can be

        if which_pump == "left":
            self.pump1.blink(cycle_length * 0.1, cycle_length * 0.9, totalSteps)
            logging.info("left_reward," + str(reward_size))
        elif which_pump == "center":
            self.pump2.blink(cycle_length * 0.1, cycle_length * 0.9, totalSteps)
            logging.info("center_reward," + str(reward_size))
        elif which_pump == "right":
            logging.info("right_reward," + str(reward_size))
            self.pump3.blink(cycle_length * 0.1, cycle_length * 0.9, totalSteps)

    def __init__(self, session_info):

        logging.info("behavior_box_initialized")
        self.session_info = session_info

        IP_address = socket.gethostbyname(socket.gethostname() + ".local")
        self.IP_address = IP_address
        IP_address_video_list = list(IP_address)
        IP_address_video_list[-3] = "2"
        self.IP_address_video = "".join(IP_address_video_list)

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
        # self.DIO1 = LED(7)  # don't declare DIO1. It's reserved for the frame out pin for the visual stimuli
        self.DIO2 = LED(8)
        # self.DIO3 = LED(9)  # for testing purposes using pin 9 for the syringe pump
        self.DIO4 = LED(10)
        self.DIO5 = LED(11)
        # there is a DIO6, but that is the same pin as the camera strobe

        ###############################################################################################
        # nosepokes
        ###############################################################################################
        self.poke1 = Button(
            5, None, True
        )  # None, True inverts the signal so poke=True, no-poke=False
        self.poke2 = Button(6, None, True)
        self.poke3 = Button(12, None, True)
        # self.poke4 = Button(13, None, True)  # won't define pokes 4-5 right now, but those are the
        # self.poke5 = Button(16, None, True)  # pin numbers

        # link nosepoke event detections to callbacks
        self.poke1.when_pressed = self.left_poke_entry
        self.poke2.when_pressed = self.center_poke_entry
        self.poke3.when_pressed = self.right_poke_entry
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
        self.lick1.when_pressed = self.left_lick_start
        self.lick2.when_pressed = self.center_lick_start
        self.lick3.when_pressed = self.right_lick_start
        self.lick1.when_released = self.left_lick_stop
        self.lick2.when_released = self.center_lick_stop
        self.lick3.when_released = self.right_lick_stop

        ###############################################################################################
        # syringe pumps - will configure these as LEDs for now until new class is written
        ###############################################################################################
        self.pump1 = LED(9)  # for testing only - the correct pin number is 19
        # self.pump1   = LED(19)
        self.pump2 = LED(20)
        self.pump3 = LED(21)
        self.pump4 = LED(23)
        self.pump5 = LED(24)
        self.pump_en = LED(25)  # pump enable

        ###############################################################################################
        # camera strobe signal
        ###############################################################################################
        self.camera_strobe = Button(4)
        # TODO: write code so that rising and falling edges are detected and logged in a separate video file

        # ###############################################################################################
        # # visual stimuli
        # ###############################################################################################
        # self.visualstim = VisualStim(self.session_info)

        # ###############################################################################################
        # # TODO: ADC(Adafruit_ADS1x15)
        # ###############################################################################################
        # self.ADC = ADS1x15(self.ADS1015)

        # ###############################################################################################
        # # TODO: treadmill
        # ###############################################################################################
        # self.treadmill = Treadmill(self.dacval)

        ###############################################################################################
        # Keystroke handler
        ###############################################################################################
        DISPLAYSURF = pygame.display.set_mode((200, 200))
        pygame.display.set_caption(session_info["box_name"])
        print(
            "\nKeystroke handler initiated. In order for keystrokes to register, the pygame window"
        )
        print("must be in the foreground. Keys are as follows:\n")
        print(
            Fore.YELLOW
            + "         1: left poke            2: center poke            3: right poke"
        )
        print(
            "         Q: left lick            W: center lick            E: right lick"
        )
        print(
            Fore.CYAN
            + "                       Esc: close key capture window\n"
            + Style.RESET_ALL
        )
        print(
            Fore.GREEN
            + Style.BRIGHT
            + "         TO EXIT, CLICK THE MAIN TEXT WINDOW AND PRESS CTRL-C "
            + Fore.RED
            + "ONCE\n"
            + Style.RESET_ALL
        )

        self.keyboard_active = True

    ###############################################################################################
    # check for key presses - uses pygame window to simulate nosepokes and licks
    ###############################################################################################
    def check_keybd(self):
        if self.keyboard_active == True:
            event = pygame.event.poll()
            KeyDown = 2  # event type numbers
            KeyUp = 3
            if event:
                if event.type == KeyDown and event.key == 49:  # 1 key
                    self.left_poke_entry()
                elif event.type == KeyUp and event.key == 49:
                    self.left_poke_exit()
                elif event.type == KeyDown and event.key == 50:  # 2 key
                    self.center_poke_entry()
                elif event.type == KeyUp and event.key == 50:
                    self.center_poke_exit()
                elif event.type == KeyDown and event.key == 51:  # 3 key
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
                elif event.type == KeyDown and event.key == 27:  # escape key
                    pygame.quit()
                    self.keyboard_active = False

    ###############################################################################################
    # methods to start and stop video
    # These work with fake video files but haven't been tested with real ones
    ###############################################################################################
    def video_start(self):
        # IP_address_video = self.IP_address_video
        # dir_name = self.session_info['dir_name']
        # if self.session_info["config"] == "head_fixed_v1":
        #     # this assumes the second RPi has the same hostname except with a "b"
        #     # appended, e.g. bumbrlik02b instead of bumbrlik02
        #
        #     # Now that we have the IP_address_video:
        #     os.system("ssh pi@" + IP_address_video + " 'date >> " + dir_name + "/videolog.log ' ")
        #     tempstr = (
        #         "ssh pi@" + IP_address_video + " 'nohup /home/pi/RPi4_behavior_boxes/record_video.py "
        #         + self.session_info["mouse_name"]
        #         + " >> ~/Videos/videolog.log 2>&1 & ' "
        #     )
        #     os.system(tempstr)
        #
        # elif self.session_info["config"] == "freely_moving_v1":
        #     # for freely-moving box
        #     os.system("ssh pi@" + IP_address_video + " 'date >> ~/Videos/videolog.log ' ")
        #     tempstr = (
        #         "ssh pi@" + IP_address_video + " 'nohup /home/pi/RPi4_behavior_boxes/record_video.py "
        #         + self.session_info["mouse_name"]
        #         + " >> ~/Videos/videolog.log 2>&1 & "
        #     )
        #     os.system(tempstr)
        #
        # else:
        #     print("config in session_info not recognized by BehavBox!")
        #     raise RuntimeError
        IP_address_video = self.IP_address_video
        dir_name = self.session_info['dir_name']
        basename = self.session_info['basename']
        file_name = dir_name + "/" + basename

        os.system("ssh pi@" + IP_address_video + " mkdir " + dir_name)
        os.system("ssh pi@" + IP_address_video + " 'date >> ~/video/videolog.log' ")  # I/O redirection
        tempstr = (
                "ssh pi@" + IP_address_video + " 'nohup /home/pi/RPi4_behavior_boxes/record_video.py "
                + dir_name
                + " >> " + dir_name + ".log 2>&1 & ' "  # file descriptors
        )

        # start recording
        os.system(tempstr)

    def video_stop(self):
        # Get the basename from the session information
        basename = self.session_info['basename']
        dir_name = self.session_info['dir_name']
        # Get the ip address for the box video:
        IP_address_video = self.IP_address_video

        # Run the stop_video script in the box video
        os.system("ssh pi@" + IP_address_video + " /home/pi/RPi4_behavior_boxes/stop_video")
        time.sleep(2)
        hostname = socket.gethostname()
        print("Moving video files from " + hostname + "video to " + hostname + ":")

        # Create a directory for storage on the hard drive mounted on the box behavior
        base_dir = '/mnt/hd/'
        hd_dir = base_dir + basename
        os.mkdir(hd_dir)

        # Move the video + log from the box_video SD card to the box_behavior external hard drive
        os.system(
            "rsync -av --progress --remove-source-files pi@" + IP_address_video + ":" + dir_name + " "
            + hd_dir
        )
        print("rsync finished!")

        # # if self.session_info["config"] == "head_fixed_v1":
        # # sends SIGINT to record_video.py, telling it to exit
        # os.system("ssh pi@" + IP_address_video + " /home/pi/RPi4_behavior_boxes/stop_video")
        # time.sleep(2)
        # hostname = socket.gethostname()
        # print("Moving video files from " + hostname + "video to " + hostname + ":")
        # os.system(
        #     "rsync -av --progress --remove-source-files pi@" + IP_address_video + ":Videos/*.avi " # this could be a problem .avi
        #     + self.session_info["dir_name"]
        # )
        # os.system(
        #     "rsync -av --progress --remove-source-files pi@" + IP_address_video + ":Videos/*.log "
        #     + self.session_info["dir_name"]
        # )
        #
        # elif self.session_info["config"] == "freely_moving_v1":
        #     # sends SIGINT to record_video.py, telling it to exit
        #     os.system("ssh pi@" + IP_address_video + " /home/pi/RPi4_behavior_boxes/stop_video")
        #     time.sleep(2)
        #     os.system(
        #         "mv /home/pi/Videos/*.avi " + self.session_info["dir_name"] + " & "
        #     )
        #     os.system(
        #         "mv /home/pi/Videos/*.log " + self.session_info["dir_name"] + " & "
        #     )

    ###############################################################################################
    # callbacks
    ###############################################################################################
    def left_poke_entry(self):
        self.event_list.append("left_poke_entry")
        logging.info("left_poke_entry")

    def center_poke_entry(self):
        self.event_list.append("center_poke_entry")
        logging.info("center_poke_entry")

    def right_poke_entry(self):
        self.event_list.append("right_poke_entry")
        logging.info("right_poke_entry")

    def left_poke_exit(self):
        self.event_list.append("left_poke_exit")
        logging.info("left_poke_exit")

    def center_poke_exit(self):
        self.event_list.append("center_poke_exit")
        logging.info("center_poke_exit")

    def right_poke_exit(self):
        self.event_list.append("right_poke_exit")
        logging.info("right_poke_exit")

    def left_lick_start(self):
        self.event_list.append("left_lick_start")
        logging.info("left_lick_start")

    def center_lick_start(self):
        self.event_list.append("center_lick_start")
        logging.info("center_lick_start")

    def right_lick_start(self):
        self.event_list.append("right_lick_start")
        logging.info("right_lick_start")

    def left_lick_stop(self):
        self.event_list.append("left_lick_stop")
        logging.info("left_lick_stop")

    def center_lick_stop(self):
        self.event_list.append("center_lick_stop")
        logging.info("center_lick_stop")

    def right_lick_stop(self):
        self.event_list.append("right_lick_stop")
        logging.info("right_lick_stop")


# this is for the cue LEDs. BoxLED.value is the intensity value (PWM duty cycle, from 0 to 1)
# currently. BoxLED.set_value is the saved intensity value that determines how bright the
# LED will be if BoxLED.on() is called. This is better than the original PWMLED class.
class BoxLED(PWMLED):
    set_value = 1  # the intensity value, ranging from 0-1

    def on(
        self,
    ):  # unlike PWMLED, here the on() function sets the intensity to set_value,
        # not to full intensity
        self.value = self.set_value
