#Test file from https://github.com/bill-connelly/rpg
################
# import rpg
import time
import threading
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


gratings_dir = Path('/home/pi/gratings')  # './dummy_vis'
# options = {"duration": 2, "angle": 90, "spac_freq": 0.2, "temp_freq": 1}
# rpg.build_grating(gratings_dir / "test0_grating.dat", options)


# grating = myscreen.load_grating("~/second_grating.dat")
# myscreen.display_grating(grating)


plt.ion()
f, ax = plt.subplots()
def repeat_stimulus(t_stimulus: int):
    for _ in range(t_stimulus):
        # with rpg.Screen() as myscreen:
        #     grating = myscreen.load_grating(gratings_dir / "test2_grating.dat")
        #     myscreen.display_grating(grating)
        #     time.sleep(1)

        # Radius: 1, face-color: red, edge-color: blue
        plt.plot(np.random.rand(10), np.random.rand(10), 'ro')
        plt.axis('scaled')
        plt.draw()
        plt.pause(.01)
        print('red light')
        # time.sleep(.5)
        # f.canvas.flush_events()

        # plt.plot(np.random.rand(10), np.random.rand(10), 'go')
        # plt.axis('scaled')
        # plt.draw()
        # print('green light')
        # time.sleep(.5)
        # f.canvas.flush_events()
        # plt.pause(.01)


def ion_test():
    x = np.linspace(0, 10 * np.pi, 100)
    y = np.sin(x)

    plt.ion()
    fig, ax = plt.subplots()
    line1, = ax.plot(x, y, 'b-')

    for phase in np.linspace(0, 10 * np.pi, 100):
        line1.set_ydata(np.sin(0.5 * x + phase))
        fig.canvas.draw()
        plt.pause(0.1)  # Add a short pause to improve animation smoothness


t_stimulus = 1
# threading.Thread(target=repeat_stimulus, args=(t_stimulus,)).start()
threading.Thread(target=ion_test).start()

