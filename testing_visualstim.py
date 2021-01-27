#!/usr/bin/env python3

# testing the visual stim class

import logging
from visualstim import VisualStim
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
    datefmt=('%H:%M:%S'),
    handlers=[
        logging.StreamHandler()
    ]
)

gray_level = 40; # background screen will be gray, with a value from 0-255
logging.info("initiating vstim")
screen = VisualStim(gray_level)
screen.load_stimulus_dir('/home/pi/gratings')

screen.show_stimulus('first_grating.grat')

# proof that the threading works - note that other stuff is done while the 
# stimulus is playing
for i in range(21):
	logging.info("these should be slightly more than 200 ms apart")
	time.sleep(0.2)




