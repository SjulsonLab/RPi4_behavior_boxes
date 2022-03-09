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
# from visualstim import VisualStim
from visualstim_go import VisualStim_go
from visualstim_nogo import VisualStim_nogo

import scipy.io, pickle

import Treadmill
import ADS1x15

from fake_session_info import fake_session_info

# for the flipper
from FlipperOutput import FlipperOutput


class BehavBox(object):
    event_list = (
        deque()
    )  # all detected events are added to this queue to be read out by the behavior class

    def __init__(self, session_info):

        logging.info(str(time.time()) + ", behavior_box_initialized")

        # set up the external hard drive path for the flipper output
        self.session_info = session_info
        storage_path = self.session_info['external_storage'] + '/' + self.session_info['basename']
        self.session_info['flipper_filename'] = storage_path + '/' + self.session_info['basename'] + '_flipper_output'

        # initiating flipper object
        self.flipper = FlipperOutput(self.session_info, pin=4)

        from subprocess import check_output
        IP_address = check_output(['hostname', '-I']).decode('ascii')[:-2]
        self.IP_address = IP_address
        IP_address_video_list = list(IP_address)
        IP_address_video_list[-3] = "2"
        self.IP_address_video = "".join(IP_address_video_list)
        ###############################################################################################
        # below are all the pin numbers for Yi's breakout board
        # cue LEDs - setting PWM frequency of 200 Hz
        ###############################################################################################
        self.cueLED1 = BoxLED(22, frequency=100)
        self.cueLED2 = BoxLED(18, frequency=200)
        self.cueLED3 = BoxLED(17, frequency=200)
        self.cueLED4 = BoxLED(14, frequency=200)

        ###############################################################################################
        # digital I/O's - used for cue LED
        # cue for animals
        # DIO 1 and 2 are reserved for the audio board
        ###############################################################################################
        self.DIO3 = LED(9)  # reserved for vacuum function
        self.DIO4 = LED(10)
        self.DIO5 = LED(11)
        # there is a DIO6, but that is the same pin as the camera strobe

        ###############################################################################################
        # IR detection (for licks)
        ###############################################################################################
        self.IR_rx1 = Button(5, None, True)  # None, True inverts the signal so poke=True, no-poke=False
        self.IR_rx2 = Button(6, None, True)
        self.IR_rx3 = Button(12, None, True)
        self.IR_rx4 = Button(13, None, True)  # (optional, reserved for future use
        self.IR_rx5 = Button(16, None, True)  # (optional, reserved for future use

        # link nosepoke event detections to callbacks (exit and entry are opposite to pressed and release)
        self.IR_rx1.when_pressed = self.left_IR_exit
        self.IR_rx2.when_pressed = self.center_IR_exit
        self.IR_rx3.when_pressed = self.right_IR_exit
        self.IR_rx1.when_released = self.left_IR_entry
        self.IR_rx2.when_released = self.center_IR_entry
        self.IR_rx3.when_released = self.right_IR_entry

        ###############################################################################################
        # sound: audio board DIO - pins sending TTL to the Tsunami soundboard via SMA connectors
        ###############################################################################################
        # pins originally reserved for the lick detection is now used for audio board TTL input signal
        self.sound1 = LED(26)  # originally lick1
        self.sound2 = LED(27)  # originally lick2
        self.sound3 = LED(15)  # originally lick3

        self.sound4 = LED(23)  # originally DIO1
        self.sound5 = LED(24)  # originally DIO2

        # ###############################################################################################
        # # lick detectors
        # ###############################################################################################
        # self.lick1 = Button(26)
        # self.lick2 = Button(27)
        # self.lick3 = Button(15)
        #
        # # link licks to callback functions
        # self.lick1.when_pressed = self.left_lick_start
        # self.lick2.when_pressed = self.center_lick_start
        # self.lick3.when_pressed = self.right_lick_start
        # self.lick1.when_released = self.left_lick_stop
        # self.lick2.when_released = self.center_lick_stop
        # self.lick3.when_released = self.right_lick_stop

        ###############################################################################################
        # camera strobe signal
        ###############################################################################################
        # self.camera_strobe = Button(4)
        # # TODO: write code so that rising and falling edges are detected and logged in a separate video file

        ###############################################################################################
        # visual stimuli
        ###############################################################################################
        try:
            # self.visualstim = VisualStim(self.session_info)
            self.visualstim_go = VisualStim_go(self.session_info)
            self.visualstim_nogo = VisualStim_nogo(self.session_info)

        except Exception as error_message:
            print("visualstim issue\n")
            print(str(error_message))

        ###############################################################################################
        # TODO: ADC(Adafruit_ADS1x15)
        ###############################################################################################
        try:
            self.ADC = ADS1x15.ADS1015
        except Exception as error_message:
            print("ADC issue\n")
            print(str(error_message))

        # ###############################################################################################
        # # TODO: treadmill
        # ###############################################################################################
        try:
            self.treadmill = Treadmill.dacval
        except Exception as error_message:
            print("treadmill issue\n")
            print(str(error_message))

        ###############################################################################################
        # Keystroke handler
        ###############################################################################################
        # try:
        #     DISPLAYSURF = pygame.display.set_mode((200, 200))
        #     pygame.display.set_caption(session_info["box_name"])
        #     print(
        #         "\nKeystroke handler initiated. In order for keystrokes to register, the pygame window"
        #     )
        #     print("must be in the foreground. Keys are as follows:\n")
        #     print(
        #             Fore.YELLOW
        #             + "         1: left poke            2: center poke            3: right poke"
        #     )
        #     print(
        #         "         Q: left lick            W: center lick            E: right lick"
        #     )
        #     print(
        #             Fore.CYAN
        #             + "                       Esc: close key capture window\n"
        #             + Style.RESET_ALL
        #     )
        #     print(
        #             Fore.GREEN
        #             + Style.BRIGHT
        #             + "         TO EXIT, CLICK THE MAIN TEXT WINDOW AND PRESS CTRL-C "
        #             + Fore.RED
        #             + "ONCE\n"
        #             + Style.RESET_ALL
        #     )
        #
        #     self.keyboard_active = True
        # except Exception as error_message:
        #     print("pygame issue\n")
        #     print(str(error_message))

    ###############################################################################################
    # check for key presses - uses pygame window to simulate nosepokes and licks
    ###############################################################################################

    # def check_keybd(self):
    #     if self.keyboard_active == True:
    #         event = pygame.event.poll()
    #         KeyDown = 768  # event type numbers
    #         KeyUp = 769
    #         if event:
    #             if event.type == KeyDown and event.key == 49:  # 1 key
    #                 self.left_IR_entry()
    #             elif event.type == KeyUp and event.key == 49:
    #                 self.left_IR_exit()
    #             elif event.type == KeyDown and event.key == 50:  # 2 key
    #                 self.center_IR_entry()
    #             elif event.type == KeyUp and event.key == 50:
    #                 self.center_IR_exit()
    #             elif event.type == KeyDown and event.key == 51:  # 3 key
    #                 self.right_IR_entry()
    #             elif event.type == KeyUp and event.key == 51:
    #                 self.right_IR_exit()
    #             elif event.type == KeyDown and event.key == 27:  # escape key
    #                 pygame.quit()
    #                 self.keyboard_active = False
    #             print(event) # for debug purpose

    ###############################################################################################
    # methods to start and stop video
    # These work with fake video files but haven't been tested with real ones
    ###############################################################################################
    def video_start(self):
        IP_address_video = self.IP_address_video
        dir_name = self.session_info['dir_name']
        basename = self.session_info['basename']
        file_name = dir_name + "/" + basename
        # print(Fore.RED + '\nTEST - RED' + Style.RESET_ALL)

        # create directory on the external storage
        base_dir = self.session_info['external_storage'] + '/'
        hd_dir = base_dir + basename
        os.mkdir(hd_dir)

        # Preview check per Kelly request
        print(Fore.YELLOW + "Killing any python process prior to this session!\n" + Style.RESET_ALL)
        try:
            os.system("ssh pi@" + IP_address_video + " pkill python")
            print(Fore.CYAN + "\nStart Previewing ..." + Style.RESET_ALL)
            print(Fore.RED + "\n CRTL + C to quit previewing and start recording" + Style.RESET_ALL)

            os.system("ssh pi@" + IP_address_video + " '/home/pi/RPi4_behavior_boxes/start_preview.py'")
            # Kill any python process before start recording
            print(Fore.GREEN + "\nKilling any python process before start recording!" + Style.RESET_ALL)

            os.system("ssh pi@" + IP_address_video + " pkill python")
            time.sleep(2)

            # Prepare the path for recording
            os.system("ssh pi@" + IP_address_video + " mkdir " + dir_name)
            os.system("ssh pi@" + IP_address_video + " 'date >> ~/video/videolog.log' ")  # I/O redirection
            tempstr = (
                    "ssh pi@" + IP_address_video + " 'nohup /home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition.py "
                    + file_name
                    + " >> ~/video/videolog.log 2>&1 & ' "  # file descriptors
            )
            # start the flipper before the recording start
            # initiate the flipper
            try:
                self.flipper.flip()
            except:
                pass
            # start recording
            print(Fore.GREEN + "\nStart Recording!" + Style.RESET_ALL)
            os.system(tempstr)
            print(
                Fore.RED + Style.BRIGHT + "Please check if the preview screen is on! Cancel the session if it's not!" + Style.RESET_ALL)

            # start initiating the dumping of the session information when available
            scipy.io.savemat(hd_dir + "/" + basename + '_session_info.mat', {'session_info': self.session_info})
            print("dumping session_info")
            pickle.dump(self.session_info, open(hd_dir + "/" + basename + '_session_info.pkl', "wb"))

        except Exception as e:
            print(e)

    def video_stop(self):
        # Get the basename from the session information
        basename = self.session_info['basename']
        dir_name = self.session_info['dir_name']
        # Get the ip address for the box video:
        IP_address_video = self.IP_address_video
        try:
            # Run the stop_video script in the box video
            os.system(
                "ssh pi@" + IP_address_video + " /home/pi/RPi4_behavior_boxes/video_acquisition/stop_acquisition.sh")
            time.sleep(2)
            # now stop the flipper after the video stopped recording
            try:  # try to stop the flipper
                self.flipper.close()
            except:
                pass
            time.sleep(2)

            hostname = socket.gethostname()
            print("Moving video files from " + hostname + "video to " + hostname + ":")

            # Create a directory for storage on the hard drive mounted on the box behavior
            base_dir = self.session_info['external_storage'] + '/'
            hd_dir = base_dir + basename

            scipy.io.savemat(hd_dir + "/" + basename + '_session_info.mat', {'session_info': self.session_info})
            print("dumping session_info")
            pickle.dump(self.session_info, open(hd_dir + "/" + basename + '_session_info.pkl', "wb"))

            # Move the video + log from the box_video SD card to the box_behavior external hard drive
            os.system(
                "rsync -av --progress --remove-source-files pi@" + IP_address_video + ":" + dir_name + "/ "
                + hd_dir
            )
            os.system(
                "rsync -av --progress --remove-source-files pi@" + IP_address_video + ":~/video/*.log "
                + hd_dir
            )
            print("rsync finished!")

        except Exception as e:
            print(e)

    ###############################################################################################
    # method to start and stop vacuum
    ###############################################################################################
    def vacuum_on(self):
        self.cueLED2.on()
        self.event_list.append("vacuum_ON")
        logging.info(str(time.time()) + ", vacuum ON!")

    def vacuum_off(self):
        self.cueLED2.off()
        self.event_list.append("vaccum_OFF")
        logging.info(str(time.time()) + ", vacuum OFF!")

    ###############################################################################################
    # callbacks
    ###############################################################################################
    def left_IR_entry(self):
        self.event_list.append("left_IR_entry")
        logging.info(str(time.time()) + ", left_IR_entry")

    def center_IR_entry(self):
        self.event_list.append("center_IR_entry")
        logging.info(str(time.time()) + ", center_IR_entry")

    def right_IR_entry(self):
        self.event_list.append("right_IR_entry")
        logging.info(str(time.time()) + ", right_IR_entry")

    def left_IR_exit(self):
        self.event_list.append("left_IR_exit")
        logging.info(str(time.time()) + ", left_IR_exit")

    def center_IR_exit(self):
        self.event_list.append("center_IR_exit")
        logging.info(str(time.time()) + ", center_IR_exit")

    def right_IR_exit(self):
        self.event_list.append("right_IR_exit")
        logging.info(str(time.time()) + ", right_IR_exit")

    # def left_lick_start(self):
    #     self.event_list.append("left_lick_start")
    #     logging.info(str(time.time()) + ", left_lick_start")
    #
    # def center_lick_start(self):
    #     self.event_list.append("center_lick_start")
    #     logging.info(str(time.time()) + ", center_lick_start")
    #
    # def right_lick_start(self):
    #     self.event_list.append("right_lick_start")
    #     logging.info(str(time.time()) + ", right_lick_start")
    #
    # def left_lick_stop(self):
    #     self.event_list.append("left_lick_stop")
    #     logging.info(str(time.time()) + ", left_lick_stop")
    #
    # def center_lick_stop(self):
    #     self.event_list.append("center_lick_stop")
    #     logging.info(str(time.time()) + ", center_lick_stop")
    #
    # def right_lick_stop(self):
    #     self.event_list.append("right_lick_stop")
    #     logging.info(str(time.time()) + ", right_lick_stop")


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


class Pump(object):
    def __init__(self):

        ###############################################################################################
        # syringe pumps
        ###############################################################################################
        self.pump1 = LED(19)  # for testing only - the correct pin number is 19
        self.pump2 = LED(20)
        self.pump3 = LED(21)
        self.pump4 = LED(8)
        self.pump5 = LED(7)
        self.pump_en = LED(25)  # pump enable

    def reward(self, which_pump, reward_size, reward_duration):
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
        # reward_duration = 1  # delivery reward over 300 ms
        cycle_length = (
                reward_duration / totalSteps
        )  # need to know what the minimum value can be

        if which_pump == "left":
            self.pump1.blink(cycle_length * 0.1, cycle_length * 0.9, totalSteps)
            logging.info(str(time.time()) + ", left_reward ")
        elif which_pump == "center":
            self.pump2.blink(cycle_length * 0.1, cycle_length * 0.9, totalSteps)
            logging.info(str(time.time()) + ", center_reward ")
        elif which_pump == "right":
            logging.info(str(time.time()) + ", right_reward ")
            self.pump3.blink(cycle_length * 0.1, cycle_length * 0.9, totalSteps)