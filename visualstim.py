# this is the class for creating visual stimuli on the RPi4. It uses a slightly-modified 
# version of Bill Connelly's rpg library (located here: https://github.com/SjulsonLab/rpg.git)
# that enables the visual stimuli to be delivered in a separate thread

import rpg
import time
import threading
import logging
import os
from collections import OrderedDict
from icecream import ic

class VisualStim(object):

    def __init__(self, grating_directory, gray_value):
        self.grating_directory = grating_directory
        self.gray_value = gray_value
        self.myscreen = rpg.Screen()
        self.myscreen.display_greyscale(self.gray_value)
        logging.info("screen_opened")
        self.load_gratings(grating_directory)

    # this is called by init, but you can call it manually to replace the gratings that
    # are currently loaded in RAM
    def load_gratings(self, grating_directory):
        logging.info('loading_gratings')
        os.chdir(grating_directory)
        self.grating_list = os.listdir()
        self.grating_list.sort()
        self.gratings = OrderedDict()
        for fname in self.grating_list:
            self.gratings.update({fname: self.myscreen.load_grating(fname)})
        logging.info('gratings_loaded')
        ic(self.gratings)

    # here you can add gratings to the gratings already in RAM
    def add_gratings(self, grating_directory):
        logging.info('adding_gratings')
        os.chdir(grating_directory)
        self.grating_list = os.listdir()
        self.grating_list.sort()
        for fname in self.grating_list:
            self.gratings.update({fname: self.myscreen.load_grating(fname)})
        logging.info('gratings_added')
        ic(self.gratings)

    # call this method to display the grating. It will launch it in a separate thread
    def show_grating(self, grating_name):
        logging.info("ready to make thread")
        x = threading.Thread(target=self.thread_function, args=(grating_name, ) )
        logging.info("starting thread")
        x.start()

    # this is the thread function that is launched by show_grating
    def thread_function(self, grating_name):
        logging.info(grating_name + "_on")
        self.myscreen.display_grating(self.gratings[grating_name])  
        logging.info(grating_name + "_off")
        self.myscreen.display_greyscale(self.gray_value)
        logging.info("grayscale_on")