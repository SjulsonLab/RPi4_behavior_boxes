from typing import List, Tuple

from icecream import ic
import time
import logging
import threading
from essential.base_classes import Presenter, Model, GUI, Box, Pump

PUMP1_IX = 0
PUMP2_IX = 1
trial_choice_map = {'right': 0, 'left': 1}


class FlushPresenter(Presenter):

    def __init__(self, model: Model, box: Box, pump: Pump, gui: GUI, session_info: dict):
        self.task: Model = model
        self.gui: GUI = gui
        self.box = box
        self.pump = pump
        self.session_info = session_info
        self.pump_keys = (session_info["reward_pump1"], session_info['reward_pump2'])
        self.reward_size = [20, 20]
        self.interact_list = []
        self.LED_is_on = False

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

    def perform_task_commands(self) -> None:
        for c in self.task.presenter_commands:
            if c == 'give_right_reward':
                logging.info(";" + str(time.time()) + ";[reward];giving_right_reward;" + str(""))
                self.deliver_reward(pump_key=self.pump_keys[PUMP1_IX], reward_size=self.reward_size[PUMP1_IX])

            elif c == 'give_left_reward':
                logging.info(";" + str(time.time()) + ";[reward];giving_left_reward;" + str(""))
                self.deliver_reward(pump_key=self.pump_keys[PUMP2_IX], reward_size=self.reward_size[PUMP2_IX])

            elif c == 'blink_LED':
                if self.LED_is_on:
                    pass  # don't blink until the LEDs are off
                else:
                    logging.info(";" + str(time.time()) + ";[action];blinking_LEDs;" + str(""))
                    self.LEDs_on()
                    threading.Timer(1, self.LEDs_off).start()

        self.task.presenter_commands.clear()
