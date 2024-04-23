import pygame
import pygame.display
from colorama import Fore, Style

import matplotlib
matplotlib.use('module://pygame_matplotlib.backend_pygame')
import matplotlib.pyplot as plt
from essential.base_classes import GUI, PerformanceFigure


RIGHT_IX = 0
LEFT_IX = 1


class LivePlot(PerformanceFigure):

    def __init__(self, right_ix: int, left_ix: int):
        fig, ax = plt.subplots()
        self.figure = fig
        self.correct_line = ax.plot([], color='g', marker="o", label='Correct', linestyle='', markersize=10)[0]
        self.error_line = ax.plot([], color='r', marker="o", label='Error', linestyle='', markersize=10)[0]
        self.reward_line = ax.plot([], color='b', marker="v", label='Reward given', linestyle='', markersize=5)[0]
        self.state_text = ax.text(0.05, 0.95, '', transform=ax.transAxes, fontsize=14, verticalalignment='top')  #, bbox=props)
        self.stimulus_text = ax.text(0.05, 0.05, '', transform=ax.transAxes, fontsize=14, verticalalignment='bottom')  #, bbox=props)
        ax.set_yticks([right_ix, left_ix])
        ax.set_yticklabels(['right lick', 'left lick'])
        plt.ylim([right_ix - .5, left_ix + .5])


class PygameGUI(GUI):

    def __init__(self, session_info: dict):

        self.figure_window = LivePlot(RIGHT_IX, LEFT_IX)
        self.fig_name = session_info['basedir'] + "/" + session_info['basename'] + "/" + \
                        session_info['basename'] + "_choice_plot" + '.png'

        ###############################################################################################
        # pygame window setup and keystroke handler
        ###############################################################################################
        try:
            pygame.init()
            self.main_display = pygame.display.set_mode((800, 600))
            pygame.display.set_caption(session_info["box_name"])
            self.check_plot(self.figure_window.figure)

            print(
                "\nKeystroke handler initiated. In order for keystrokes to register, the pygame window"
            )
            print("must be in the foreground.\n")
            print(
                Fore.GREEN
                + Style.BRIGHT
                + "         TO EXIT, CLICK THE MAIN TEXT WINDOW AND PRESS CTRL-C "
                + Fore.RED
                + "ONCE\n"
                + Style.RESET_ALL
            )
            self.keyboard_active = True

        except Exception as error_message:
            print("pygame issue\n")
            print(str(error_message))

    ###############################################################################################
    # check for data visualization - uses pygame window to show behavior progress
    ###############################################################################################

    def check_plot(self, figure=None, FPS=60, savefig=False):
        if figure:
            FramePerSec = pygame.time.Clock()
            figure.canvas.draw()
            self.main_display.blit(figure, (0, 0))
            pygame.display.update()
            FramePerSec.tick(FPS)

            if savefig:
                plt.figure(figure.number)
                plt.savefig(self.fig_name)

        else:
            print("No figure available")

