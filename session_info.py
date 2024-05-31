# put all of your mouse and session info in here

import collections
import socket
from datetime import datetime
from typing import List, Tuple, Union, Dict, Any
import pandas as pd
import numpy as np
from icecream import ic
from pathlib import Path


### PARAMETERS - Rig and defaults ###
# TODO - get rid of all the redundancy in here

# Parameters: mouse, session type
def make_session_info() -> Dict[str, Any]:
    # Information for this session (the user should edit this each session)
    session_info                              	= collections.OrderedDict()
    session_info['mouse_name']                 	= 'test_mouse'

    session_info['weight']                	    = 0  # in grams
    session_info['date']					= datetime.now().strftime("%Y-%m-%d")  # for example, '2023-09-28'
    session_info['task_config']				    = 'flush'   # 'alternating_latent', 'latent_inference_forage', 'flush', 'latent_inference_with_stimuli'

    # behavior parameters - ideally set these to a default for each session type, which is adjustable
    session_info['max_trial_number']            = 100
    session_info['timeout_length']              = 5  # in seconds
    session_info['reward_size']					= 10  # in microliters
    session_info["lick_threshold"]              = 2
    session_info['reward_time_delay']           = 20
    session_info['intertrial_interval']         = 4  # in seconds
    session_info['quiet_ITI']          = False
    session_info['initiation_timeout'] = 120  # s

    # session_info['entry_interval'] = 1  # this is the one that delays between choices - ITI? or intertrial_interval? or entry_interval?
    # session_info['timeout_time'] = 2
    # session_info['ContextA_reward_probability'] = 1
    # session_info['ContextB_reward_probability'] = 1

    session_info['correct_reward_probability'] = 1
    session_info['incorrect_reward_probability'] = 0
    session_info['switch_probability'] = 1

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

    # Parameters - visual stimuli
    gratings_dir = '/home/pi/gratings'  # './dummy_vis'
    session_info["visual_stimulus"]             = False
    if session_info["visual_stimulus"]:
        session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
        times = [.5, 1]  # , 2]
        session_info['vis_gratings'] = ['vertical_grating_{}s.dat'.format(t) for t in times] + ['horizontal_grating_{}s.dat'.format(t) for t in times]
        session_info['vis_gratings'] = [gratings_dir + '/' + g for g in session_info['vis_gratings']]
        session_info['vis_raws']					= []
        session_info['counterbalance_type'] = 'rightA'  # 'leftA', 'rightA'
        session_info['grating_duration'] = 1
        session_info['inter_grating_interval'] = 2
        session_info['stimulus_duration'] = 10
        session_info['p_stimulus'] = 1

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
        session_info["calibration_coefficient"]['1'] = solenoid_coeff["1"]
        session_info["calibration_coefficient"]['2'] = solenoid_coeff["2"]
        session_info["calibration_coefficient"]['3'] = solenoid_coeff["3"]
        session_info["calibration_coefficient"]['4'] = solenoid_coeff["4"]
    except Exception as e:
        print(e)
        print("No coefficients, generate the default")
        session_info["calibration_coefficient"]['1'] = [7, 0]
        session_info["calibration_coefficient"]['2'] = [7, 0]
        session_info["calibration_coefficient"]['3'] = [7, 0]
        session_info["calibration_coefficient"]['4'] = [7, 0]

    sanity_checks(session_info)
    return session_info


def sanity_checks(session_info: dict):
    if session_info['visual_stimulus']:
        assert session_info['vis_gratings'], "No visual stimuli specified"
        assert session_info['counterbalance_type'], "No counterbalance type specified"
        assert session_info['task_config'] in ['latent_inference_with_stimuli', 'flush'], "Invalid task config for stimulus task"
        assert session_info['grating_duration'] + session_info['inter_grating_interval'] <= session_info['intertrial_interval'], \
            "Intertrial interval too short for visual stimuli"
        assert session_info['grating_duration'] + session_info['inter_grating_interval'] < np.amin(session_info['dark_period_times']), \
            "Intertrial interval too short for dark period"


def get_solenoid_coefficients():
    df_calibration = pd.read_csv("~/experiment_info/calibration_info/calibration_hardcode.csv")
    # df_calibration = pd.read_csv(r"C:\Users\mattc\Documents\RPi_clone\calibration_hardcode.csv")
    pump_coefficient = {}
    for ix in df_calibration.index:
        pump_coefficient[str(df_calibration.loc[ix, 'pump_number'])] = [df_calibration.loc[ix, 'slope'], df_calibration.loc[ix, 'intercept']]

    return pump_coefficient


def main():
    session_info = make_session_info()
    ic(session_info['calibration_coefficient'])


if __name__ == '__main__':
    main()
