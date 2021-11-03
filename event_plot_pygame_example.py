import matplotlib
matplotlib.use("Agg")
import matplotlib.backends.backend_agg as agg
import matplotlib.pyplot as plt

import pygame
from pygame.locals import *
import numpy as np

current_trial = 1
trial_list = list(range(0, 300))
trial_outcome = ["" for o in range(300)]

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

# create an outcome plot

textstr = '\n'.join((
    f"trial {trial_list[0]} : {trial_outcome[0]}",
    f"trial {trial_list[1]} : {trial_outcome[1]}",
    f"trial {trial_list[2]} : {trial_outcome[2]}",
    f"trial {trial_list[3]} : {trial_outcome[3]}",
    f"trial {trial_list[4]} : {trial_outcome[4]}",
    f"trial {trial_list[5]} : {trial_outcome[5]}",
    f"trial {trial_list[6]} : {trial_outcome[6]}",
    f"trial {trial_list[7]} : {trial_outcome[7]}",
    f"trial {trial_list[8]} : {trial_outcome[8]}",
    f"trial {trial_list[9]} : {trial_outcome[9]}",
    f"trial {trial_list[10]} : {trial_outcome[10]}",
    f"trial {trial_list[11]} : {trial_outcome[11]}",
    f"trial {trial_list[12]} : {trial_outcome[12]}",
    f"trial {trial_list[13]} : {trial_outcome[13]}",
    f"trial {trial_list[14]} : {trial_outcome[14]}"))
axs[0, 0].text(0.05, 0.95, textstr, fontsize=6, verticalalignment='top')

# create a vertical plot
axs[1, 0].eventplot(data1, colors=colors1, lineoffsets=lineoffsets1,
                    linelengths=linelengths1)
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

# Draw on canvas
canvas = agg.FigureCanvasAgg(fig)
canvas.draw()
renderer = canvas.get_renderer()
raw_data = renderer.tostring_rgb()
pygame.init()
window = pygame.display.set_mode((800, 800), DOUBLEBUF)
screen = pygame.display.get_surface()
size = canvas.get_width_height()
surf = pygame.image.fromstring(raw_data, size, "RGB")
screen.blit(surf, (0,0))
pygame.display.flip()

# Close figure when pygame quit
show = True
while show:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            # Stop showing when quit
            show = False
    pygame.display.update()