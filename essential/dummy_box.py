import logging
import queue
import time
from typing import List, Tuple, Union
from essential.base_classes import Box, PumpBase, Presenter, Model, GUI, VisualStimBase
from threading import Timer, Thread
from icecream import ic
from multiprocessing import Process, Queue
from threading import Thread


class LED:
    def __init__(self, pin: int = 0):
        self.is_on: bool = False
        self.pin: int = pin
        self.blink_thread = None
        self.blinking = False

    def blink_loop(self, on_time: float, off_time: float, n: int = None):
        """
        A while loop that blinks the LED on and off. If n is not None, it will blink n times.
        If n is None, it will blink indefinitely until a separate thread turns it off.
        """
        self.blinking = True
        while self.blinking:
            self.is_on = True
            time.sleep(on_time)
            self.is_on = False
            time.sleep(off_time)

            if n is not None:
                n -= 1

            if n == 0:
                self.blinking = False

    def blink(self, on_time: float, off_time: float, n: int = None):
        if self.blinking:
            ic("already blinking")
            return

        ic("starting blink")
        self.blink_thread = Thread(target=self.blink_loop, args=(on_time, off_time, n))
        self.blink_thread.start()

    def on(self):
        self.is_on = True

    def off(self):
        self.is_on = False
        self.blinking = False

    def display_greyscale(self, brightness: int):
        # an empty function for debugging compatibility
        pass

    def toggle(self):
        self.is_on = not self.is_on

    def value(self):
        return self.is_on


