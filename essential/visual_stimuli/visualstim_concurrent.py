import rpg
import time
import logging
from icecream import ic
from threading import Thread
from multiprocessing import Process, Queue, Pipe
import queue
import sys

sys.path.append('/home/pi/RPi4_behavior_boxes')
from essential.visualstim import VisualStim


# class VisualStimMultiprocess(VisualStim):
#
#     def __init__(self, session_info):
#         super().__init__(session_info)
#         self.gratings_on = False
#         self.presenter_commands = Queue()
#         self.stimulus_commands = Queue()
#         self.t_start = time.perf_counter()
#
#     def loop_grating(self, grating_name: str, stimulus_duration: float):
#         logging.info(";" + str(time.time()) + ";[configuration];ready to make process")
#         self.active_process = Process(target=self.loop_grating_process, args=(grating_name, stimulus_duration,
#                                                                               self.presenter_commands, self.stimulus_commands))
#         logging.info(";" + str(time.time()) + ";[configuration];starting process")
#         self.gratings_on = True
#         self.t_start = time.perf_counter()
#         self.active_process.start()
#
#     def loop_grating_process(self, grating_name: str, stimulus_duration: float,
#                              from_visualstim_commands: Queue, to_visualstim_commands: Queue):
#         logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_start")
#         tstart = time.perf_counter()
#         gratings_on = True  # the multiprocess loop can't access the original process variable
#         while gratings_on and time.perf_counter() - tstart < stimulus_duration:
#             logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "_on")
#             self.myscreen.display_grating(self.gratings[grating_name])
#
#             logging.info(";" + str(time.time()) + ";[stimulus];grayscale_on")
#             self.display_default_greyscale()
#
#             try:
#                 command = to_visualstim_commands.get(block=False)
#                 if command == 'gratings_off':
#                     ic("gratings_off command received")
#                     gratings_on = False
#                 else:
#                     raise ValueError("Unknown command: " + str(command))
#             except queue.Empty:
#                 pass
#
#             if gratings_on and time.perf_counter() - tstart < stimulus_duration:
#                 sleeptime = min(self.session_info["inter_grating_interval"], stimulus_duration - (time.perf_counter() - tstart))
#                 time.sleep(sleeptime)
#                 # time.sleep(self.session_info["inter_grating_interval"])
#             else:
#                 break
#
#         from_visualstim_commands.put('reset_stimuli')
#         ic("stimulus loop_grating_process done")
#         ic('stimulus time', time.perf_counter() - tstart)
#         logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_end")
#
#     def end_gratings_process(self):
#         if self.active_process is not None and self.gratings_on:
#             self.stimulus_commands.put('gratings_off')
#             self.active_process.join()
#             ic('full process time', time.perf_counter() - self.t_start)
#
#         self.gratings_on = False
#         try:
#             self.stimulus_commands.get(block=False)
#         except queue.Empty:
#             pass


