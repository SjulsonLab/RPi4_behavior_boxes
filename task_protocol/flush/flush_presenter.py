from typing import List, Tuple

from icecream import ic
import time
import logging
import threading
from threading import Thread
from essential.base_classes import Presenter, Model, GUI, Box, PumpBase

PUMP1_IX = 0
PUMP2_IX = 1
trial_choice_map = {'right': 0, 'left': 1}


class FlushPresenter(Presenter):

    def __init__(self, model: Model, box: Box, pump: PumpBase, gui: GUI, session_info: dict):
        self.task: Model = model
        self.gui: GUI = gui
        self.box = box
        self.pump = pump
        self.session_info = session_info
        self.pump_keys = (session_info["reward_pump1"], session_info['reward_pump2'])
        self.reward_size = 20
        self.interact_list = []

        self.LED_is_on = False
        self.sound1_is_on = False
        self.sound2_is_on = False
        # self.gratings_on = False
        # self.stimulus_A_thread = None
        # self.stimulus_B_thread = None

    def run(self) -> None:
        self.task.run_event_loop()
        self.perform_task_commands()
        self.check_keyboard()

    def LEDs_on(self):
        self.box.cueLED1.on()
        self.box.cueLED2.on()
        self.LED_is_on = True
        ic("LEDs on")

    def LEDs_off(self):
        self.box.cueLED1.off()
        self.box.cueLED2.off()
        self.LED_is_on = False
        ic("LEDs off")

    def sound1_on(self):
        self.box.sound2.off()
        self.box.sound1.on()
        self.sound1_is_on = True
        self.sound2_is_on = False
        ic("sound 1 on")

    def sound2_on(self):
        self.box.sound1.off()
        self.box.sound2.on()
        self.sound1_is_on = False
        self.sound2_is_on = True
        ic("sound 2 on")

    def sounds_off(self) -> None:
        self.box.sound1.off()
        self.box.sound2.off()
        self.sound1_is_on = False
        self.sound2_is_on = False
        ic("sounds off")

    def perform_task_commands(self) -> None:
        for c in self.task.presenter_commands:
            if c == 'toggle_right_water':
                logging.info(";" + str(time.time()) + ";[reward];toggling_right_water;" + str(""))
                self.pump.toggle(self.pump_keys[PUMP1_IX])

            elif c == 'toggle_left_water':
                logging.info(";" + str(time.time()) + ";[reward];giving_left_reward;" + str(""))
                self.pump.blink(self.pump_keys[PUMP2_IX], self.session_info['flush_duration'])

            elif c == 'toggle_sound1':
                self.box.sound1.toggle()

            elif c == 'toggle_sound2':
                self.box.sound2.toggle()
                # if self.sound1_is_on:
                #     pass
                # else:
                #     logging.info(";" + str(time.time()) + ";[action];blinking_sound1;" + str(""))
                #     # self.sound1_on()
                #     self.box.sound1.toggle()
                #     threading.Timer(1, self.sounds_off).start()

            # elif c == 'blink_sound2':
            #     if self.sound2_is_on:
            #         pass
            #     else:
            #         logging.info(";" + str(time.time()) + ";[action];blinking_sound2;" + str(""))
            #         self.sound2_on()
            #         threading.Timer(1, self.sounds_off).start()

            elif c == 'toggle_LED':
                self.box.cueLED1.toggle()
                self.box.cueLED2.toggle()

            else:
                logging.info(";" + str(time.time()) + ";[action];unknown_command;" + str(c))
                ic("Unknown command:", c)

        self.task.presenter_commands.clear()

    def K_z_callback(self) -> None:
        self.task.presenter_commands.append('toggle_sound1')
        logging.info(";" + str(time.time()) + ";[action];user_triggered_sound1_on;" + str(""))

    def K_x_callback(self) -> None:
        self.task.presenter_commands.append('toggle_sound2')
        logging.info(";" + str(time.time()) + ";[action];user_triggered_sound2_on;" + str(""))

    def K_l_callback(self) -> None:
        self.task.presenter_commands.append('toggle_LED')
        logging.info(";" + str(time.time()) + ";[action];toggle_LED")

    def end_ITI(self):
        self.ITI_active = False
        self.LEDs_on()

    def print_controls(self) -> None:
        print("[***] KEYBOARD CONTROLS [***]")
        print("1, 3: left/right nosepoke entry + 1s reward delivery")
        print("q, w, e, r: pump 1/2/3/4 reward delivery")
        print("t: vacuum activation")
        print("l: toggle LED")
        print("z, x: sound 1 (white noise) / 2 (beep) on")
