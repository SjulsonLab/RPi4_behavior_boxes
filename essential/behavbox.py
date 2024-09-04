# python3: behavbox.py
"""
author: tian qiu
date: 2022-05-15
name: behavbox.py
goal: base framework for running wide range of behavioral task
description:
    an updated test version for online behavior performance visualization
"""

# contains the behavior box class, which includes pin numbers and whether DIO pins are
# configured as input or output

from gpiozero import PWMLED, LED, Button
import os, sys
import socket
import time
from collections import deque
from icecream import ic

import logging
from colorama import Fore, Style

from essential.visualstim import VisualStim
from essential.visual_stimuli.visualstim_concurrent import VisualStimMultiprocess

# sys.path.insert(0, '.')  # essential (this folder) holds behavbox and equipment classes

import scipy.io, pickle

import Treadmill
import ADS1x15

# for the flipper
from FlipperOutput import FlipperOutput
from base_classes import Presenter, PumpBase, Box
from typing import List, Tuple, Union, Dict, Any


class BehavBox(Box):
    event_list = (
        deque()
    )  # all detected events are added to this queue to be read out by the behavior class

    def __init__(self, session_info):
        try:
            # set up the external hard drive path for the flipper output
            self.session_info = session_info
            storage_path = self.session_info['external_storage'] + '/' + self.session_info['basename']
            self.session_info['flipper_filename'] = storage_path + '/' + self.session_info[
                'basename'] + '_flipper_output'

            # make data directory and initialize logfile
            os.makedirs(session_info['dir_name'])
            os.chdir(session_info['dir_name'])
            session_info['file_basename'] = session_info['dir_name'] + '/' + session_info['mouse_name'] + "_" + session_info['datetime']
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
                datefmt=('%H:%M:%S'),
                handlers=[
                    logging.FileHandler(session_info['file_basename'] + '.log'),
                    logging.StreamHandler()  # sends copy of log output to screen
                ]
            )
            logging.info(";" + str(time.time()) + ";[initialization];behavior_box_initialized;")
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
        # IR detection - for nosepoke
        ###############################################################################################
        self.IR_rx1 = Button(5, None, True)  # None, True inverts the signal so poke=True, no-poke=False
        self.IR_rx2 = Button(6, None, True)
        self.IR_rx3 = Button(12, None, True)
        self.IR_rx4 = Button(13, None, True)  # (optional, reserved for future use
        self.IR_rx5 = Button(16, None, True)  # (optional, reserved for future use


        ###############################################################################################
        # close circuit detection - for ground pin circuit lick detection
        ###############################################################################################
        self.lick1 = Button(26, None, True)
        self.lick2 = Button(27, None, True)
        self.lick3 = Button(15, None, True)
        #self.reserved_rx1 = Button(13, None, True)  # for mitch
        #self.reserved_rx2 = Button(16, None, True)  # for mitch

        ###############################################################################################
        # sound: audio board DIO - pins sending TTL to the Tsunami soundboard via SMA connectors
        ###############################################################################################
        # pins originally reserved for the lick detection is now used for audio board TTL input signal
        # NEW EDIT: switch sound to lick
        """
        self.sound1 = LED(26)  # originally lick1
        self.sound2 = LED(27)  # originally lick2
        self.sound3 = LED(15)  # originally lick3
        """
        self.sound1 = LED(23)  # branch new_lick modification
        self.sound2 = LED(24)  # branch new_lick modification

        ###############################################################################################
        # flipper strobe signal (previously called camera strobe signal)
        ###############################################################################################
        # previously: self.camera_strobe = Button(4)
        # previously: rising and falling edges are detected and logged in a separate video file
        # initiating flipper object
        try:
            self.flipper = FlipperOutput(self.session_info, pin=4)
        except Exception as error_message:
            print("flipper issue\n")
            print(str(error_message))

        ###############################################################################################
        # visual stimuli initiation
        ###############################################################################################
        if self.session_info["visual_stimulus"]:
            try:
                # self.visualstim = VisualStimMultiprocess(self.session_info)
                self.visualstim = VisualStim(self.session_info)
            except Exception as error_message:
                print("visualstim issue - module not loaded \n")
                print(str(error_message))
        else:
            pass
        ###############################################################################################
        # ADC(Adafruit_ADS1x15) setup
        ###############################################################################################
        try:
            self.ADC = ADS1x15.ADS1015
        except Exception as error_message:
            print("ADC issue\n")
            print(str(error_message))

        # ###############################################################################################
        # # treadmill setup
        # ###############################################################################################
        if session_info['treadmill'] == True:
            try:
                self.treadmill = Treadmill.Treadmill(self.session_info)
            except Exception as error_message:
                print("treadmill issue\n")
                # print("Ignore following erro if no treadmill is connected: ")
                print(str(error_message))
        else:
            self.treadmill = False
            print("No treadmill I2C connection detected!")

    def set_callbacks(self, presenter: Presenter):
        # link nosepoke event detections to callbacks
        self.IR_rx1.when_pressed = presenter.IR_1_entry
        self.IR_rx2.when_pressed = presenter.IR_2_entry
        self.IR_rx3.when_pressed = presenter.IR_3_entry
        self.IR_rx4.when_pressed = presenter.IR_4_entry
        self.IR_rx5.when_pressed = presenter.IR_5_entry
        self.IR_rx1.when_released = presenter.IR_1_exit
        self.IR_rx2.when_released = presenter.IR_2_exit
        self.IR_rx3.when_released = presenter.IR_3_exit
        self.IR_rx4.when_released = presenter.IR_4_exit
        self.IR_rx5.when_released = presenter.IR_5_exit

        # This is how it's set in the base code
        # self.lick1.when_pressed = presenter.left_exit
        # self.lick2.when_pressed = presenter.right_exit
        # self.lick3.when_pressed = presenter.center_exit
        #
        # self.lick1.when_released = presenter.left_entry
        # self.lick2.when_released = presenter.right_entry
        # self.lick3.when_released = presenter.center_entry

        # This makes more sense intuitively??
        self.lick1.when_pressed = presenter.left_entry
        self.lick2.when_pressed = presenter.right_entry
        self.lick3.when_pressed = presenter.center_entry

        self.lick1.when_released = presenter.left_exit
        self.lick2.when_released = presenter.right_exit
        self.lick3.when_released = presenter.center_exit

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
            except Exception as error_message:
                print("flipper can't run\n")
                print(str(error_message))

            # Treadmill initiation
            if self.treadmill is not False:
                try:
                    self.treadmill.start()
                except Exception as error_message:
                    print("treadmill can't run\n")
                    print(str(error_message))

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
            if self.treadmill is not False:
                try:  # try to stop recording the treadmill
                    self.treadmill.close()
                except:
                    pass
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

            os.system(
                "rsync -arvz --progress --remove-source-files " + self.session_info['dir_name'] + "/ "
                + hd_dir
            )
            print("rsync finished!")
            # print("Control-C to quit (ignore the error for now)")

        except Exception as e:
            print(e)


