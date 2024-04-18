#Test file from https://github.com/bill-connelly/rpg
################
import rpg
import time
import threading
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from icecream import ic


gratings_dir = Path('/home/pi/gratings')  # './dummy_vis'

def repeat_stimulus(stimulus_path: str, t_stimulus: int):
    with rpg.Screen() as myscreen:
        grating = myscreen.load_grating(stimulus_path)
        for _ in range(t_stimulus):
            ic("Stimulus on")
            myscreen.display_grating(grating)
            time.sleep(.5)
            ic("Stimulus off")

            ic("Gray screen on")
            myscreen.display_greyscale(0)
            time.sleep(1)
            ic("Gray screen off")

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
grating = gratings_dir / "vertical_grating_.5s.dat"
t = threading.Thread(target=repeat_stimulus, args=(grating, t_stimulus))
t.start()
t.join()

threading.Thread(target=repeat_grayscreen, args=(t_stimulus,)).start()
# threading.Thread(target=ion_test).start()

