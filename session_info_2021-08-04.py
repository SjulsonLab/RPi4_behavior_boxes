# put all of your mouse and session info in here

from datetime import datetime
import os
import pysistence, collections
import socket


# defining immutable mouse dict (once defined for a mouse, NEVER EDIT IT)
mouse_info = pysistence.make_dict({'mouse_name': 'FSA071_OF_COCAINE',
                 'fake_field': 'fake_info',
                 })

# Information for this session (the user should edit this each session)
session_info                              	= collections.OrderedDict()
session_info['mouse_info']					= mouse_info
session_info['mouse_name']                 	= mouse_info['mouse_name']
#session_info['trainingPhase']             	= 4
session_info['basedir']					  	= '/home/pi/fakedata'
# for actual data save to this dir:
#session_info['basedir']					  	= '/home/pi/video'
session_info['weight']                	    = 32.18
session_info['manual_date']					= '2021-08-04'
session_info['box_name']             		= socket.gethostname()

# session_info['config']						= 'freely_moving_v1'
session_info['config']						= 'head_fixed_v1'

# behavior parameters
session_info['timeout_length']              = 5  # in seconds
session_info['reward_size']					= 10  # in microliters

# visual stimulus
session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
session_info['vis_gratings']				= ['/home/pi/gratings/first_grating.grat', 
											   '/home/pi/gratings/second_grating.grat']
session_info['vis_raws']					= []

