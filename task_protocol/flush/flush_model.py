#!/usr/bin/env python
# coding: utf-8

# python3: lick_task_left_and_right_alternate.py
"""
author: Matthew Chin
last updated: 2023-06-30
name: flush_model.py
"""
from essential.base_classes import TimedStateMachine, Model, GUI, Box, PumpBase

from icecream import ic
import time

import random
import numpy as np

import logging.config
from typing import List, Tuple, Union
from collections import defaultdict, deque
import threading


RIGHT_IX = 0
LEFT_IX = 1


class FlushModel(Model):

    def __init__(self, session_info: dict):  # name and session_info should be provided as kwargs
        # TASK + BEHAVIOR STATUS
        self.ITI = session_info['intertrial_interval']
        self.lick_threshold = session_info['lick_threshold']

        self.event_list = deque()
        self.t_session = time.time()

        self.presenter_commands = []
        self.ITI_active = False
        self.ITI_thread = None
        self.t_ITI_start = 0

    def activate_ITI(self):
        self.lick_side_buffer *= 0
        self.presenter_commands.append('turn_LED_off')
        self.ITI_active = True
        t = threading.Timer(interval=self.ITI, function=self.end_ITI)
        self.t_ITI_start = time.perf_counter()
        t.start()
        self.ITI_thread = t

    def end_ITI(self):
        # ic(time.perf_counter() - self.t_ITI_start)
        self.lick_side_buffer *= 0
        self.ITI_active = False
        self.presenter_commands.append('turn_LED_on')

    def run_event_loop(self) -> None:
        if self.event_list:
            event = self.event_list.popleft()
        else:
            event = ''

        if self.ITI_active:
            self.lick_side_buffer *= 0
            return

        if event == 'right_entry':
            # self.activate_ITI()
            self.toggle_right_water()

        elif event == 'left_entry':
            # self.activate_ITI()
            self.toggle_left_water()

    def toggle_left_water(self) -> None:
        self.presenter_commands.append('toggle_left_water')

    def toggle_right_water(self) -> None:
        self.presenter_commands.append('toggle_right_water')

    def start_task(self):
        # self.presenter_commands.append('turn_LED_on')
        pass

    def give_correct_reward(self) -> bool:
        return False

    def give_incorrect_reward(self) -> bool:
        return False


def main():
    session_info = defaultdict(list)
    session_info['timeout_time'] = 1
    task = FlushModel(session_info)


if __name__ == '__main__':
    main()
