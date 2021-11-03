import matplotlib
matplotlib.use("Agg")
import matplotlib.backends.backend_agg as agg
import matplotlib.pyplot as plt

import pygame
from pygame.locals import *
import numpy as np

# Set up the fig to plot
# fig = plt.figure(figsize=[6, 6],  # Inches
#                  dpi=100,         # 100 dots per inch, so buffer is 400x400 pixels
#                  )

# Plot the figure
fig, axs = plt.subplots(2, 2)
matplotlib.rcParams['font.size'] = 5.0
# create random data
data1 = np.random.random([6, 50])
# set different colors for each set of positions
colors1 = ['C{}'.format(i) for i in range(6)]
# set different line properties for each set of positions
# note that some overlap
lineoffsets1 = np.array([-15, -3, 1, 1.5, 6, 10])
linelengths1 = [5, 2, 1, 1, 3, 1.5]
# create a horizontal plot
axs[0, 0].eventplot(data1, colors=colors1, lineoffsets=lineoffsets1,
                    linelengths=linelengths1)
# create a vertical plot
axs[1, 0].eventplot(data1, colors=colors1, lineoffsets=lineoffsets1,
                    linelengths=linelengths1, orientation='vertical')
# create another set of random data.
# the gamma distribution is only used fo aesthetic purposes
data2 = np.random.gamma(4, size=[60, 50])
# use individual values for the parameters this time
# these values will be used for all data sets (except lineoffsets2, which
# sets the increment between each data set in this usage)
colors2 = 'black'
lineoffsets2 = 1
linelengths2 = 1
# create a horizontal plot
axs[0, 1].eventplot(data2, colors=colors2, lineoffsets=lineoffsets2,
                    linelengths=linelengths2)
# create a vertical plot
axs[1, 1].eventplot(data2, colors=colors2, lineoffsets=lineoffsets2,
                    linelengths=linelengths2, orientation='vertical')

canvas = agg.FigureCanvasAgg(fig)
canvas.draw()
renderer = canvas.get_renderer()
raw_data = renderer.tostring_rgb()

pygame.init()

window = pygame.display.set_mode((600, 600), DOUBLEBUF)
screen = pygame.display.get_surface()

size = canvas.get_width_height()

surf = pygame.image.fromstring(raw_data, size, "RGB")
screen.blit(surf, (0,0))
pygame.display.flip()

show = True
while show:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            # Stop showing when quit
            show = False
    pygame.display.update()