# put all of your mouse and session info in here

import collections
import socket
from datetime import datetime
from typing import List, Tuple, Union, Dict, Any
import pandas as pd
import numpy as np


### PARAMETERS - Rig and defaults ###
# TODO - get rid of all the redundancy in here

# Parameters: mouse, session type
def make_session_info() -> Dict[str, Any]:
    # Information for this session (the user should edit this each session)
    session_info                              	= collections.OrderedDict()
    session_info['mouse_name']                 	= 'test_mouse'

    session_info['weight']                	    = 0  # in grams
    session_info['date']					= datetime.now().strftime("%Y-%m-%d")  # for example, '2023-09-28'
    session_info['task_config']				    = 'flush'   # ['alternating_latent', 'latent_inference_forage', 'flush']

    # behavior parameters - ideally set these to a default for each session type, which is adjustable
    session_info['max_trial_number']            = 100
    session_info['timeout_length']              = 5  # in seconds
    session_info['reward_size']					= 10  # in microliters
    session_info["lick_threshold"]              = 2
    session_info['reward_time_delay']           = 20
    session_info['intertrial_interval']         = .5  # in seconds
    session_info['quiet_ITI']          = True

    session_info['initiation_timeout'] = 120  # s

    session_info['entry_interval'] = 1  # this is the one that delays between choices - ITI? or intertrial_interval? or entry_interval?
    session_info['timeout_time'] = 3
    session_info['ContextA_reward_probability'] = 1
    session_info['ContextB_reward_probability'] = 1

    session_info['correct_reward_probability'] = 1
    session_info['incorrect_reward_probability'] = 0
    session_info['switch_probability'] = .1

    session_info["ContextA_time"] = 30  # todo - revise this or make adjustable by mouse performance
    session_info["ContextB_time"] = 30
    session_info["ContextC_time"] = 30

    session_info['epoch_length'] = 120
    session_info['dark_period_times'] = [10]

    # Reward pump parameters
    session_info["reward_pump1"] = '2'
    session_info['reward_pump2'] = '1'

    session_info['reward_size_large'] = 5
    session_info['reward_size_small'] = 0
    session_info['errors_to_reward_delivery'] = 5
    session_info['key_reward_amount'] = 3

    # Parameters - file saving
    session_info['file_basename']               = 'place_holder'
    session_info['basedir']					  	= '/home/pi/buffer'
    session_info['external_storage']            = '/mnt/hd'
    session_info['flipper_filename']            = '/home/pi/buffer/flipper_timestamp'

    # Parameters - box and rig
    session_info['box_name']             		= socket.gethostname()

    session_info["visual_stimulus"]             = False
    session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
    session_info['vis_gratings']				= ['/home/pi/gratings/context_a.dat',
                                                   '/home/pi/gratings/context_b.dat']
    session_info['vis_raws']					= []

    session_info['treadmill_setup']             = {}
    session_info['treadmill']                   = True

    if session_info['treadmill']:
        session_info['treadmill_setup']['distance_initiation'] = 10  # cm
        session_info['treadmill_setup']['distance_cue'] = 25  # cm
    else:
        session_info['treadmill_setup'] = None

    session_info['air_duration'] = 0
    session_info["vacuum_duration"] = 1
    session_info["calibration_coefficient"] = {}

    try:
        solenoid_coeff = get_solenoid_coefficients()
    except Exception as e:
        print(e)
        solenoid_coeff = None

    if solenoid_coeff:
        session_info["calibration_coefficient"]['1'] = solenoid_coeff["1"]
        session_info["calibration_coefficient"]['2'] = solenoid_coeff["2"]
        session_info["calibration_coefficient"]['3'] = solenoid_coeff["3"]
        session_info["calibration_coefficient"]['4'] = solenoid_coeff["4"]
    else:
        print("No coefficients, generate the default")
        # solenoid valve linear fit coefficient for each pump
        session_info["calibration_coefficient"]['1'] = [7, 0]
        session_info["calibration_coefficient"]['2'] = [7, 0]
        session_info["calibration_coefficient"]['3'] = [7, 0]
        session_info["calibration_coefficient"]['4'] = [7, 0]

    ### DEPRECATED / NOT CURRENTLY IN USE ###
    session_info['LED_duration'] = 3

    session_info['error_repeat'] = True
    if session_info['error_repeat']:
        session_info['error_max'] = 3

    session_info["reward_pump"] = '2'
    session_info['reward_size'] = 1

    return session_info


def get_solenoid_coefficients():
    df_calibration = pd.read_csv("~/experiment_info/calibration_info/calibration.csv")
    # df_calibration = pd.read_csv(r"C:\Users\mattc\Documents\RPi_clone\calibration.csv")
    pump_coefficient = {}

    for pump_num in range(1, 5):
        df_pump = df_calibration[df_calibration['pump_number'] == pump_num]
        mg_per_pulse = df_pump['weight_fluid'].div(df_pump['iteration'])

        # keep this commented while calibration files are untrustworthy
        # try:
        #     mg_per_pulse = df_pump['weight_fluid'].div(df_pump['iteration'])
        # except KeyError as e:
        #     # print(e)
        #     mg_per_pulse = df_pump['water_weight'].div(df_pump['iteration'])

        on_time = df_pump['on_time']

        fit_calibration = np.polyfit(mg_per_pulse, on_time, 1)  # output with highest power first
        pump_coefficient[str(pump_num)] = fit_calibration

    return pump_coefficient
