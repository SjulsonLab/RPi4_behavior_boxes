import rpg
import time
import logging
from icecream import ic
from threading import Thread
from multiprocessing import Process, Queue
import sys

sys.path.append('/home/pi/RPi4_behavior_boxes')
from essential.visualstim import VisualStim


class VisualStimMultiprocess(VisualStim):

    def __init__(self, session_info):
        super().__init__(session_info)
        self.gratings_on = False
        self.presenter_commands = Queue()
        self.tstart = None

    def loop_grating(self, grating_name: str, stimulus_duration: float):
        logging.info(";" + str(time.time()) + ";[configuration];ready to make process")
        self.active_process = Process(target=self.loop_grating_process, args=(grating_name, stimulus_duration,
                                                                              self.presenter_commands))
        logging.info(";" + str(time.time()) + ";[configuration];starting process")
        self.gratings_on = True
        self.active_process.start()
        self.tstart = time.perf_counter()

    def loop_grating_process(self, grating_name: str, stimulus_duration: float, queue: Queue = None):
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

        queue.put('reset_stimuli')
        ic("stimulus loop_grating_process done")
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_end")


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