class VisualStim(VisualStimBase):

    def __init__(self, session_info):
        self.session_info = session_info
        self.gratings_on = False
        self.presenter_commands = Queue()
        self.stimulus_commands = Queue()
        self.t_start = time.perf_counter()
        self.active_process = None

    def stimulus_A_on(self) -> None:
        if self.active_process is not None and self.active_process.is_alive():
            self.stimulus_commands.put('vertical_gratings')
            ic("vertical_gratings command sent; main process gratings on")
        else:
            grating_name = 'vertical_grating_{}s.dat'.format(self.session_info['grating_duration'])
            self.loop_grating(grating_name, self.session_info['stimulus_duration'])

    def stimulus_B_on(self) -> None:
        if self.active_process is not None and self.active_process.is_alive():
            self.stimulus_commands.put('horizontal_gratings')
            ic("horizontal_gratings command sent; main process gratings on")
        else:
            grating_name = 'horizontal_grating_{}s.dat'.format(self.session_info['grating_duration'])
            self.loop_grating(grating_name, self.session_info['stimulus_duration'])

    def display_default_greyscale(self):
        self.stimulus_commands.put('default_greyscale')
        self.gratings_on = False
        ic('main process gratings off')

    def _display_default_greyscale(self):
        # self.gratings_on = False
        ic('secondary process gratings off')

    def display_dark_greyscale(self):
        self.stimulus_commands.put('dark_greyscale')
        self.gratings_on = False
        ic('main process gratings off')

    def _display_dark_greyscale(self):
        self.gratings_on = False
        ic('secondary process gratings off')

    def loop_grating(self, grating_name: str, stimulus_duration: float):
        logging.info(";" + str(time.time()) + ";[configuration];ready to make process;")
        if self.active_process is not None and self.active_process.is_alive():
            raise ValueError("A Process is already running!! Time to debug")

        self.active_process = Process(target=self._loop_grating, args=(grating_name, self.stimulus_commands,
                                                                       self.presenter_commands))
        logging.info(";" + str(time.time()) + ";[configuration];starting process;")
        self.gratings_on = True
        self.t_start = time.perf_counter()
        self.active_process.start()

    def _loop_grating(self, grating_name: str, in_queue: Queue, out_queue: Queue):
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_start;")
        self.empty_stimulus_queue()
        self.gratings_on = True  # the multiprocess loop can't access the original process variable
        ic('secondary process gratings on')
        t_start = time.perf_counter()
        while self.gratings_on and time.perf_counter() - t_start < self.session_info['stimulus_duration']:
            # stim on
            logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "_on;")
            out_queue.put('turn_sounds_on')
            time.sleep(self.session_info['grating_duration'])

            # stim off
            logging.info(";" + str(time.time()) + ";[stimulus];grayscale_on;")
            out_queue.put('turn_sounds_off')
            # out_queue.put('turn_stimulus_C_on')
            if self.gratings_on and time.perf_counter() - t_start < self.session_info['stimulus_duration']:
                sleeptime = min(self.session_info["inter_grating_interval"],
                                self.session_info['stimulus_duration'] - (time.perf_counter() - t_start))
                time.sleep(sleeptime)
            else:
                ic('ending stimulus loop with time', time.perf_counter() - t_start, 'or gratings_on', self.gratings_on)
                break

            grating_name, t_start = self.check_in_queue(in_queue, grating_name, t_start)

        self.gratings_on = False
        self.empty_stimulus_queue()
        out_queue.put('stimulus_process_done')
        ic('secondary process gratings off')
        ic('stimulus loop_grating_process done', time.perf_counter() - t_start)
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_end;")

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

    def loop_grating_process(self, grating_name: str, in_queue: Queue, out_queue: Queue):
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_start;")
        t_start = time.perf_counter()
        self.gratings_on = True  # the multiprocess loop can't access the original process variable
        ic('secondary process gratings on')
        while self.gratings_on and time.perf_counter() - t_start < self.session_info['stimulus_duration']:
            logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "_on;")
            time.sleep(.5)

            logging.info(";" + str(time.time()) + ";[stimulus];grayscale_on;")
            try:
                command = in_queue.get(block=False)
                ic(command, 'command received in loop_grating_process')
                if command in ['default_greyscale', 'gratings_off']:
                    self._display_default_greyscale()
                    break
                elif command in ['dark_greyscale', 'end_process']:
                    self._display_dark_greyscale()
                    break
                elif command == 'vertical_gratings':
                    grating_name = 'vertical_grating_{}s.dat'.format(self.session_info['grating_duration'])
                    ic('last stimulus time', time.perf_counter() - t_start)
                    t_start = time.perf_counter()
                elif command == 'horizontal_gratings':
                    grating_name = 'horizontal_grating_{}s.dat'.format(self.session_info['grating_duration'])
                    ic('last stimulus time', time.perf_counter() - t_start)
                    t_start = time.perf_counter()
                else:
                    raise ValueError("Unknown command: " + str(command))
            except queue.Empty:
                pass

            if self.gratings_on and time.perf_counter() - t_start < self.session_info['stimulus_duration']:
                sleeptime = min(self.session_info["inter_grating_interval"],
                                self.session_info['stimulus_duration'] - (time.perf_counter() - t_start))
                time.sleep(sleeptime)
                # time.sleep(self.session_info["inter_grating_interval"])
            else:
                break

        self.gratings_on = False
        ic('secondary process gratings off')
        out_queue.put('reset_stimuli')
        ic('stimulus loop_grating_process done', time.perf_counter() - t_start)
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "loop_end;")

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

    def show_grating(self, grating_name):
        logging.info(";" + str(time.time()) + ";[configuration];ready to make process;")
        self.active_process = Process(target=self.process_function, args=(grating_name,))
        logging.info(";" + str(time.time()) + ";[configuration];starting process;")
        self.active_process.start()

    def process_function(self, grating_name):
        # simulate showing the grating
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "_on;")
        time.sleep(self.session_info['grating_duration'])
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "_off;")
        logging.info(";" + str(time.time()) + ";[stimulus];grayscale_on;")


class BehavBox(Box):

    cueLED1 = LED()
    cueLED2 = LED()
    sound1 = LED()
    sound2 = LED()

    def __init__(self, session_info):
        self.visualstim = VisualStim(session_info)

    def set_callbacks(self, presenter):
        pass

    def video_start(self):
        pass

    def video_stop(self):
        pass

    def transfer_files_to_external_storage(self):
        pass


