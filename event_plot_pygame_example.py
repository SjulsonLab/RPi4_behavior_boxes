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

# Initialize the figure
fig = plt.figure(figsize=(20, 12))
ax1 = fig.add_subplot(231)
ax2 = fig.add_subplot(212)
ax3 = fig.add_subplot(232)
ax4 = fig.add_subplot(233)


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
ax1.set_title('Trial Outcome', fontsize=15)
ax1.text(0.05, 0.95, textstr, fontsize=12, verticalalignment='top')
ax1.set_xticklabels([])
ax1.set_xticks([])
ax1.set_yticks([])
ax1.set_yticklabels([])
ax1.set_xlim([0, 0.5])

# create a vertical plot
# create fake data for eventplot
a = []
a = np.append(a, 0.185 - 0.02)
a = np.append(a, 0.358 - 0.02)
a = np.append(a, 0.978 - 0.02)
print(a)
b = 0.255 - 0.02
data1 = [a, [b]]

# set different colors for each set of positions
colors1 = ['C{}'.format(i) for i in range(2)]
# set different line properties for each set of positions
lineoffsets1 = np.array([6, 3])
linelengths1 = [2, 2]
ax2.set_title('Vertical Plot')
ax2.eventplot(data1, colors=colors1, lineoffsets=lineoffsets1, linelengths=linelengths1)
ax2.set_xlim([0, 1.5])
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
ax3.eventplot(data2, colors=colors2, lineoffsets=lineoffsets2,
                    linelengths=linelengths2)
# create a vertical plot
ax4.eventplot(data2, colors=colors2, lineoffsets=lineoffsets2,
                    linelengths=linelengths2, orientation='vertical')

# Draw on canvas
canvas = agg.FigureCanvasAgg(fig)
canvas.draw()
renderer = canvas.get_renderer()
raw_data = renderer.tostring_rgb()
pygame.init()
window = pygame.display.set_mode((2000, 1200), DOUBLEBUF)
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