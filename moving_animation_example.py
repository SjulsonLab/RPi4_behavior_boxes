import numpy as np
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation


# plt.style.use('seaborn-pastel')
fig = plt.figure()
ax1 = plt.axes(xlim=(0, 10), ylim=(-10, 10))
line, = ax1.plot([], [], lw=2)
plt.xlabel(["Time (s)"])
plt.ylabel(["Task parameters"])

plotlays, plotcols = [2], ["black", "red"]
lines = []
for index in range(2):
    lobj = ax1.plot([], [], lw=2, color=plotcols[index])[0]
    lines.append(lobj)

def init():
    for line in lines:
        line.set_data([], [])
    return lines

x1, y1 = [], []
x2, y2 = [], []

def animate(i):
    x1 = np.linspace(0, 10, 1000)
    x2 = np.linspace(0, 10, 1000)
    y1 = np.sin(10 * np.pi * (x1 - 0.02 * i))
    y2 = np.sin(4 * np.pi * (x2 - 0.01 * i)) + 4

    xlist = [x1, x2]
    ylist =[y1, y2]

    for lnum,line in enumerate(lines):
        line.set_data(xlist[lnum], ylist[lnum])

    return lines


anim = FuncAnimation(fig, animate, init_func=init,
                               frames=200, interval=20, blit=True)
plt.show()