class Pump(PumpBase):
    def __init__(self, session_info):
        self.pump1 = LED(19)
        self.pump2 = LED(20)
        self.pump3 = LED(21)
        self.pump4 = LED(7)
        self.pump_air = LED(8)
        self.pump_vacuum = LED(25)

        # this needs to move to the controller
        # is this even used?
        self.reward_list = []  # a list of tuple (pump_x, reward_amount) with information of reward history for data

        self.coefficient_p1 = session_info["calibration_coefficient"]['1']
        self.coefficient_p2 = session_info["calibration_coefficient"]['2']
        self.coefficient_p3 = session_info["calibration_coefficient"]['3']
        self.coefficient_p4 = session_info["calibration_coefficient"]['4']
        self.duration_air = session_info['air_duration']
        self.duration_vac = session_info["vacuum_duration"]

    def reward(self, which_pump: str, reward_size: float) -> None:
        if which_pump in ["1", "key_1"]:
            duration = round((self.coefficient_p1[0] * (reward_size / 1000) + self.coefficient_p1[1]),
                             5)  # linear function
            logging.info(";" + str(time.time()) + ";[reward];pump1_reward(reward_coeff: " + str(self.coefficient_p1) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ");")
        elif which_pump in ["2", "key_2"]:
            duration = round((self.coefficient_p2[0] * (reward_size / 1000) + self.coefficient_p2[1]),
                             5)  # linear function
            logging.info(";" + str(time.time()) + ";[reward];pump2_reward(reward_coeff: " + str(self.coefficient_p2) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ");")
        elif which_pump in ["3", "key_3"]:
            duration = round((self.coefficient_p3[0] * (reward_size / 1000) + self.coefficient_p3[1]),
                             5)  # linear function
            logging.info(";" + str(time.time()) + ";[reward];pump3_reward(reward_coeff: " + str(self.coefficient_p3) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ");")
        elif which_pump in ["4", "key_4"]:
            duration = round((self.coefficient_p4[0] * (reward_size / 1000) + self.coefficient_p4[1]),
                             5)  # linear function
            logging.info(";" + str(time.time()) + ";[reward];pump4_reward(reward_coeff: " + str(self.coefficient_p4) +
                         ", reward_amount: " + str(reward_size) + ", duration: " + str(duration) + ");")
        elif which_pump in ["air_puff", "key_air_puff"]:
            logging.info(";" + str(time.time()) + ";[reward];pump_air;" + str(reward_size) + ";")
        elif which_pump in ["vacuum", "key_vacuum"]:
            logging.info(";" + str(time.time()) + ";[reward];pump_vacuum;" + str(self.duration_vac) + ";")

    def blink(self, pump_key: str, on_time: float) -> None:
        """Blink a pump-port once for testing purposes."""
        if pump_key in ["1", "key_1"]:
            self.pump1.blink(on_time=on_time, off_time=0.1, n=1)
            logging.info(";" + str(time.time()) + ";[reward];pump1_blink, duration: " + str(on_time) + ";")
        elif pump_key in ["2", "key_2"]:
            self.pump2.blink(on_time=on_time, off_time=0.1, n=1)
            logging.info(";" + str(time.time()) + ";[reward];pump2_blink, duration: " + str(on_time) + ";")
        elif pump_key in ["3", "key_3"]:
            self.pump3.blink(on_time=on_time, off_time=0.1, n=1)
            logging.info(";" + str(time.time()) + ";[reward];pump3_blink, duration: " + str(on_time) + ";")
        elif pump_key in ["4", "key_4"]:
            self.pump4.blink(on_time=on_time, off_time=0.1, n=1)
            logging.info(";" + str(time.time()) + ";[reward];pump4_blink, duration: " + str(on_time) + ";")
        elif pump_key in ["air_puff", "key_air_puff"]:
            self.pump_air.blink(on_time, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[reward];pump_air, duration: " + str(self.duration_air) + ";")
        elif pump_key in ["vacuum", "key_vacuum"]:
            self.pump_vacuum.blink(on_time, 0.1, 1)
            logging.info(";" + str(time.time()) + ";[reward];pump_vacuum, duration: " + str(self.duration_vac) + ";")

    def toggle(self, pump_key: str) -> None:
        if pump_key in ["1", "key_1"]:
            self.pump1.toggle()
            logging.info(";" + str(time.time()) + ";[reward];pump1_toggle;")
            ic(self.pump1.value)
        elif pump_key in ["2", "key_2"]:
            self.pump2.toggle()
            logging.info(";" + str(time.time()) + ";[reward];pump2_toggle;")
            ic(self.pump2.value)
        elif pump_key in ["3", "key_3"]:
            self.pump3.toggle()
            ic(self.pump3.value)
            logging.info(";" + str(time.time()) + ";[reward];pump3_toggle;")
        elif pump_key in ["4", "key_4"]:
            self.pump4.toggle()
            logging.info(";" + str(time.time()) + ";[reward];pump4_toggle;")
            ic(self.pump4.value)
        elif pump_key in ["air_puff", "key_air_puff"]:
            self.pump_air.toggle()
            logging.info(";" + str(time.time()) + ";[reward];pump_air_toggle;")
            ic(self.pump_air.value)
        elif pump_key in ["vacuum", "key_vacuum"]:
            self.pump_vacuum.toggle()
            logging.info(";" + str(time.time()) + ";[reward];pump_vacuum_toggle;")
            ic(self.pump_vacuum.value)
