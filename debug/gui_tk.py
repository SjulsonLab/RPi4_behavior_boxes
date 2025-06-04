from colorama import Fore, Style

import matplotlib
import matplotlib.pyplot as plt
from essential.base_classes import GUI, PerformanceFigure

import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from typing import Callable
key_pressed = False

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


class TkGUI(GUI):

    def __init__(self, session_info: dict):
        self.session_info = session_info
        self.figure_window = LivePlot(session_info['right_ix'], session_info['left_ix'])
        self.fig_name = session_info['buffer_dir'] + "/" + session_info['session_name'] + "/" + \
                        session_info['session_name'] + "_choice_plot" + '.png'
        self.keyboard_active = True

    def bind_keystrokes(self, on_key_press: Callable, on_key_release: Callable):
        try:
            self.root = tk.Tk()
            self.root.geometry("800x600")
            self.root.title(self.session_info["box_name"])

            # Create a canvas to hold the plot
            self.canvas = FigureCanvasTkAgg(self.figure_window.figure, master=self.root)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

            # Bind the keypress event to the handler function
            self.root.bind("<KeyPress>", on_key_press)
            self.root.bind("<KeyRelease>", on_key_release)

            # Run the Tkinter event loop
            self.root.mainloop()

            self.check_plot(self.figure_window.figure)
            print(
                "\nKeystroke handler initiated. In order for keystrokes to register, the GUI window "
                "must be in the foreground.\n")
            print(
                Fore.GREEN
                + Style.BRIGHT
                + "         TO EXIT, CLICK THE MAIN TEXT WINDOW AND PRESS CTRL-C "
                + Fore.RED
                + "ONCE\n"
                + Style.RESET_ALL
            )

        except Exception as error_message:
            print("tkinter/GUI issue\n")
            print(str(error_message))

    def check_plot(self, figure=None, FPS=60, savefig=False):
        if figure:
            figure.canvas.draw()

            if savefig:
                plt.figure(figure.number)
                plt.savefig(self.fig_name)

        else:
            print("No figure available")