class VisualStimMultiprocess(VisualStim):

    def __init__(self, session_info):
        super().__init__(session_info)
        self.gratings_on = False
        self.presenter_commands = Queue()
        self.stimulus_commands = Queue()
        self.t_start = time.perf_counter()

    def stimulus_A_on(self) -> None:
        self.stimulus_commands.put('vertical_gratings')
        self.gratings_on = True

    def stimulus_B_on(self) -> None:
        self.stimulus_commands.put('horizontal_gratings')
        self.gratings_on = True

    def display_default_greyscale(self):
        self.myscreen.display_greyscale(self.session_info["gray_level"])

    def display_dark_greyscale(self):
        self.myscreen.display_greyscale(0)

    def run_eventloop(self):
        self.active_process = Process(target=self.eventloop, args=(self.stimulus_commands, self.presenter_commands))
        self.active_process.start()

    def eventloop(self, in_queue: Queue, out_queue: Queue):
        while True:
            try:
                command = self.stimulus_commands.get(block=False)
                if command == 'vertical_gratings':
                    grating_name = 'vertical_grating_{}s.dat'.format(self.session_info['grating_duration'])
                    self.loop_grating_process(grating_name, in_queue, out_queue)
                elif command == 'horizontal_gratings':
                    grating_name = 'horizontal_grating_{}s.dat'.format(self.session_info['grating_duration'])
                    self.loop_grating_process(grating_name, in_queue, out_queue)
                elif command == 'default_greyscale':
                    self.display_default_greyscale()
                elif command == 'dark_greyscale':
                    self.myscreen.display_greyscale(0)
                elif command == 'gratings_off':
                    self.display_default_greyscale()
                else:
                    raise ValueError("Unknown command: " + str(command))

            except queue.Empty:
                pass

    def loop_grating_process(self, grating_name: str, in_queue: Queue, out_queue: Queue):
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_start")
        t_start = time.perf_counter()
        gratings_on = True  # the multiprocess loop can't access the original process variable
        while gratings_on and time.perf_counter() - t_start < self.session_info['stimulus_duration']:
            logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "_on")
            self.myscreen.display_grating(self.gratings[grating_name])

            logging.info(";" + str(time.time()) + ";[stimulus];grayscale_on")
            self.display_default_greyscale()

            try:
                command = in_queue.get(block=False)
                if command == 'gratings_off':
                    ic("gratings_off command received")
                    gratings_on = False
                    break
                elif command == 'vertical_gratings':
                    grating_name = 'vertical_grating_{}s.dat'.format(self.session_info['grating_duration'])
                    ic('last stimulus time', time.perf_counter() - t_start)
                    t_start = time.perf_counter()
                elif command == 'horizontal_gratings':
                    grating_name = 'horizontal_grating_{}s.dat'.format(self.session_info['grating_duration'])
                    ic('last stimulus time', time.perf_counter() - t_start)
                    t_start = time.perf_counter()
                elif command == 'default_greyscale':
                    self.display_default_greyscale()
                    break
                elif command == 'dark_greyscale':
                    self.myscreen.display_greyscale(0)
                    break
                elif command == 'end_process':
                    gratings_on = False
                    break
                else:
                    raise ValueError("Unknown command: " + str(command))
            except queue.Empty:
                pass

            if gratings_on and time.perf_counter() - t_start < self.session_info['stimulus_duration']:
                sleeptime = min(self.session_info["inter_grating_interval"],
                                self.session_info['stimulus_duration'] - (time.perf_counter() - t_start))
                time.sleep(sleeptime)
                # time.sleep(self.session_info["inter_grating_interval"])
            else:
                break

        out_queue.put('reset_stimuli')
        ic("stimulus loop_grating_process done")
        ic('stimulus time', time.perf_counter() - t_start)
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_end")

    def loop_grating(self, grating_name: str, stimulus_duration: float):
        logging.info(";" + str(time.time()) + ";[configuration];ready to make process")
        self.active_process = Process(target=self.loop_grating_process, args=(grating_name, stimulus_duration,
                                                                              self.presenter_commands, self.stimulus_commands))
        logging.info(";" + str(time.time()) + ";[configuration];starting process")
        self.gratings_on = True
        self.t_start = time.perf_counter()
        self.active_process.start()

    def end_gratings_process(self):
        if self.active_process is not None and self.gratings_on:
            self.stimulus_commands.put('gratings_off')
            self.active_process.join()
            ic('full process time', time.perf_counter() - self.t_start)

        self.gratings_on = False
        while not self.stimulus_commands.empty():
            try:
                self.stimulus_commands.get(block=False)
            except queue.Empty:
                break


class VisualStimThreaded(VisualStim):

    def __init__(self, session_info):
        super().__init__(session_info)
        self.gratings_on = False
        self.presenter_commands = []

    def loop_grating(self, grating_name: str, stimulus_duration: float):
        logging.info(";" + str(time.time()) + ";[configuration];ready to make process")
        self.active_process = Thread(target=self.loop_grating_process, args=(grating_name, stimulus_duration))
        logging.info(";" + str(time.time()) + ";[configuration];starting process")
        self.active_process.start()

    def loop_grating_process(self, grating_name: str, stimulus_duration: float):
        self.gratings_on = True
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_start")
        tstart = time.perf_counter()
        while self.gratings_on and time.perf_counter() - tstart < stimulus_duration:
            logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "_on")
            self.myscreen.display_grating(self.gratings[grating_name])

            logging.info(";" + str(time.time()) + ";[stimulus];grayscale_on")
            self.display_default_greyscale()
            if time.perf_counter() - tstart >= stimulus_duration:
                break
            else:
                time.sleep(self.session_info["inter_grating_interval"])

        self.gratings_on = False
        self.presenter_commands.append('reset_stimuli')
        ic("stimulus loop_grating_process done")
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_end")
