from typing import List, Tuple, Callable

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
        self.current_stimulus = None

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
                logging.info(";" + str(time.time()) + ";[reward];toggling_left_water;" + str(""))
                self.pump.toggle(self.pump_keys[PUMP2_IX])

            if c == 'toggle_pump1':
                logging.info(";" + str(time.time()) + ";[reward];toggling_pump1;" + str(""))
                # self.pump.toggle(self.pump_keys[PUMP1_IX])
                self.pump.toggle('1')

            elif c == 'toggle_pump2':
                logging.info(";" + str(time.time()) + ";[reward];toggling_pump2;" + str(""))
                self.pump.toggle('2')

            elif c == 'toggle_pump3':
                logging.info(";" + str(time.time()) + ";[reward];toggling_pump3;" + str(""))
                self.pump.toggle('3')

            elif c == 'toggle_pump4':
                logging.info(";" + str(time.time()) + ";[reward];toggling_pump4;" + str(""))
                self.pump.toggle('4')

            elif c == 'toggle_pump5':
                logging.info(";" + str(time.time()) + ";[reward];toggling_pump5;" + str(""))
                self.pump.toggle('air_puff')

            elif c == 'toggle_pump6':
                logging.info(";" + str(time.time()) + ";[reward];toggling_pump6;" + str(""))
                self.pump.toggle('vacuum')

            elif c == 'toggle_sound1':
                self.box.sound1.toggle()
                ic(self.box.sound1.value)

            elif c == 'toggle_sound2':
                self.box.sound2.toggle()
                ic(self.box.sound2.value)

            elif c == 'toggle_sound3':
                self.box.sound3.toggle()
                ic(self.box.sound3.value)

            elif c == 'toggle_LED':
                self.box.cueLED1.toggle()
                self.box.cueLED2.toggle()
                ic(self.box.cueLED1.value, self.box.cueLED2.value)

            elif c == 'turn_stimulus_A_on':
                self.stimulus_A_on()

            elif c == 'turn_stimulus_B_on':
                self.stimulus_B_on()

            elif c == 'turn_horizontal_grating_on':
                self.stimulus_B_on(play_sound=False)

            elif c == 'turn_vertical_grating_on':
                self.stimulus_A_on(play_sound=False)

            else:
                logging.info(";" + str(time.time()) + ";[action];unknown_command;" + str(c))
                ic("Unknown command:", c)

        self.task.presenter_commands.clear()

    def play_soundA(self):
        if self.session_info['ephys_rig']:
            self.box.sound3.blink(on_time=.1, off_time=0.1)
        else:
            self.box.sound1.blink(on_time=.1, off_time=0.1)

    def play_soundB(self):
        if self.session_info['ephys_rig']:
            if self.session_info['num_sounds'] == 2:
                self.box.sound1.blink(on_time=.2, off_time=0.1)
            else:
                self.box.sound3.blink(on_time=.2, off_time=0.1)

        else:
            if self.session_info['num_sounds'] == 2:
                self.box.sound3.blink(on_time=.2, off_time=0.1)
            else:
                self.box.sound1.blink(on_time=.2, off_time=0.1)

    # def stimulus_A_on(self, play_sound=True) -> None:
    #     grating_name = 'vertical_grating_{}s.dat'.format(self.session_info['grating_duration'])
    #     sound_on_time = 0.1
    #     self.stimulus_A_thread = Thread(target=self.stimulus_loop, args=(grating_name, sound_on_time, self.stimulus_B_thread, play_sound))
    #     logging.info(";" + str(time.time()) + ";[stimulus];" + "stimulus_A_on;")
    #     self.stimulus_A_thread.start()

    def stimulus_A_on(self, play_sound=True) -> None:
        grating_name = 'vertical_grating_{}s.dat'.format(self.session_info['grating_duration'])
        self.stimulus_A_thread = Thread(target=self.stimulus_loop, args=(grating_name, self.play_soundA, self.stimulus_B_thread, play_sound))
        self.current_stimulus = 'A'
        self.stimulus_A_thread.start()

    # def stimulus_B_on(self, play_sound=True) -> None:
    #     grating_name = 'horizontal_grating_{}s.dat'.format(self.session_info['grating_duration'])
    #     sound_on_time = 0.2
    #     self.stimulus_B_thread = Thread(target=self.stimulus_loop, args=(grating_name, sound_on_time, self.stimulus_A_thread, play_sound))
    #     logging.info(";" + str(time.time()) + ";[stimulus];" + "stimulus_B_on;")
    #     self.stimulus_B_thread.start()

    def stimulus_B_on(self, play_sound=True) -> None:
        grating_name = 'horizontal_grating_{}s.dat'.format(self.session_info['grating_duration'])
        self.stimulus_B_thread = Thread(target=self.stimulus_loop, args=(grating_name, self.play_soundB, self.stimulus_A_thread, play_sound))
        self.current_stimulus = 'B'
        self.stimulus_B_thread.start()

    # def stimulus_loop(self, grating_name: str, sound_on_time: float, prev_stim_thread: Thread, play_sound=True) -> None:
    #     if prev_stim_thread is not None:
    #         self.gratings_on = False
    #         prev_stim_thread.join()
    #
    #     self.gratings_on = True
    #     self.box.visualstim.show_grating(grating_name)
    #     if play_sound:
    #         self.box.sound2.off()
    #         self.box.sound1.blink(sound_on_time, 0.1)
    #         # self.box.sound1.off()
    #         # self.box.sound2.blink(sound_on_time, 0.1)
    #
    #     time.sleep(self.session_info['grating_duration'])
    #     self.sounds_off()
    #     # self.stimulus_C_on()
    #     self.gratings_on = False

    def stimulus_loop(self, grating_name: str, sound_fn: Callable, prev_stim_thread: Thread, play_sound=True) -> None:
        if prev_stim_thread is not None:
            self.gratings_on = False
            prev_stim_thread.join()

        self.gratings_on = True
        self.box.visualstim.show_grating(grating_name)
        if play_sound:
            self.sounds_off()
            sound_fn()

        time.sleep(self.session_info['grating_duration'])
        self.sounds_off()
        # self.stimulus_C_on()
        self.gratings_on = False

    def K_z_callback(self) -> None:
        self.task.presenter_commands.append('turn_stimulus_A_on')
        logging.info(";" + str(time.time()) + ";[action];user_triggered_stimulusA_on;" + str(""))

    def K_x_callback(self) -> None:
        self.task.presenter_commands.append('turn_stimulus_B_on')
        logging.info(";" + str(time.time()) + ";[action];user_triggered_stimulusB_on;" + str(""))

    def K_d_callback(self) -> None:
        self.task.presenter_commands.append('toggle_sound1')
        logging.info(";" + str(time.time()) + ";[action];user_triggered_sound1_on;" + str(""))

    def K_f_callback(self) -> None:
        self.task.presenter_commands.append('toggle_sound2')
        logging.info(";" + str(time.time()) + ";[action];user_triggered_sound2_on;" + str(""))

    def K_s_callback(self) -> None:
        self.task.presenter_commands.append('toggle_sound3')
        logging.info(";" + str(time.time()) + ";[action];user_triggered_sound3_on;" + str(""))

    def K_b_callback(self) -> None:
        self.task.presenter_commands.append('turn_horizontal_grating_on')
        logging.info(";" + str(time.time()) + ";[action];user_triggered_horizontal_grating_on;" + str(""))

    def K_v_callback(self) -> None:
        self.task.presenter_commands.append('turn_vertical_grating_on')
        logging.info(";" + str(time.time()) + ";[action];user_triggered_vertical_grating_on;" + str(""))

    def K_l_callback(self) -> None:
        self.task.presenter_commands.append('toggle_LED')
        logging.info(";" + str(time.time()) + ";[action];toggle_LED;")

    def K_1_down_callback(self) -> None:
        logging.info(";" + str(time.time()) + ";[reward];key_pressed_toggle_pump1;")
        self.task.presenter_commands.append('toggle_pump1')

    def K_2_down_callback(self) -> None:
        logging.info(";" + str(time.time()) + ";[reward];key_pressed_toggle_pump2;")
        self.task.presenter_commands.append('toggle_pump2')

    def K_3_down_callback(self) -> None:
        logging.info(";" + str(time.time()) + ";[action];key_pressed_toggle_pump3;")
        self.task.presenter_commands.append('toggle_pump3')

    def K_4_down_callback(self) -> None:
        logging.info(";" + str(time.time()) + ";[action];key_pressed_toggle_pump4;")
        self.task.presenter_commands.append('toggle_pump4')

    def K_5_down_callback(self) -> None:
        logging.info(";" + str(time.time()) + ";[action];key_pressed_toggle_pump5;")
        self.task.presenter_commands.append('toggle_pump5')

    def K_6_down_callback(self) -> None:
        logging.info(";" + str(time.time()) + ";[action];key_pressed_toggle_pump6;")
        self.task.presenter_commands.append('toggle_pump6')

    def K_1_up_callback(self) -> None:
        pass

    def K_2_up_callback(self) -> None:
        pass

    def K_3_up_callback(self) -> None:
        pass

    def end_ITI(self):
        self.ITI_active = False
        self.LEDs_on()

    def print_controls(self) -> None:
        print("[***] KEYBOARD CONTROLS [***]")
        # print("1, 3: left/right nosepoke entry + toggle pump open/closed")
        print("1, 2, 3, 4: toggle pump 1/2/3/4 open or closed")
        print("q, w, e, r: pump 1/2/3/4 reward delivery")
        print("t: vacuum activation")
        print("l: toggle LED")
        print("z, x: stimulus A / B on")
        print("d, f: toggle sound 1 (beep) / 2 (white noise)")
        print("b, v: horizontal/vertical gratings on")

