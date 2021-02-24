#!/usr/bin/env python3

# testing the visual stim class

import logging
from visualstim import VisualStim
import time
import collections, pysistence
import socket
from datetime import datetime


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
    datefmt=("%H:%M:%S"),
    handlers=[logging.StreamHandler()],
)


# defining immutable mouse dict (once defined for a mouse, this should never change)
mouse_info = pysistence.make_dict(
    {
        "mouse_name": "mouse01",
        "fake_field": "fake_info",
    }
)

# making fake session_info
session_info = collections.OrderedDict()
session_info["mouse_name"] = mouse_info["mouse_name"]
# session_info['trainingPhase']             	= 4
session_info["basedir"] = "/home/pi/fakedata"
session_info["weight"] = 32.18
session_info["manual_date"] = "2021-01-27"
session_info["date"] = datetime.now().strftime("%Y-%m-%d")
session_info["time"] = datetime.now().strftime("%H%M%S")
session_info["datetime"] = session_info["date"] + "_" + session_info["time"]
session_info["basename"] = mouse_info["mouse_name"] + "_" + session_info["datetime"]
session_info["box_name"] = socket.gethostname()
session_info["dir_name"] = (
    session_info["basedir"]
    + "/"
    + session_info["mouse_name"]
    + "_"
    + session_info["datetime"]
)
# session_info['config']						= 'freely_moving_v1'
session_info["config"] = "head_fixed_v1"

# visual stimulus
session_info[
    "gray_level"
] = 40  # the pixel value from 0-255 for the screen between stimuli
session_info["vis_gratings"] = [
    "/home/pi/gratings/first_grating.grat",
    "/home/pi/gratings/second_grating.grat",
]
session_info["vis_raws"] = []


logging.info("initiating vstim")
screen = VisualStim(session_info)
# screen.load_stimulus_dir('/home/pi/gratings')

screen.show_stimulus("first_grating.grat")

# proof that the threading works - note that other stuff is done while the
# stimulus is playing
for i in range(21):
    logging.info("these should be slightly more than 200 ms apart")
    time.sleep(0.2)
