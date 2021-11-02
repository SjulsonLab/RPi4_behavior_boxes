import matplotlib
matplotlib.use("Agg")
import matplotlib.backends.backend_agg as agg
import pylab
import datetime as dt
import time

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pygame
from pygame.locals import *
import numpy as np

def plot_animation(self):
    fig = pylab.figure(figsize=[6, 6],  # Inches
                       dpi=100,  # 100 dots per inch, so the resulting buffer is 600x600 pixels
                       )
    ax = fig.gca()
    xs = []
    ys = []

    def animate(i, xs, ys):
        # read detection value from lick_detector
        detection_value = self.lick_detector()

        # Add x and y to lists
        xs = np.linspace(0, 10, 1000)
        ys = np.sin(10 * np.pi * (xs - 0.02 * i))

        # Limit x and y lists to 100 items
        xs = xs[-100:]
        ys = ys[-100:]

        # Draw x and y lists
        ax.clear()
        ax.plot(xs, ys)

        # Format plot
        plt.xticks(rotation=45, ha='right')
        plt.subplots_adjust(bottom=0.30)
        plt.title('licks over time (s)')
        plt.ylabel('events')

    # Set up plot to call animate() function periodically
    ani = animation.FuncAnimation(fig, animate, fargs=(xs, ys), interval=1000)
    # plt.show()

    canvas = agg.FigureCanvasAgg(fig)
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()

    # initialize pygame to be display the plot
    pygame.init()
    window = pygame.display.set_mode((600, 600), DOUBLEBUF)
    screen = pygame.display.get_surface()
    size = canvas.get_width_height()
    surf = pygame.image.fromstring(raw_data, size, "RGB")
    screen.blit(surf, (0, 0))
    pygame.display.flip()

    crashed = False
    while not crashed:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                crashed = True