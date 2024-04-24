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


class VisualStimMultiprocess(VisualStim):

    def __init__(self, session_info):
        super().__init__(session_info)
        self.gratings_on = False
        self.presenter_commands = Queue()
        self.stimulus_commands = Queue()
        self.t_start = time.perf_counter()

    def loop_grating(self, grating_name: str, stimulus_duration: float):
        logging.info(";" + str(time.time()) + ";[configuration];ready to make process")
        self.active_process = Process(target=self.loop_grating_process, args=(grating_name, stimulus_duration,
                                                                              self.presenter_commands))
        logging.info(";" + str(time.time()) + ";[configuration];starting process")
        self.gratings_on = True
        self.active_process.start()
        self.t_start = time.perf_counter()

    def loop_grating_process(self, grating_name: str, stimulus_duration: float,
                             from_visualstim_commands: Queue, to_visualstim_commands: Queue):
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_start")
        tstart = time.perf_counter()
        gratings_on = True  # the multiprocess loop can't access the original process variable
        while gratings_on and time.perf_counter() - tstart < stimulus_duration:
            logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "_on")
            self.myscreen.display_grating(self.gratings[grating_name])

            logging.info(";" + str(time.time()) + ";[stimulus];grayscale_on")
            self.display_default_greyscale()

            try:
                command = to_visualstim_commands.get(block=False)
                if command == 'gratings_off':
                    gratings_on = False
                else:
                    raise ValueError("Unknown command: " + str(command))
            except queue.Empty:
                pass

            if gratings_on and time.perf_counter() - tstart < stimulus_duration:
                time.sleep(self.session_info["inter_grating_interval"])
            else:
                break

        from_visualstim_commands.put('reset_stimuli')
        ic("stimulus loop_grating_process done")
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_end")

    def end_gratings_process(self):
        if self.active_process is not None:
            self.stimulus_commands.put('gratings_off')
            self.active_process.join()
            ic(time.perf_counter() - self.t_start)

        self.gratings_on = False
        try:
            self.stimulus_commands.get(block=False)
        except queue.Empty:
            pass


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
