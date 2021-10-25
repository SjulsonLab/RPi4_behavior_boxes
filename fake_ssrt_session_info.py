# SSRT session information

import collections, socket
from datetime import datetime

fake_SSRT_session_info                                = collections.OrderedDict()
fake_SSRT_session_info['mouse_name']                  = 'fakemouse01'
fake_SSRT_session_info['basedir']                     = '/home/pi/fakedata'
fake_SSRT_session_info['date']                        = datetime.now().strftime("%Y-%m-%d")
fake_SSRT_session_info['time']                        = datetime.now().strftime('%H%M%S')
fake_SSRT_session_info['datetime']                    = fake_SSRT_session_info['date'] + '_' + fake_SSRT_session_info['time']
fake_SSRT_session_info['basename']                    = fake_SSRT_session_info['mouse_name'] + '_' + fake_SSRT_session_info['datetime']
fake_SSRT_session_info['box_name']                    = socket.gethostname()
fake_SSRT_session_info['dir_name']                    = fake_SSRT_session_info['basedir'] + "/" + fake_SSRT_session_info['mouse_name'] + "_" + fake_SSRT_session_info['datetime']
# fake_session_info['config']                        = 'freely_moving_v1'
fake_SSRT_session_info['config']                      = 'head_fixed_v1'
fake_SSRT_session_info['init_length']                 = 1  # in seconds
fake_SSRT_session_info['cue_length']                  = 3  # in seconds
fake_SSRT_session_info['iti_length']                  = 3  # in seconds
fake_SSRT_session_info['reward_size']                 = 5  # in microliters

# visual stimulus
fake_SSRT_session_info['gray_level']                  = 40  # the pixel value from 0-255 for the screen between stimuli
fake_SSRT_session_info['vis_gratings']                = ['/home/pi/gratings/first_grating.grat', '/home/pi/gratings/second_grating.grat']
fake_SSRT_session_info['vis_raws']                    = []
