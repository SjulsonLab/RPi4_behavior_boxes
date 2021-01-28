#!/usr/bin/env python3

# put all of your mouse and session info in here

from datetime import datetime
import os
import pysistence, collections
import socket


# defining immutable mouse dict (once defined for a mouse, this should never change)
mouse_info = pysistence.make_dict({'mouse_name': 'mouse01',
                 'fake_field': 'fake_info',
                 })

# Information for this session (the user should edit this each session)
session_info                              	= collections.OrderedDict()
session_info['mouse_name']                 	= mouse_info['mouse_name']
#session_info['trainingPhase']             	= 4
session_info['basedir']					  	= '/home/pi/fakedata'
session_info['weight']                	    = 32.18
session_info['manual_date']					= '2021-01-27'
session_info['date']                   	   	= datetime.now().strftime("%Y-%m-%d")
session_info['time']                   	   	= datetime.now().strftime('%H%M%S')
session_info['datetime']					= session_info['date'] + '_' + session_info['time']
session_info['basename']                  	= mouse_info['mouse_name'] + '_' + session_info['datetime']
session_info['box_name']             		= socket.gethostname()
session_info['dir_name']  					= session_info['basedir'] + "/" + session_info['mouse_name'] + "_" + session_info['datetime']
# session_info['config']						= 'freely_moving_v1'
session_info['config']						= 'head_fixed_v1'

# visual stimulus
session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
session_info['vis_gratings']				= ['/home/pi/gratings/first_grating.grat', '/home/pi/gratings/second_grating.grat']
session_info['vis_raws']					= []

