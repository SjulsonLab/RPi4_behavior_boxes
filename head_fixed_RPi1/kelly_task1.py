#!/usr/bin/python3

from .. import behavbox

from time import sleep
import collections
import logging

# define all parameters for expt




# initialize hardware - using pins for breakout board https://oshwhub.com/PancLAN/40-pin-for-rpi


box = behavbox.BehavBox


box.cueLED1.on()
sleep(1)
box.cueLED1.off()



#session_info                              = collections.OrderedDict()
#session_info['cueLED1']                 = PWMLED(22)
#session_info['trainingPhase']             = 4
#session_info['weight']                    = 32.18

