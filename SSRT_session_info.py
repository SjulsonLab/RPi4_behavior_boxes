# SSRT session information

import collections, socket
from datetime import datetime

SSRT_session_info                                = collections.OrderedDict()
SSRT_session_info['mouse_name']                  = 'fakemouse01'
SSRT_session_info['basedir']                     = '/home/pi/fakedata'
SSRT_session_info['date']                        = datetime.now().strftime("%Y-%m-%d")
SSRT_session_info['time']                        = datetime.now().strftime('%H%M%S')
SSRT_session_info['datetime']                    = SSRT_session_info['date'] + '_' + SSRT_session_info['time']
SSRT_session_info['basename']                    = SSRT_session_info['mouse_name'] + '_' + SSRT_session_info['datetime']
SSRT_session_info['box_name']                    = socket.gethostname()
SSRT_session_info['dir_name']                    = SSRT_session_info['basedir'] + "/" + SSRT_session_info['mouse_name'] + "_" + SSRT_session_info['datetime']
# fake_session_info['config']                        = 'freely_moving_v1'
SSRT_session_info['config']                      = 'head_fixed_v1'
SSRT_session_info['timeout_length']              = 5  # in seconds
SSRT_session_info['reward_size']                 = 10  # in microliters

# visual stimulus
SSRT_session_info['gray_level']                  = 40  # the pixel value from 0-255 for the screen between stimuli
SSRT_session_info['vis_gratings']                = ['/home/pi/gratings/first_grating.grat', '/home/pi/gratings/second_grating.grat']
SSRT_session_info['vis_raws']                    = []
