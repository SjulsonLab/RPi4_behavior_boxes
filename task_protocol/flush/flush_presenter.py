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
        self.gratings_on = False
        self.stimulus_A_thread = None
        self.stimulus_B_thread = None

    def run(self) -> None:
        # self.task.run_event_loop()
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
                logging.info(";" + str(time.time()) + ";[reward];toggling_left_water;" + str(""))
                self.pump.toggle(self.pump_keys[PUMP2_IX])

            elif c == 'toggle_sound1':
                self.box.sound1.toggle()

            elif c == 'toggle_sound2':
                self.box.sound2.toggle()

            elif c == 'toggle_LED':
                self.box.cueLED1.toggle()
                self.box.cueLED2.toggle()

            elif c == 'turn_stimulus_A_on':
                self.stimulus_A_on()

            elif c == 'turn_stimulus_B_on':
                self.stimulus_B_on()

            else:
                logging.info(";" + str(time.time()) + ";[action];unknown_command;" + str(c))
                ic("Unknown command:", c)

        self.task.presenter_commands.clear()

    def stimulus_A_on(self) -> None:
        grating_name = 'vertical_grating_{}s.dat'.format(self.session_info['grating_duration'])
        sound_on_time = 0.1
        self.stimulus_A_thread = Thread(target=self.stimulus_loop, args=(grating_name, sound_on_time, self.stimulus_B_thread))
        logging.info(";" + str(time.time()) + ";[stimulus];" + "stimulus_A_on")
        self.stimulus_A_thread.start()

    def stimulus_B_on(self) -> None:
        grating_name = 'horizontal_grating_{}s.dat'.format(self.session_info['grating_duration'])
        sound_on_time = 0.2
        self.stimulus_B_thread = Thread(target=self.stimulus_loop, args=(grating_name, sound_on_time, self.stimulus_A_thread))
        logging.info(";" + str(time.time()) + ";[stimulus];" + "stimulus_B_on")
        self.stimulus_B_thread.start()

    def stimulus_loop(self, grating_name: str, sound_on_time: float, prev_stim_thread: Thread) -> None:
        if prev_stim_thread is not None:
            self.gratings_on = False
            prev_stim_thread.join()

        self.gratings_on = True
        self.box.visualstim.show_grating(grating_name)
        self.box.sound2.off()
        self.box.sound1.blink(sound_on_time, 0.1)
        # self.box.sound1.off()
        # self.box.sound2.blink(sound_on_time, 0.1)

        time.sleep(self.session_info['grating_duration'])
        self.sounds_off()
        # self.stimulus_C_on()
        self.gratings_on = False

    def K_z_callback(self) -> None:
        # self.task.presenter_commands.append('toggle_sound1')
        self.task.presenter_commands.append('turn_stimulus_A_on')
        logging.info(";" + str(time.time()) + ";[action];user_triggered_sound1_on;" + str(""))

    def K_x_callback(self) -> None:
        # self.task.presenter_commands.append('toggle_sound2')
        self.task.presenter_commands.append('turn_stimulus_B_on')
        logging.info(";" + str(time.time()) + ";[action];user_triggered_sound2_on;" + str(""))

    def K_l_callback(self) -> None:
        self.task.presenter_commands.append('toggle_LED')
        logging.info(";" + str(time.time()) + ";[action];toggle_LED")

    def end_ITI(self):
        self.ITI_active = False
        self.LEDs_on()

    def print_controls(self) -> None:
        print("[***] KEYBOARD CONTROLS [***]")
        print("1, 3: left/right nosepoke entry + toggle pump open/closed")
        print("q, w, e, r: pump 1/2/3/4 reward delivery")
        print("t: vacuum activation")
        print("l: toggle LED")
        print("z, x: sound 1 (beep) / 2 (white noise) on")
