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


gratings_dir = Path('/home/pi/gratings')  # './dummy_vis'

def repeat_stimulus(stimulus_path: str, t_stimulus: int):
    with rpg.Screen() as myscreen:
        grating = myscreen.load_grating(stimulus_path)
        for _ in range(t_stimulus):
            tstart = time.perf_counter()
            ic("Stimulus on")
            myscreen.display_grating(grating)
            tgrating = time.perf_counter()
            # time.sleep(.5)
            ic("Stimulus off")
            tsleep = time.perf_counter()

            ic(tgrating - tstart, "sec elapsed after grating command")
            ic(tsleep - tgrating, "sec elapsed over .5s sleep command")
            ic(tsleep - tstart, "sec elapsed over grating")

            ic("Gray screen on")
            myscreen.display_greyscale(0)
            tgrey = time.perf_counter()
            time.sleep(1)
            ic("Gray screen off")
            tend = time.perf_counter()

            ic(tgrey - tstart, "sec elapsed after grayscreen command")
            ic(tgrey - tsleep, "sec elapsed after gratings sleep command")
            ic(tend - tsleep, "sec elapsed since sleep command")
            ic(tend - tgrey, "sec elapsed since grayscreen command")
            ic(tend - tstart, "sec elapsed for cycle")


def repeat_stimulus_process(stimulus_path: str, t_stimulus: float):
    visualstim = VisualStim()
    grating = visualstim.myscreen.load_grating(stimulus_path)
    visualstim.loop_grating_process(grating, t_stimulus)


def repeat_grayscreen(t_stimulus: int):
    with rpg.Screen() as myscreen:
        for _ in range(t_stimulus):
            ic("Gray screen on")
            myscreen.display_greyscale(40)
            time.sleep(1)
            ic("Gray screen off")
            myscreen.display_greyscale(0)
            time.sleep(1)


t_stimulus = 5
grating = gratings_dir / "vertical_grating_0.5s.dat"
# t = threading.Thread(target=repeat_stimulus, args=(grating, t_stimulus))
# t.start()
# t.join()
visualstim = VisualStim()
visualstim.list_gratings()

# threading.Thread(target=repeat_grayscreen, args=(t_stimulus,)).start()
# threading.Thread(target=ion_test).start()
repeat_stimulus_process(grating, t_stimulus)

