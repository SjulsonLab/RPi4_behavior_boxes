#!/usr/bin/env python3

from behavbox import BehavBox

from time import sleep
import collections, pysistence, socket
import logging
import datetime


# very little of this has been written yet


# define all parameters for expt

# TODO - figure out what to include in ordered dicts (like before)
# defining immutable mouse dict (once defined for a mouse, this should never change)
mouse_info = pysistence.make_dict({'mouseName': 'test',
                 'requiredVersion': 8,
                 'leftVisCue': 3,
                 'rightVisCue': 0,
                 'leftAudCue': 0,
                 'rightAudCue': 3})

# Information for this session (the user should edit this each session)
session_info                              = collections.OrderedDict()
session_info['mouseName']                 = mouse_info['mouseName']
session_info['trainingPhase']             = 4
session_info['weight']                    = 32.18
session_info['date']                      = datetime.datetime.now().strftime("%Y%m%d")
session_info['time']                      = datetime.datetime.now().strftime('%H%M%S')
session_info['basename']                  = mouse_info['mouseName'] + '_' + session_info['date'] + '_' + session_info['time']
session_info['box_number']                = 1      # put the number of the behavior box here
session_info['computer_name']             = socket.gethostname()
session_info['correctBias']               = 1
session_info['blocks_reward']             = 1      #flag to do blocks of reward, i.e., increase reward on the left and decrease on the right for a certain number of trials


#session_info                              = collections.OrderedDict()
#session_info['cueLED1']                 = PWMLED(22)
#session_info['trainingPhase']             = 4
#session_info['weight']                    = 32.18



# initialize hardware - using pins for breakout board https://oshwhub.com/PancLAN/40-pin-for-rpi
box = BehavBox

# for testing
box.cueLED1.on()
sleep(1)
box.cueLED1.off()



