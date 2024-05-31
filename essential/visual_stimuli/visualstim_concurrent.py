import rpg
import time
import logging
from icecream import ic
from threading import Thread
from multiprocessing import Process, Queue, BoundedSemaphore
import queue
import sys
from typing import List, Tuple

sys.path.append('/home/pi/RPi4_behavior_boxes')
from essential.visualstim import VisualStim


class VisualStimMultiprocess(VisualStim):

    def __init__(self, session_info):
        super().__init__(session_info)
        self.gratings_on = False
        self.presenter_commands = Queue()
        self.stimulus_commands = Queue()
        self.t_start = time.perf_counter()
        self.display_default_greyscale()

    def stimulus_A_on(self) -> None:
        if self.active_process is not None and self.active_process.is_alive():
            self.stimulus_commands.put('vertical_gratings')
            ic("vertical_gratings command sent; main process gratings on")
        else:
            grating_name = 'vertical_grating_{}s.dat'.format(self.session_info['grating_duration'])
            self.loop_grating(grating_name, self.session_info['stimulus_duration'])

        self.gratings_on = True

    def stimulus_B_on(self) -> None:
        if self.active_process is not None and self.active_process.is_alive():
            self.stimulus_commands.put('horizontal_gratings')
            ic("horizontal_gratings command sent; main process gratings on")
        else:
            grating_name = 'horizontal_grating_{}s.dat'.format(self.session_info['grating_duration'])
            self.loop_grating(grating_name, self.session_info['stimulus_duration'])

        self.gratings_on = True

    def display_default_greyscale(self):
        if self.active_process is not None and self.active_process.is_alive():
            self.stimulus_commands.put('default_greyscale')
        else:
            self.myscreen.display_greyscale(self.session_info["gray_level"])

        self.gratings_on = False
        ic('main process gratings off')

    def _display_default_greyscale(self):
        self.myscreen.display_greyscale(self.session_info["gray_level"])
        self.gratings_on = False
        ic('secondary process gratings off')

    def display_dark_greyscale(self):
        if self.active_process is not None and self.active_process.is_alive():
            self.stimulus_commands.put('dark_greyscale')
        else:
            self.myscreen.display_greyscale(0)

        self.gratings_on = False
        ic('main process gratings off')

    def _display_dark_greyscale(self):
        self.myscreen.display_greyscale(0)
        self.gratings_on = False
        ic('secondary process gratings off')

    def loop_grating(self, grating_name: str, stimulus_duration: float):
        logging.info(";" + str(time.time()) + ";[configuration];ready to make process")
        if self.active_process is not None and self.active_process.is_alive():
            raise ValueError("A Process is already running!! Time to debug")

        self.active_process = Process(target=self._loop_grating, args=(grating_name, self.stimulus_commands,
                                                                       self.presenter_commands))
        logging.info(";" + str(time.time()) + ";[configuration];starting process")
        self.gratings_on = True
        self.t_start = time.perf_counter()
        self.active_process.start()

    def _loop_grating(self, grating_name: str, in_queue: Queue, out_queue: Queue):
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_start")
        self.empty_stimulus_queue()
        self.gratings_on = True  # the multiprocess loop can't access the original process variable
        ic('secondary process gratings on')
        t_start = time.perf_counter()
        while self.gratings_on and time.perf_counter() - t_start < self.session_info['stimulus_duration']:
            # stim on
            logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "_on")
            out_queue.put('turn_sounds_on')
            self.myscreen.display_grating(self.gratings[grating_name])

            # stim off
            logging.info(";" + str(time.time()) + ";[stimulus];grayscale_on")
            out_queue.put('turn_sounds_off')
            # out_queue.put('turn_stimulus_C_on')
            self.myscreen.display_greyscale(self.session_info["gray_level"])

            if self.gratings_on and time.perf_counter() - t_start < self.session_info['stimulus_duration']:
                sleeptime = min(self.session_info["inter_grating_interval"],
                                self.session_info['stimulus_duration'] - (time.perf_counter() - t_start))
                time.sleep(sleeptime)
                # time.sleep(self.session_info["inter_grating_interval"])

            else:
                ic('ending stimulus loop with time', time.perf_counter() - t_start, 'or gratings_on', self.gratings_on)
                break

            grating_name, t_start = self.check_in_queue(in_queue, grating_name, t_start)

        self.gratings_on = False
        self.empty_stimulus_queue()
        ic('secondary process gratings off')
        out_queue.put('stimulus_process_done')
        # out_queue.put('reset_stimuli')
        # out_queue.put('sounds_off')
        # out_queue.put('turn_stimulus_C_on')
        ic('stimulus loop_grating_process done', time.perf_counter() - t_start)
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_end")

    def check_in_queue(self, in_queue: Queue, grating_name: str, t_start: float) -> Tuple[str, float]:
        try:
            while True:  # this loop will end when the queue is empty
                c = in_queue.get(block=False)
                ic(c, 'command received in _loop_grating')
                if c in ['default_greyscale', 'gratings_off']:
                    self._display_default_greyscale()
                    ic('ending stimulus loop with default greyscale')
                    self.gratings_on = False
                    break
                elif c == 'dark_greyscale':
                    ic('ending stimulus loop with dark greyscale')
                    self._display_dark_greyscale()
                    self.gratings_on = False
                    break
                elif c == 'vertical_gratings':
                    grating_name = 'vertical_grating_{}s.dat'.format(self.session_info['grating_duration'])
                    ic('abbrev stimulus time', time.perf_counter() - t_start)
                    t_start = time.perf_counter()
                elif c == 'horizontal_gratings':
                    grating_name = 'horizontal_grating_{}s.dat'.format(self.session_info['grating_duration'])
                    ic('abbrev stimulus time', time.perf_counter() - t_start)
                    t_start = time.perf_counter()
                else:
                    raise ValueError("Unknown command: " + str(c))

        except queue.Empty:
            pass

        return grating_name, t_start

    def end_gratings_process(self):
        # join the process and empty any remaining commands
        if self.active_process is not None and self.active_process.is_alive():
            self.stimulus_commands.put('gratings_off')
            self.active_process.join()
            ic('full process time', time.perf_counter() - self.t_start)

        self.gratings_on = False
        self.empty_stimulus_queue()

    def empty_stimulus_queue(self) -> List[str]:
        commands = []
        while True:
            try:
                commands.append(self.stimulus_commands.get(block=False))
            except queue.Empty:
                break
        return commands