# this is for the cue LEDs. BoxLED.value is the intensity value (PWM duty cycle, from 0 to 1)
# currently. BoxLED.set_value is the saved intensity value that determines how bright the
# LED will be if BoxLED.on() is called. This is better than the original PWMLED class.
class BoxLED(PWMLED):
    set_value = 1  # the intensity value, ranging from 0-1
    def on(self):  # unlike PWMLED, here the on() function sets the intensity to set_value,
        # not to full intensity
        self.value = self.set_value


###############################################################################################
# pump: trigger signal output to a driver board induce the solenoid valve to deliver reward
###############################################################################################
class Pump(PumpBase):
    def __init__(self, session_info: Dict[str, Any]):
        self.pump1 = LED(19)
        self.pump2 = LED(20)
        self.pump3 = LED(21)
        self.pump4 = LED(7)
        self.pump_air = LED(8)
        self.pump_vacuum = LED(25)

        # this needs to move to the controller, if it's used at all
        self.reward_list = []  # a list of tuple (pump_x, reward_amount) with information of reward history for data
        # visualization

        self.coefficient_p1 = session_info["calibration_coefficient"]['1']
        self.coefficient_p2 = session_info["calibration_coefficient"]['2']
        self.coefficient_p3 = session_info["calibration_coefficient"]['3']
        self.coefficient_p4 = session_info["calibration_coefficient"]['4']
        self.duration_air = session_info['air_duration']
        self.duration_vac = session_info["vacuum_duration"]

    def blink(self, pump_key: str, on_time: float):
        """Blink a pump-port once for testing purposes."""
        if pump_key in ["1", "key_1"]:
            self.pump1.blink(on_time=on_time, off_time=0.1, n=1)
            logging.info(";" + str(time.time()) + ";[reward];pump1_blink, duration: " + str(on_time) + ";")
        elif pump_key in ["2", "key_2"]:
            self.pump2.blink(on_time=on_time, off_time=0.1, n=1)
            logging.info(";" + str(time.time()) + ";[reward];pump2_blink, duration: " + str(on_time) + ";")
        elif pump_key in ["3", "key_3"]:
            self.pump3.blink(on_time=on_time, off_time=0.1, n=1)
            logging.info(";" + str(time.time()) + ";[reward];pump3_blink, duration: " + str(on_time) + ";")
        elif pump_key in ["4", "key_4"]:
            self.pump4.blink(on_time=on_time, off_time=0.1, n=1)
            logging.info(";" + str(time.time()) + ";[reward];pump4_blink, duration: " + str(on_time) + ";")
        elif pump_key in ["air_puff", "key_air_puff"]:
            self.pump_air.blink(on_time, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[reward];pump_air, duration: " + str(self.duration_air) + ";")
        elif pump_key in ["vacuum", "key_vacuum"]:
            self.pump_vacuum.blink(on_time, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[reward];pump_vacuum, duration: " + str(self.duration_vac) + ";")

    def reward(self, which_pump: str, reward_size: float) -> None:
        if which_pump in ["1", "key_1"]:
            duration = round((self.coefficient_p1[0] * (reward_size / 1000) + self.coefficient_p1[1]),
                             5)  # linear function
            self.pump1.blink(duration, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[reward];pump1_reward(reward_coeff: " + str(self.coefficient_p1) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ");")
        elif which_pump in ["2", "key_2"]:
            duration = round((self.coefficient_p2[0] * (reward_size / 1000) + self.coefficient_p2[1]),
                             5)  # linear function
            self.pump2.blink(duration, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[reward];pump2_reward(reward_coeff: " + str(self.coefficient_p2) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ");")
        elif which_pump in ["3", "key_3"]:
            duration = round((self.coefficient_p3[0] * (reward_size / 1000) + self.coefficient_p3[1]),
                             5)  # linear function
            self.pump3.blink(duration, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[reward];pump3_reward(reward_coeff: " + str(self.coefficient_p3) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ");")
        elif which_pump in ["4", "key_4"]:
            duration = round((self.coefficient_p4[0] * (reward_size / 1000) + self.coefficient_p4[1]),
                             5)  # linear function
            self.pump4.blink(duration, 0.1, 1)
            # self.reward_list.append(("pump4_reward", reward_size))
            logging.info(";" + str(time.time()) + ";[reward];pump4_reward(reward_coeff: " + str(self.coefficient_p4) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ");")
        elif which_pump in ["air_puff", "key_air_puff"]:
            self.pump_air.blink(self.duration_air, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[reward];pump_air" + str(reward_size) + ";")
            # self.reward_list.append(("air_puff", reward_size))
        elif which_pump in ["vacuum", "key_vacuum"]:
            self.pump_vacuum.blink(self.duration_vac, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[reward];pump_vacuum" + str(self.duration_vac) + ";")

    def toggle(self, pump_key: str) -> None:
        if pump_key in ["1", "key_1"]:
            self.pump1.toggle()
            logging.info(";" + str(time.time()) + ";[reward];pump1_toggle;")
            ic(self.pump1.value)
        elif pump_key in ["2", "key_2"]:
            self.pump2.toggle()
            logging.info(";" + str(time.time()) + ";[reward];pump2_toggle;")
            ic(self.pump2.value)
        elif pump_key in ["3", "key_3"]:
            self.pump3.toggle()
            ic(self.pump3.value)
            logging.info(";" + str(time.time()) + ";[reward];pump3_toggle;")
        elif pump_key in ["4", "key_4"]:
            self.pump4.toggle()
            logging.info(";" + str(time.time()) + ";[reward];pump4_toggle;")
            ic(self.pump4.value)
        elif pump_key in ["air_puff", "key_air_puff"]:
            self.pump_air.toggle()
            logging.info(";" + str(time.time()) + ";[reward];pump_air_toggle;")
            ic(self.pump_air.value)
        elif pump_key in ["vacuum", "key_vacuum"]:
            self.pump_vacuum.toggle()
            logging.info(";" + str(time.time()) + ";[reward];pump_vacuum_toggle;")
            ic(self.pump_vacuum.value)


