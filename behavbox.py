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
import os
import socket
import time
from collections import deque
import pygame
import pygame.display

import numpy as np
import matplotlib
matplotlib.use('module://pygame_matplotlib.backend_pygame')
import matplotlib.pyplot as plt
import matplotlib.figure as fg

import logging
from colorama import Fore, Style
from visualstim import VisualStim

import scipy.io, pickle

import Treadmill
import ADS1x15

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
            logging.info(";" + str(time.time()) + ";[initialization];behavior_box_initialized")
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
        # event list trigger by the interaction between the RPi and the animal for visualization
        # interact_list: lick, choice interaction between the board and the animal for visualization
        ###############################################################################################
        self.interact_list = []

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

        # link nosepoke event detections to callbacks
        self.IR_rx1.when_pressed = self.IR_1_entry
        self.IR_rx2.when_pressed = self.IR_2_entry
        self.IR_rx3.when_pressed = self.IR_3_entry
        self.IR_rx4.when_pressed = self.IR_4_entry
        self.IR_rx5.when_pressed = self.IR_5_entry
        self.IR_rx1.when_released = self.IR_1_exit
        self.IR_rx2.when_released = self.IR_2_exit
        self.IR_rx3.when_released = self.IR_3_exit
        self.IR_rx4.when_released = self.IR_4_exit
        self.IR_rx5.when_released = self.IR_5_exit
        ###############################################################################################
        # IR detection - for nosepoke detection
        ###############################################################################################
        self.lick1 = Button(26, None, True)
        self.lick2 = Button(27, None, True)
        self.lick3 = Button(15, None, True)
        #self.reserved_rx1 = Button(13, None, True)  # for mitch
        #self.reserved_rx2 = Button(16, None, True)  # for mitch
        #
        # # link nosepoke event detections to callbacks
        self.lick1.when_pressed = self.left_exit
        self.lick2.when_pressed = self.right_exit
        self.lick3.when_pressed = self.center_exit

        self.lick1.when_released = self.left_entry
        self.lick2.when_released = self.right_entry
        self.lick3.when_released = self.center_entry

        # self.reserved_rx1.when_pressed = self.reserved_rx1_pressed
        # self.reserved_rx2.when_pressed = self.reserved_rx2_pressed
        # self.reserved_rx1.when_released = self.reserved_rx1_released
        # self.reserved_rx2.when_released = self.reserved_rx2_released

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
        self.sound1 = LED(23) # branch new_lick modification
        self.sound2 = LED(24) # branch new_lick modification

        ###############################################################################################
        # pump: trigger signal output to a driver board induce the solenoid valve to deliver reward
        ###############################################################################################
        self.pump = Pump(self.session_info)

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
                self.visualstim = VisualStim(self.session_info)
            except Exception as error_message:
                print("visualstim issue\n")
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
        ###############################################################################################
        # pygame window setup and keystroke handler
        ###############################################################################################
        try:
            pygame.init()
            self.main_display = pygame.display.set_mode((800, 600))
            pygame.display.set_caption(session_info["box_name"])
            fig, axes = plt.subplots(1, 1, )
            axes.plot()
            self.check_plot(fig)
            print(
                "\nKeystroke handler initiated. In order for keystrokes to register, the pygame window"
            )
            print("must be in the foreground. Keys are as follows:\n")
            print(
                Fore.YELLOW
                + "         1: left poke            2: center poke            3: right poke"
            )
            print(
                "         Q: pump_1            W: pump_2            E: pump_3            R: pump_4"
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
        except Exception as error_message:
            print("pygame issue\n")
            print(str(error_message))
    ###############################################################################################
    # check for data visualization - uses pygame window to show behavior progress
    ###############################################################################################
    """
    1. show a blank window. (change in the pygame initiation part)
    2. show a x,y axis with a count of trial
    """
    def check_plot(self, figure=None, FPS=144):
        if figure:
            FramePerSec = pygame.time.Clock()
            figure.canvas.draw()
            self.main_display.blit(figure, (0, 0))
            pygame.display.update()
            FramePerSec.tick(FPS)
        else:
            print("No figure available")

    ###############################################################################################
    # check for key presses - uses pygame window to simulate nosepokes and licks
    ###############################################################################################

    def check_keybd(self):
        reward_size = self.session_info['reward_size']
        # pump = Pump()
        if self.keyboard_active:
            # event = pygame.event.get()
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.keyboard_active = False
                    elif event.key == pygame.K_1:
                        self.left_entry()
                        self.left_IR_entry()
                        logging.info(";" + str(time.time()) + ";[action];key_pressed_left_entry()")
                    elif event.key == pygame.K_2:
                        self.center_entry()
                        self.center_IR_entry()
                        logging.info(";" + str(time.time()) + ";[action];key_pressed_center_entry()")
                    elif event.key == pygame.K_3:
                        self.right_entry()
                        self.right_IR_entry()
                        logging.info(";" + str(time.time()) + ";[action];key_pressed_right_entry()")
                    # elif event.key == pygame.K_4:
                    #     self.reserved_rx1_pressed()
                    #     logging.info(";" + str(time.time()) + ";[action];key_pressed_reserved_rx1_pressed()")
                    # elif event.key == pygame.K_5:
                    #     self.reserved_rx2_pressed()
                    #     logging.info(";" + str(time.time()) + ";[action];key_pressed_reserved_rx2_pressed()")
                    elif event.key == pygame.K_q:
                        # print("Q down: syringe pump 1 moves")
                        logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump1")
                        self.pump.reward("1", 5)
                    elif event.key == pygame.K_w:
                        # print("W down: syringe pump 2 moves")
                        logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump2")
                        self.pump.reward("2", 5)
                    elif event.key == pygame.K_e:
                        # print("E down: syringe pump 3 moves")
                        logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump3")
                        self.pump.reward("3", 5)
                    elif event.key == pygame.K_r:
                        # print("R down: syringe pump 4 moves")
                        logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump4")
                        self.pump.reward("4", 5)
                    elif event.key == pygame.K_t:
                        # print("T down: vacuum on")
                        logging.info(";" + str(time.time()) + ";[reward];key_pressed_pump_vacuum")
                        self.pump.reward("vacuum", 1)
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_1:
                        self.left_exit()
                    elif event.key == pygame.K_2:
                        self.center_exit()
                    elif event.key == pygame.K_3:
                        self.right_exit()

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

    ###############################################################################################
    # callbacks
    ###############################################################################################
    def left_entry(self):
        self.event_list.append("left_entry")
        self.interact_list.append((time.time(), "left_entry"))
        logging.info(";" + str(time.time()) + ";[action];left_entry")

    def center_entry(self):
        self.event_list.append("center_entry")
        self.interact_list.append((time.time(), "center_entry"))
        logging.info(";" + str(time.time()) + ";[action];center_entry")

    def right_entry(self):
        self.event_list.append("right_entry")
        self.interact_list.append((time.time(), "right_entry"))
        logging.info(";" + str(time.time()) + ";[action];right_entry")

    def left_exit(self):
        self.event_list.append("left_exit")
        self.interact_list.append((time.time(), "left_exit"))
        logging.info(";" + str(time.time()) + ";[action];left_exit")

    def center_exit(self):
        self.event_list.append("center_exit")
        self.interact_list.append((time.time(), "center_exit"))
        logging.info(";" + str(time.time()) + ";[action];center_exit")

    def right_exit(self):
        self.event_list.append("right_exit")
        self.interact_list.append((time.time(), "right_exit"))
        logging.info(";" + str(time.time()) + ";[action];right_exit")

    # def reserved_rx1_pressed(self):
    #     self.event_list.append("reserved_rx1_pressed")
    #     self.interact_list.append((time.time(), "reserved_rx1_pressed"))
    #     logging.info(";" + str(time.time()) + ";[action];reserved_rx1_pressed")
    #
    # def reserved_rx2_pressed(self):
    #     self.event_list.append("reserved_rx2_pressed")
    #     self.interact_list.append((time.time(), "reserved_rx2_pressed"))
    #     logging.info(";" + str(time.time()) + ";[action];reserved_rx2_pressed")
    #
    # def reserved_rx1_released(self):
    #     self.event_list.append("reserved_rx1_released")
    #     self.interact_list.append((time.time(), "reserved_rx1_released"))
    #     logging.info(";" + str(time.time()) + ";[action];reserved_rx1_released")
    #
    # def reserved_rx2_released(self):
    #     self.event_list.append("reserved_rx2_released")
    #     self.interact_list.append((time.time(), "reserved_rx2_released"))
    #     logging.info(";" + str(time.time()) + ";[action];reserved_rx2_released")
    def IR_1_entry(self):
        self.event_list.append("IR_1_entry")
        logging.info(str(time.time()) + ", IR_1_entry")

    def IR_2_entry(self):
        self.event_list.append("IR_2_entry")
        logging.info(str(time.time()) + ", IR_2_entry")

    def IR_3_entry(self):
        self.event_list.append("IR_3_entry")
        logging.info(str(time.time()) + ", IR_3_entry")

    def IR_4_entry(self):
        self.event_list.append("IR_4_entry")
        logging.info(str(time.time()) + ", IR_4_entry")

    def IR_5_entry(self):
        self.event_list.append("IR_5_entry")
        logging.info(str(time.time()) + ", IR_5_entry")

    def IR_1_exit(self):
        self.event_list.append("IR_1_exit")
        logging.info(str(time.time()) + ", IR_1_exit")

    def IR_2_exit(self):
        self.event_list.append("IR_2_exit")
        # self.cueLED2.off()
        logging.info(str(time.time()) + ", IR_2_exit")

    def IR_3_exit(self):
        self.event_list.append("IR_3_exit")
        logging.info(str(time.time()) + ", IR_3_exit")

    def IR_4_exit(self):
        self.event_list.append("IR_4_exit")
        logging.info(str(time.time()) + ", IR_4_exit")

    def IR_5_exit(self):
        self.event_list.append("IR_5_exit")
        logging.info(str(time.time()) + ", IR_5_exit")

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
    def __init__(self, session_info):
        self.session_info = session_info
        self.pump1 = LED(19)
        self.pump2 = LED(20)
        self.pump3 = LED(21)
        self.pump4 = LED(7)
        self.pump_air = LED(8)
        self.pump_vacuum = LED(25)
        self.reward_list = [] # a list of tuple (pump_x, reward_amount) with information of reward history for data
        # visualization

    def reward(self, which_pump, reward_size):
        # import coefficient from the session_information
        coefficient_p1 = self.session_info["calibration_coefficient"]['1']
        coefficient_p2 = self.session_info["calibration_coefficient"]['2']
        coefficient_p3 = self.session_info["calibration_coefficient"]['3']
        coefficient_p4 = self.session_info["calibration_coefficient"]['4']
        duration_air = self.session_info['air_duration']
        duration_vac = self.session_info["vacuum_duration"]


        if which_pump == "1":
            duration = round((coefficient_p1[0] * (reward_size / 1000) + coefficient_p1[1]), 3)  # linear function
            self.pump1.blink(duration, 0.1, 1)
            self.reward_list.append(("pump1_reward", reward_size))
            logging.info(";" + str(time.time()) + ";[reward];pump1_reward_" + str(reward_size))
        elif which_pump == "2":
            duration = round((coefficient_p2[0] * (reward_size / 1000) + coefficient_p2[1]), 3)  # linear function
            self.pump2.blink(duration, 0.1, 1)
            self.reward_list.append(("pump2_reward", reward_size))
            logging.info(";" + str(time.time()) + ";[reward];pump2_reward_" + str(reward_size))
        elif which_pump == "3":
            duration = round((coefficient_p3[0] * (reward_size / 1000) + coefficient_p3[1]), 3)  # linear function
            self.pump3.blink(duration, 0.1, 1)
            self.reward_list.append(("pump3_reward", reward_size))
            logging.info(";" + str(time.time()) + ";[reward];pump3_reward_" + str(reward_size))
        elif which_pump == "4":
            duration = round((coefficient_p4[0] * (reward_size / 1000) + coefficient_p4[1]), 3)  # linear function
            self.pump4.blink(duration, 0.1, 1)
            self.reward_list.append(("pump4_reward", reward_size))
            logging.info(";" + str(time.time()) + ";[reward];pump4_reward_" + str(reward_size))
        elif which_pump == "air_puff":
            self.pump_air.blink(duration_air, 0.1, 1)
            self.reward_list.append(("air_puff", reward_size))
            logging.info(";" + str(time.time()) + ";[reward];pump4_reward_" + str(reward_size))
        elif which_pump == "vacuum":
            self.pump_vacuum.blink(duration_vac, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[reward];pump_vacuum" + str(duration_vac))