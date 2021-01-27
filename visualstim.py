# this is the class for creating visual stimuli on the RPi4. It uses a slightly-modified 
# version of Bill Connelly's rpg library (located here: https://github.com/SjulsonLab/rpg.git)
# that enables the visual stimuli to be delivered in a separate process.
# To build your visual stimulus files, look at the scripts in rpg/examples
#
# Luke Sjulson, 2021-01-27
#
# TODO: make show_random() method to show a random stimulus from the list
# TODO: (someday) implement triggering of visual stimuli

import rpg
import time
import logging
import os
from collections import OrderedDict
from icecream import ic
from multiprocessing import Process

class VisualStim(object):

    def __init__(self, gray_value):
        self.stimuli = OrderedDict()
        self.gray_value = gray_value
        self.myscreen = rpg.Screen()
        self.myscreen.display_greyscale(self.gray_value)
        logging.info("screen_opened")

    def load_stimulus_file(self, stimulus_file): # best if stimulus_file is an absolute path
        fname = os.path.split(stimulus_file)
        logging.info('loading stimulus file')
        self.stimuli.update({fname[1]: self.myscreen.load_grating(stimulus_file)})
        print(fname[1] + ' loaded')
        logging.info(fname[1] + ' loaded')
        ic(self.stimuli)

    def load_stimulus_dir(self, stimulus_directory):
        logging.info('loading stimulus directory')
        os.chdir(stimulus_directory)
        self.stimulus_list = os.listdir()
        self.stimulus_list.sort()
        for fname in self.stimulus_list:
            self.stimuli.update({fname: self.myscreen.load_grating(fname)})
            logging.info(fname + ' loaded')
            print(fname + ' loaded')
        ic(self.stimuli)

    def list_stimuli(self):
        ic(self.stimuli)

    def clear_stimuli(self):
        self.stimuli = {}
        ic(self.stimuli)

    # call this method to display the stimulus. It will launch it in a separate process
    # to run on a separate core
    def show_stimulus(self, stimulus_name):
        logging.info("ready to make process")
        x = Process(target=self.process_function, args=(stimulus_name, ) )
        logging.info("starting process")
        x.start()

    # this is the function that is launched by show_stimulus to run in a different process
    def process_function(self, stimulus_name):
        logging.info(stimulus_name + "_on")
        self.myscreen.display_grating(self.stimuli[stimulus_name])  
        logging.info(stimulus_name + "_off")
        self.myscreen.display_greyscale(self.gray_value) # reset the screen to neutral gray
        logging.info("grayscale_on")

    def __del__(self):
        self.myscreen.close()

