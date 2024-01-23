import pygame
import pygame.display
from colorama import Fore, Style

import matplotlib
matplotlib.use('module://pygame_matplotlib.backend_pygame')
import matplotlib.pyplot as plt
from typing import Protocol


RIGHT_IX = 0
LEFT_IX = 1


class Presenter(Protocol):

    def K_escape_callback(self):
        ...

    def K_1_down_callback(self):
        ...

    def K_2_down_callback(self):
        ...

    def K_3_down_callback(self):
        ...

    def K_1_up_callback(self):
        ...

    def K_2_up_callback(self):
        ...

    def K_3_up_callback(self):
        ...

    def K_q_callback(self):
        ...

    def K_w_callback(self):
        ...

    def K_e_callback(self):
        ...

    def K_r_callback(self):
        ...

    def K_t_callback(self):
        ...

    def K_a_callback(self):
        ...

    def K_g_callback(self):
        ...


class PerformanceFigure:

    def __init__(self, right_ix: int, left_ix: int):
        fig, ax = plt.subplots()
        self.figure = fig
        self.correct_line = ax.plot([], color='g', marker="o", label='Correct', linestyle='', markersize=10)[0]
        self.error_line = ax.plot([], color='r', marker="o", label='Error', linestyle='', markersize=10)[0]
        self.reward_line = ax.plot([], color='b', marker="v", label='Reward given', linestyle='', markersize=5)[0]
        ax.set_yticks([right_ix, left_ix])
        ax.set_yticklabels(['right lick', 'left lick'])
        plt.ylim([right_ix - .5, left_ix + .5])


class GUI:

    def __init__(self, session_info: dict):

        self.figure_window = PerformanceFigure(RIGHT_IX, LEFT_IX)
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

    def check_plot(self, figure=None, FPS=144, savefig=False):
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

    def set_callbacks(self, presenter: Presenter):
        self.K_escape_callback = presenter.K_escape_callback

        self.K_1_down_callback = presenter.K_1_down_callback
        self.K_2_down_callback = presenter.K_2_down_callback
        self.K_3_down_callback = presenter.K_3_down_callback

        self.K_1_up_callback = presenter.K_1_up_callback
        self.K_2_up_callback = presenter.K_2_up_callback
        self.K_3_up_callback = presenter.K_3_up_callback

        self.K_q_callback = presenter.K_q_callback
        self.K_w_callback = presenter.K_w_callback
        self.K_e_callback = presenter.K_e_callback
        self.K_r_callback = presenter.K_r_callback
        self.K_t_callback = presenter.K_t_callback
        self.K_a_callback = presenter.K_a_callback
        self.K_g_callback = presenter.K_g_callback

    ###############################################################################################
    # check for key presses - uses pygame window to simulate nosepokes and licks
    ###############################################################################################

    def check_keyboard(self):

        if self.keyboard_active:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.K_escape_callback()

                    # lick port interaction buttons
                    elif event.key == pygame.K_1:
                        self.K_1_down_callback()
                    elif event.key == pygame.K_2:
                        self.K_2_down_callback()
                    elif event.key == pygame.K_3:
                        self.K_3_down_callback()

                    # interactive training functions
                    elif event.key == pygame.K_q:
                        self.K_q_callback()
                    elif event.key == pygame.K_w:
                        self.K_w_callback()
                    elif event.key == pygame.K_e:
                        self.K_e_callback()
                    elif event.key == pygame.K_r:
                        self.K_r_callback()
                    elif event.key == pygame.K_t:
                        self.K_t_callback()
                    elif event.key == pygame.K_a:
                        self.K_a_callback()
                    elif event.key == pygame.K_g:
                        self.K_g_callback()

                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_1:
                        self.K_1_up_callback()
                    elif event.key == pygame.K_2:
                        self.K_2_up_callback()
                    elif event.key == pygame.K_3:
                        self.K_3_up_callback()
