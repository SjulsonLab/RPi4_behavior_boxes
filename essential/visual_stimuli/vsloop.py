#Test file from https://github.com/bill-connelly/rpg
################
import rpg
import time
import threading
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from icecream import ic
# import importlib.util
# from ..visualstim import VisualStim
import sys
sys.path.append('/home/pi/RPi4_behavior_boxes')
from essential.visualstim import VisualStim
from session_info import make_session_info


def repeat_stimulus(stimulus_path: str, t_stimulus: int):
    with rpg.Screen() as myscreen:
        grating = myscreen.load_grating(stimulus_path)
        for _ in range(t_stimulus):
            ic("Stimulus on")
            myscreen.display_grating(grating)

            ic("Gray screen on")
            myscreen.display_greyscale(0)
            time.sleep(.5)


def alternate_process():
    st = time.perf_counter()
    while time.perf_counter() - st < 5:
        ic('{} sec elapsed'.format(time.perf_counter() - st))
        time.sleep(.5)


def repeat_stimulus_process(visualstim: VisualStim, stimulus_name: str, t_stimulus: float):
    visualstim.loop_grating_process(stimulus_name, t_stimulus)


def repeat_grayscreen(visualstim: VisualStim, t_stimulus: int):
    with rpg.Screen() as myscreen:
        for _ in range(t_stimulus):
            ic("Gray screen on")
            visualstim.myscreen.display_greyscale(40)
            time.sleep(1)
            ic("Gray screen off")
            myscreen.display_greyscale(0)
            time.sleep(1)


t_stimulus = 5
gratings_dir = Path('/home/pi/gratings')  # './dummy_vis'
grating = gratings_dir / "vertical_grating_0.5s.dat"
t_stim = threading.Thread(target=repeat_stimulus, args=(grating, t_stimulus))
t_iter = threading.Thread(target=repeat_stimulus, args=(grating, t_stimulus))
t_stim.start()
t_iter.start()
# t.join()

# session_info = make_session_info()
# visualstim = VisualStim(session_info)
# visualstim.list_gratings()

# threading.Thread(target=repeat_grayscreen, args=(t_stimulus,)).start()
# threading.Thread(target=ion_test).start()
# repeat_stimulus_process(visualstim, "vertical_grating_0.5s.dat", t_stimulus)

