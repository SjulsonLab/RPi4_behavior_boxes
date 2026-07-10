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
from photodiode import load_photodiode_off_raw, patched_grating_path, screen_args_for_grating


class VisualStim_go(object):
    def __init__(self, session_info):
        self.session_info = session_info
        self.gratings = OrderedDict()
        self.screen_info = self.get_screen_info()
        self.myscreen = rpg.Screen(**self.screen_info)
        self.photodiode_off_raw = load_photodiode_off_raw(
            self.myscreen,
            rpg,
            self.screen_info["resolution"][0],
            self.screen_info["resolution"][1],
            self.session_info["gray_level"],
        )
        self.show_photodiode_off()
        logging.info(str(time.time()) + ", screen_opened")
        self.load_session_gratings()

    def get_screen_info(self):
        """Return RPG Screen setup matching the go grating file.

        Inputs
        ------
        None. Uses ``self.session_info`` with ``vis_gratings_go`` paths and
        ``gray_level`` intensity.

        Returns
        -------
        dict
            Keyword arguments for ``rpg.Screen``. ``resolution`` is
            ``(width, height)`` in pixels, ``background`` is intensity 0-255,
            and ``colormode`` is 16 or 24 bits/pixel.
        """
        if self.session_info["vis_gratings_go"]:
            try:
                return screen_args_for_grating(
                    self.session_info["vis_gratings_go"][0],
                    self.session_info["gray_level"],
                )
            except Exception as exc:
                logging.warning(str(time.time()) + ", photodiode screen setup warning: " + str(exc))
        return {"resolution": (1280, 720), "background": self.session_info["gray_level"], "colormode": 16}

    def show_photodiode_off(self):
        """Display gray no-stimulus screen with black photodiode square.

        Inputs
        ------
        None. Uses the preloaded RPG raw object ``self.photodiode_off_raw``.

        Returns
        -------
        None
            Updates the physical display. Screen coordinates are pixels with
            origin at the top-left corner.
        """
        self.myscreen.display_raw(self.photodiode_off_raw)

    def load_grating_file(
        self, grating_file
    ):  # best if grating_file is an absolute path
        fname = os.path.split(grating_file)
        logging.info(str(time.time()) + ", loading grating file")
        self.gratings.update({fname[1]: self.myscreen.load_grating(patched_grating_path(grating_file))})
        print(fname[1] + " loaded")
        logging.info(str(time.time()) + ", " + fname[1] + " loaded")

    def load_grating_dir(self, grating_directory):
        logging.info(str(time.time()) + ", loading all gratings in directory")
        current_dir = os.getcwd()
        os.chdir(grating_directory)
        self.grating_list = os.listdir()
        self.grating_list.sort()
        for fname in self.grating_list:
            self.gratings.update({fname: self.myscreen.load_grating(patched_grating_path(fname))})
            logging.info(str(time.time()) + ", " + fname + " loaded")
            print(fname + " loaded")
        os.chdir(current_dir)

    def load_session_gratings(self):
        for filepath in self.session_info["vis_gratings_go"]:
            self.load_grating_file(filepath)

    def list_gratings(self):
        ic(self.gratings)

    def clear_gratings(self):
        self.gratings = {}
        ic(self.gratings)

    # call this method to display the grating. It will launch it in a separate process
    # to run on a separate core
    def show_grating(self, grating_name):
        logging.info(str(time.time()) + ", ready to make vstim process")
        x = Process(target=self.process_function, args=(grating_name,))
        logging.info(str(time.time()) + ", starting vstim process")
        x.start()

    # this is the function that is launched by show_grating to run in a different process
    def process_function(self, grating_name):
        logging.info(str(time.time()) + ", " + str(grating_name) + " ON")
        self.myscreen.display_grating(self.gratings[grating_name])
        logging.info(str(time.time()) + ", " + str(grating_name) + " OFF")
        self.show_photodiode_off()  # reset the screen to neutral gray with the photodiode off
        logging.info(str(time.time()) + ", vstim grayscale ON")

    def __del__(self):
        self.myscreen.close()
