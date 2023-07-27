from datetime import datetime
import os
import pysistence, collections
import socket
import pandas as pd
import numpy as np

# defining immutable mouse dict (once defined for a mouse, NEVER EDIT IT)
mouse_info = pysistence.make_dict({'mouse_name': 'test',
                                   'fake_field': 'fake_info',
                                   })

# Information for this session (the user should edit this each session)
session_info = collections.OrderedDict()
session_info['mouse_info'] = mouse_info
session_info['mouse_name'] = mouse_info['mouse_name']

session_info['basedir'] = '/home/pi/buffer'
session_info['external_storage'] = '/mnt/hd'
session_info['flipper_filename'] = '/home/pi/buffer/flipper_timestamp'
# for actual data save to this dir:
# session_info['basedir']					  	= '/home/pi/video'
session_info['weight'] = 0.0
session_info['manual_date'] = '2023-07-13'
session_info['box_name'] = socket.gethostname()
session_info['block_number'] = 1  # 1 (left large) or 2 (right large) which block starts

session_info['config'] = 'headfixed2FC'

# behavior parameters
session_info['timeout_length'] = 5  # in seconds
session_info["lick_threshold"] = 1
# visual stimulus
session_info["visual_stimulus"] = False

session_info['config'] = 'headfixed2FC'
session_info['treadmill_setup'] = {}
session_info['treadmill'] = True
session_info['fraction'] = 0.3     # 0.3, 0.5,0.7,1 # free choice fraction 1 for all free choice
session_info['phase'] = 'foraging_reward' # 'forced_choice', 'sine_reward'



if session_info['treadmill']:
    session_info['treadmill_setup']['distance_cue'] = 5  # cm
    session_info['treadmill_setup']['distance_initiation'] = 10  # cm
else:
    session_info['treadmill_setup'] = None

session_info['error_repeat'] = True
if session_info['error_repeat']:
    session_info['error_max'] = 3

# condition setup
session_info['cue'] = ['LED_L', 'LED_R', 'all']
# session_info['state'] = ['block1', 'block2']  #
session_info['choice'] = ['right', 'left']  # lick port
session_info['air_duration'] = 0
session_info["vacuum_duration"] = 1

""" solenoid calibration information configuration """

solenoid_coeff = None
def get_coefficient():
    df_calibration = pd.read_csv("~/experiment_info/calibration_info/calibration.csv")
    pump_coefficient = {}

    for pump_num in range(1, 5):
        df_pump = df_calibration[df_calibration['pump_number'] == pump_num]
        mg_per_pulse = df_pump['weight_fluid'].div(df_pump['iteration'])
        on_time = df_pump['on_time']

        fit_calibration = np.polyfit(mg_per_pulse, on_time, 1)  # output with highest power first
        pump_coefficient[str(pump_num)] = fit_calibration
    return pump_coefficient

try:
    solenoid_coeff = get_coefficient()
except Exception as e:
    print(e)

session_info["calibration_coefficient"] = {}

if solenoid_coeff:
    session_info["calibration_coefficient"]['1'] = solenoid_coeff["1"]
    session_info["calibration_coefficient"]['2'] = solenoid_coeff["2"]
    session_info["calibration_coefficient"]['3'] = solenoid_coeff["3"]
    session_info["calibration_coefficient"]['4'] = solenoid_coeff["4"]
else:
    print("No coefficients, generate the default")
    # solenoid valve linear fit coefficient for each pump
    session_info["calibration_coefficient"]['1'] = [0.13, 0]  # highest power first
    session_info["calibration_coefficient"]['2'] = [0.13, 0]
    session_info["calibration_coefficient"]['3'] = [0.13, 0.0]
    session_info["calibration_coefficient"]['4'] = [0.13, 0.0]

# define timeout during each condition
session_info['initiation_timeout'] = 120  # s
session_info['cue_timeout'] = 120
session_info['wait_for_choice'] = 60
session_info['reward_timeout'] = 1
session_info["punishment_timeout"] = 3

session_info["key_reward_amount"] = 2
session_info['reward_size_offset'] = 2
session_info['reward_size'] = (5, 5)

if session_info["phase"] == 'independent_reward':
    session_info['independent_reward'] = {}
    session_info['independent_reward']['scale'] = 0.5
    session_info['independent_reward']['offset'] = 3.0
    session_info['independent_reward']['change_point'] = 20
    session_info['independent_reward']['ntrials'] = 1000
elif session_info["phase"] == 'sine_reward':
    session_info["sine_reward"] = {}
    session_info["sine_reward"]["increment"] = 1
    session_info["sine_reward"]["period_width"] = 40
    session_info["sine_reward"]["amplitude_offset"] = 2
    session_info["sine_reward"]["amplitude_scale"] = 3
    session_info["sine_reward"]["deviation"] = 0
elif session_info['phase'] == 'foraging_reward':
    session_info["foraging_reward"] = {}
    session_info["foraging_reward"]["increment"] = 0.25
    session_info["foraging_reward"]["offset"] = 3
    session_info["foraging_reward"]["max_reward"] = 10


session_info['consecutive_control'] = False
if session_info['consecutive_control']:
    session_info['consecutive_max'] = 3