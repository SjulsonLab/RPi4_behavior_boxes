#!/usr/bin/env python
# coding: utf-8

# python3: lick_task_left_and_right_alternate.py
"""
author: Matthew Chin
last updated: 2023-06-30
name: flush_model.py
"""
from essential.base_classes import TimedStateMachine, Model, GUI, Box, Pump

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
        self.ITI_active = True
        t = threading.Timer(interval=self.ITI, function=self.end_ITI)
        self.t_ITI_start = time.perf_counter()
        t.start()
        self.ITI_thread = t

    def end_ITI(self):
        # ic(time.perf_counter() - self.t_ITI_start)
        self.lick_side_buffer *= 0
        self.ITI_active = False

    def run_event_loop(self) -> None:
        if self.event_list:
            event = self.event_list.popleft()
        else:
            event = ''

        if self.ITI_active:
            self.lick_side_buffer *= 0
            return

        if event == 'right_entry':
            self.activate_ITI()
            self.give_right_reward()

        elif event == 'left_entry':
            self.activate_ITI()
            self.give_left_reward()

    def give_left_reward(self) -> None:
        self.presenter_commands.append('give_left_reward')

    def give_right_reward(self) -> None:
        self.presenter_commands.append('give_right_reward')

    def start_task(self):
        pass



def main():
    session_info = defaultdict(list)
    session_info['timeout_time'] = 1
    task = FlushModel(session_info)


if __name__ == '__main__':
    main()
