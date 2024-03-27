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
        try:
            # set up the external hard drive path for the flipper output
            self.session_info = session_info
            storage_path = self.session_info['external_storage'] + '/' + self.session_info['basename']
            self.session_info['flipper_filename'] = storage_path + '/' + self.session_info['basename'] + '_flipper_output'

            # make data directory and initialize logfile
            os.makedirs(session_info['dir_name'])
            os.chdir(session_info['dir_name'])
            session_info['file_basename'] = session_info['dir_name'] + '/' + session_info['mouse_name'] + "_" + session_info['datetime']
            logging.basicConfig(
                level = logging.INFO,
                format = "%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
                datefmt = ('%H:%M:%S'),
                handlers = [
                    logging.FileHandler(session_info['file_basename'] + '.log'),
                    logging.StreamHandler()  # sends copy of log output to screen
                ]
            )
            logging.info(";" + str(time.time()) + "; behavior_box_initialized")
        except Exception as error_message:
            print("Logging error")
            print(str(error_message))

        from subprocess import check_output
        IP_address = check_output(['hostname', '-I']).decode('ascii')[:-2]
        self.IP_address = IP_address
        IP_address_video_list = list(IP_address)
        # IP_address_video_list[-3] = "2"
        IP_address_video_list[-1] = "2"
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
        # digital I/O's - used for cue LED
        # cue for animals
        # DIO 1 and 2 are reserved for the audio board
        ###############################################################################################
        # self.DIO3 = LED(9)  # reserved for vacuum function
        self.DIO4 = LED(10)
        self.DIO5 = LED(11)
        # there is a DIO6, but that is the same pin as the camera strobe

        ###############################################################################################
        # IR detection (for licks)
        ###############################################################################################
        self.IR_rx1 = Button(5, None, True)  # None, True inverts the signal so poke=True, no-poke=False
        self.IR_rx2 = Button(6, None, True)
        self.IR_rx3 = Button(12, None, True)
        # self.IR_rx4 = Button(13, None, True)  # (optional, reserved for future use)
        # self.IR_rx5 = Button(16, None, True)  # (optional, reserved for future use)

        # link nosepoke event detections to callbacks (exit and entry are opposite to pressed and release)
        self.IR_rx1.when_pressed = self.left_IR_exit
        self.IR_rx2.when_pressed = self.center_IR_exit
        self.IR_rx3.when_pressed = self.right_IR_exit
        self.IR_rx1.when_released = self.left_IR_entry
        self.IR_rx2.when_released = self.center_IR_entry
        self.IR_rx3.when_released = self.right_IR_entry

        ###############################################################################################
        # Closed circuit detection for lick
        self.lick1 = Button(26, None, True)
        self.lick2 = Button(27, None, True)
        self.lick3 = Button(15, None, True)

        # Link lick detection event to callbacks
        self.lick1.when_pressed = self.left_exit
        self.lick2.when_pressed = self.right_exit
        self.lick3.when_pressed = self.center_exit

        self.lick1.when_released = self.left_entry
        self.lick2.when_released = self.right_entry
        self.lick3.when_released = self.center_entry

        ###############################################################################################
        # sound: audio board DIO - pins sending TTL to the Tsunami soundboard via SMA connectors
        ###############################################################################################
        # pins originally reserved for the lick detection is now used for audio board TTL input signal
        # NEW EDIT: switch sound to lick
        """""
        self.sound1 = LED(26)  # originally lick1
        self.sound2 = LED(27)  # originally lick2
        self.sound3 = LED(15)  # originally lick3
        """
        self.sound1 = LED(23)  # new_lick modification
        self.sound2 = LED(24)  # new_lick modification

        #################################################################################################
        # pump: trigger signal output to a driver board induce the solenoid valve to deliver reward
        # ###############################################################################################
        self.pump = Pump()

        ###############################################################################################
        # flipper strobe signal
        ###############################################################################################
        # initializing flipper object
        try:
            self.flipper = FlipperOutput(self.session_info, pin=4)
        except Exception as error_message:
            print("flipper issue\n")
            print(str(error_message))

        ###############################################################################################
        # visual stimuli initiation
        ###############################################################################################
        try:
            # self.visualstim = VisualStim(self.session_info)
            self.visualstim_go = VisualStim_go(self.session_info)
            self.visualstim_nogo = VisualStim_nogo(self.session_info)
        except Exception as error_message:
            print("visualstim issue\n")
            print(str(error_message))

        ###############################################################################################
        # ADC (Adafruit_ADS1x15) setup
        ###############################################################################################
        try:
            self.ADC = ADS1x15.ADS1015
        except Exception as error_message:
            print("ADC issue\n")
            print(str(error_message))

        # ###############################################################################################
        # Treadmill setup
        # ###############################################################################################
        if session_info['treadmill'] == True:
            try:
                self.treadmill = Treadmill.Treadmill(self.session_info)
            except Exception as error_message:
                print("treadmill issue\n")
                print(str(error_message))
        else:
            self.treadmill = False
            print("No treadmill I2C connected detected!")

    ###############################################################################################
    # methods to start and stop video
    # These work with fake video files but haven't been tested with real ones
    ###############################################################################################
    def video_start(self):
        print("Starting fake video")
        try:
            self.flipper.flip()
        except Exception as error_message:
            print("flipper can't run\n")
            print(str(error_message))

    def video_stop(self):
        print("Stopping fake video")
        try:  # try to stop the flipper
            self.flipper.close()
        except:
            pass
        time.sleep(2)

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

    def left_entry(self):
        self.event_list.append("left_entry")
        logging.info(str(time.time()) + ", left_entry")

    def center_entry(self):
        self.event_list.append("center_entry")
        logging.info(str(time.time()) + ", center_entry")

    def right_entry(self):
        self.event_list.append("right_entry")
        logging.info(str(time.time()) + ", right_entry")

    def left_exit(self):
        self.event_list.append("left_exit")
        logging.info(str(time.time()) + ", left_exit")

    def center_exit(self):
        self.event_list.append("center_exit")
        logging.info(str(time.time()) + ", center_exit")

    def right_exit(self):
        self.event_list.append("right_exit")
        logging.info(str(time.time()) + ", right_exit")


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
        self.pump1 = LED(19)  # for testing only - the correct pin number is 19
        self.pump2 = LED(20)
        self.pump3 = LED(21)
        self.pump4 = LED(7)
        self.pump_air = LED(8)
        self.pump_vacuum = LED(25)

    def reward(self, which_pump, on_time, off_time, numtimes):
        # coefficient_fit = np.array([8.78674242e-04, 7.33609848e-02, 1.47535000e+00]) # further calibration is needed
        # coefficient_1 = coefficient_fit[-1]
        # coefficient_2 = coefficient_fit[-2]
        # coefficient_3 = coefficient_fit[-3] - reward_size
        tube_fit = 0.11609  # ml/s
        # discriminant = coefficient_2 ** 2 - 4 * coefficient_1 * coefficient_3
        # # find solution, i.e. duration of pulse, by calculating the solution for the quadratic equation
        # solution = np.array([(-coefficient_2 + np.sqrt(discriminant)) / (2 * coefficient_1),
        #                      (-coefficient_2 - np.sqrt(discriminant)) / (2 * coefficient_1)])

        # With two solution, get the positive value
        # solution_positive = solution[(solution > 0).nonzero()[0][0]]
        # round to the second decimal
        # duration = round(solution_positive, 3) * (10**-3)

        duration_vacuum = 0.1  # in seconds

        if which_pump == "1":
            self.pump1.blink(on_time, off_time, numtimes)
            logging.info(str(time.time()) + ", pump1_reward")
        elif which_pump == "2":
            self.pump2.blink(on_time, off_time, numtimes)
            logging.info(str(time.time()) + ", pump2_reward")
        elif which_pump == "3":
            self.pump3.blink(on_time, off_time, numtimes)
            logging.info(str(time.time()) + ", pump3_reward")
        elif which_pump == "4":
            self.pump4.blink(on_time, off_time, numtimes)
            logging.info(str(time.time()) + ", pump4_reward")
        elif which_pump == "air_puff":
            self.pump_air.blink(on_time, off_time, numtimes)
            logging.info(str(time.time()) + ", air_puff")
        elif which_pump == "vacuum":
            self.pump_vacuum.blink(on_time, off_time, numtimes)
            logging.info(str(time.time()) + ", vacuum")