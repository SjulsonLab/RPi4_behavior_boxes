# this is the class for creating visual gratings on the RPi4. It uses a slightly-modified
# version of Bill Connelly's rpg library (located here: https://github.com/SjulsonLab/rpg.git)
# that enables the visual gratings to be delivered in a separate process.
# To build your visual grating files, look at the scripts in rpg/examples
#
# Luke Sjulson, 2021-01-27
#
# TODO: make show_random() method to show a random grating from the list
# TODO: (someday) implement triggering of visual gratings

import rpg
import time
import logging
import os
from collections import OrderedDict
from icecream import ic
from multiprocessing import Process


class VisualStim(object):
    def __init__(self, session_info):
        self.session_info = session_info
        self.gratings = OrderedDict()
        self.myscreen = rpg.Screen()
        self.myscreen.display_greyscale(self.session_info["gray_level"]["default"])
        logging.info(";" + str(time.time()) + ";[initialization];screen_opened")
        self.load_session_gratings()

    def load_grating_file(
        self, grating_file
    ):  # best if grating_file is an absolute path
        fname = os.path.split(grating_file)
        logging.info(";" + str(time.time()) + ";[initialization];loading grating file")
        self.gratings.update({fname[1]: self.myscreen.load_grating(grating_file)})
        print(fname[1] + " loaded")
        logging.info(";" + str(time.time()) + ";[initialization];loaded")

    def load_grating_dir(self, grating_directory):
        logging.info(";" + str(time.time()) + ";[initialization];loading all gratings in directory")
        current_dir = os.getcwd()
        os.chdir(grating_directory)
        self.grating_list = os.listdir()
        self.grating_list.sort()
        for fname in self.grating_list:
            self.gratings.update({fname: self.myscreen.load_grating(fname)})
            logging.info(";" + str(time.time()) + ";[initialization];loaded")
            print(fname + " loaded")
        os.chdir(current_dir)

    def load_session_gratings(self):
        for filepath in self.session_info["vis_gratings"]:
            self.load_grating_file(filepath)

    def list_gratings(self):
        ic(self.gratings)

    def clear_gratings(self):
        self.gratings = {}
        ic(self.gratings)

    # call this method to display the grating. It will launch it in a separate process
    # to run on a separate core
    def show_grating(self, grating_name):
        logging.info(";" + str(time.time()) + ";[configuration];ready to make process")
        x = Process(target=self.process_function, args=(grating_name,))
        logging.info(";" + str(time.time()) + ";[configuration];starting process")
        x.start()

    # this is the function that is launched by show_grating to run in a different process
    def process_function(self, grating_name):
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "_on")
        self.myscreen.display_grating(self.gratings[grating_name])
        logging.info(";" + str(time.time()) + ";[stimulus];" + str(grating_name) + "_off")
        self.myscreen.display_greyscale(
            self.session_info["gray_level"][grating_name]
        )  # reset the screen to neutral gray
        logging.info(";" + str(time.time()) + ";[stimulus];grayscale_on")

    def __del__(self):
        self.myscreen.close()
