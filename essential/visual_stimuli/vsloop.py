#Test file from https://github.com/bill-connelly/rpg
################
import rpg
import time
import threading
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


gratings_dir = Path('/home/pi/gratings')  # './dummy_vis'

def repeat_stimulus(t_stimulus: int):
    with rpg.Screen() as myscreen:
        grating = myscreen.load_grating(gratings_dir / "test2_grating.dat")
        for _ in range(t_stimulus):
            myscreen.display_grating(grating)
            time.sleep(1)

        #
        # plt.plot(np.random.rand(10), np.random.rand(10), 'ro')
        # plt.axis('scaled')
        # # plt.draw()
        # # plt.pause(.01)
        # print('red light')
        # time.sleep(.5)
        # # f.canvas.flush_events()
        #
        # # plt.plot(np.random.rand(10), np.random.rand(10), 'go')
        # # plt.axis('scaled')
        # # plt.draw()
        # print('green light')
        # time.sleep(.5)
        # # f.canvas.flush_events()
        # # plt.pause(.01)


t_stimulus = 5
t = threading.Thread(target=repeat_stimulus, args=(t_stimulus,))
t.start()
# threading.Thread(target=ion_test).start()

