import collections
import socket
from datetime import datetime
from typing import List, Tuple, Union, Dict, Any
import pandas as pd
import numpy as np
from icecream import ic
from pathlib import Path

# Parameters: mouse, session type
def make_session_info() -> Dict[str, Any]:
    # Information for this session (the user should edit this each session)
    session_info                              	= collections.OrderedDict()
    session_info['mouse_name']                 	= 'test-mouse'
    session_info['debug']                     	= False
    session_info['ephys_rig']                 	= True  # determines reward pumps and ssh IPs
    session_info['use_multiple_cameras']        = False
    session_info['lick_input_setting']          = 'signal_high'  # ['signal_high', 'signal_low']

    session_info['debounce_licks']              = False  # use this to check if lick signals are long enough. Licks will be detected by lick onset AND offset; throw out signals that are too short/noise
    session_info['lick_min_time'] = .05
    session_info['lick_max_time'] = 1

    session_info['weight']                	    = 0  # in grams
    session_info['date']					    = datetime.now().strftime("%Y-%m-%d")  # for example, '2023-09-28'
    session_info['task_config']				    = 'alternating_latent'   # 'alternating_latent', 'latent_inference', 'flush', 'latent_inference_with_stimuli'
    session_info['resume_pre_dark_context']     = True   # option to resume the context used before entering a dark period. Only relevant if task_config is 'latent_inference' or 'latent_inference_with_stimuli'
    session_info['control']                     = False
    session_info['emit_barcodes']               = True  # whether to emit barcodes for the flipper

    # behavior parameters - ideally set these to a default for each session type, which is adjustable
    # session_info['max_trial_number']            = 100  # we use max session time instead
    # session_info['reward_time_delay']           = 20  # s; does anything use this?
    # session_info['initiation_timeout'] = 120  # s; does anything use this?
    session_info['timeout_length']              = 5  # in seconds, not currently implemented
    session_info['reward_size']					= 10  # in microliters
    session_info["lick_threshold"]              = 1  # number of consecutive licks to one side to indicate a choice
    session_info['intertrial_interval']         = 4  # in seconds
    session_info['quiet_ITI']                   = False
    session_info['biased_side']                 = 'none'  # 'left', 'right', 'none' - must use 'none' instead of None, NoneType is not a string

    # Parameters for latent inference tasks
    session_info['correct_reward_probability'] = .8
    session_info['incorrect_reward_probability'] = 0
    session_info['biased_switch_probability'] = .5  # when on the biased side, use a higher probability of switching. requires biased_side = left or right to be used
    session_info['default_switch_probability'] = .2  # when on the unbiased side, use a higher probability of switching. requires biased_side = left or right to be used
    session_info['switch_probability'] = session_info['default_switch_probability']  # this is the switch param - when no bias is set, it is the only parameter used. In session_info settings, setting it based off default_switch reduced user parameters
    session_info['epoch_length'] = 120
    session_info['dark_period_times'] = [10]
    session_info['use_dark_period'] = False
    session_info['max_correct_trials_in_block'] = 2 / session_info['switch_probability']  # either use double the expected trials per block or hardcode 30

    # Reward pump parameters
    if session_info['ephys_rig']:
        session_info['right_reward_pump'] = '3'
        session_info['left_reward_pump'] = '2'
    else:
        session_info['right_reward_pump'] = '1'
        session_info['left_reward_pump'] = '2'

    session_info['pump1_ix'] = 0
    session_info['pump2_ix'] = 1
    session_info['right_ix'] = 0
    session_info['left_ix'] = 1
    session_info['trial_choice_map'] = {'right': 0, 'left': 1}  # probably not needed

    session_info['reward_size_large'] = 10
    session_info['reward_size_small'] = 0
    session_info['errors_to_reward_delivery'] = np.inf
    session_info['key_reward_amount'] = session_info['reward_size_large']  # this was 3 before but play with it
    # session_info['flush_duration'] = 2

    # Parameters - file saving
    session_info['session_name']                = ''
    session_info['buffer_dir']					= '/home/pi/buffer'  # previously 'basedir'
    session_info['output_dir']                  = session_info['buffer_dir'] + '/' + session_info['session_name']
    session_info['video_dir']                   = session_info['output_dir'] + '/videos'
    session_info['external_storage']            = '/mnt/sda'  # /mnt/sda
    session_info['flipper_filename']            = '/home/pi/buffer/flipper_timestamp'
    session_info['file_basename']               = session_info['output_dir'] + '/' + session_info['session_name']

    # Parameters - box and rig
    session_info['box_name']             		= socket.gethostname()
    # Two-camera example (set use_multiple_cameras=True to require both cameras)
    session_info['camera_nodes'] = [
        {
            'camera_id': 'cam0',
            'host': '10.49.98.88',
            'ssh_user': 'pi',
            'backend': 'picamera2',
            'required': True,
        },
    ]

    # Parameters - visual stimuli
    gratings_dir = '/home/pi/gratings'  # './dummy_vis'

    if session_info['task_config'] in ['latent_inference_with_stimuli', 'flush']:
        session_info["visual_stimulus"]             = True
    else:
        session_info["visual_stimulus"]             = False

    if session_info["visual_stimulus"]:
        session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
        times = [.5, 1]  # , 2]
        session_info['vis_gratings'] = ['vertical_grating_{}s.dat'.format(t) for t in times] + ['horizontal_grating_{}s.dat'.format(t) for t in times]
        session_info['vis_gratings'] = [gratings_dir + '/' + g for g in session_info['vis_gratings']]
        session_info['vis_raws']     = []
        session_info['counterbalance_type'] = 'rightA'  # 'leftA', 'rightA'
        session_info['grating_duration'] = 1
        session_info['inter_grating_interval'] = 2
        session_info['stimulus_duration'] = 10
        session_info['p_stimulus'] = 0.5
        session_info['num_sounds'] = 1

    session_info['treadmill']                   = False
    session_info['treadmill_setup']             = {
        'encoder_a_pin': 17,  # BCM numbering
        'encoder_b_pin': 27,  # BCM numbering
    }

    session_info['air_duration'] = 0
    session_info["vacuum_duration"] = 1
    session_info["calibration_coefficient"] = {}
    session_info['default_calibration_coefficient'] = [7, 0]

    try:
        solenoid_coeff = get_solenoid_coefficients()
        session_info["calibration_coefficient"]['1'] = solenoid_coeff["1"]
        session_info["calibration_coefficient"]['2'] = solenoid_coeff["2"]
        session_info["calibration_coefficient"]['3'] = solenoid_coeff["3"]
        session_info["calibration_coefficient"]['4'] = solenoid_coeff["4"]

    except Exception as e:
        print(e)
        print("No coefficients, generate the default")
        session_info["calibration_coefficient"]['1'] = session_info['default_calibration_coefficient']
        session_info["calibration_coefficient"]['2'] = session_info['default_calibration_coefficient']
        session_info["calibration_coefficient"]['3'] = session_info['default_calibration_coefficient']
        session_info["calibration_coefficient"]['4'] = session_info['default_calibration_coefficient']

    session_info = session_defaults(session_info)
    session_info = sanity_checks(session_info)
    return session_info


def session_defaults(session_info: dict) -> dict:
    if session_info['task_config'] == 'flush':
        ic('Defaulting intertrial interval to 4 seconds')
        session_info['intertrial_interval'] = 4  # in seconds
        session_info['use_dark_period'] = True

    elif session_info['task_config'] == 'alternating_latent':
        ic('Defaulting intertrial interval to 2 seconds')
        session_info['intertrial_interval'] = 2  # in seconds

    if session_info['debug']:
        pass

    return session_info


def sanity_checks(session_info: dict) -> dict:
    assert session_info['task_config'] in ['alternating_latent', 'latent_inference', 'flush', 'latent_inference_with_stimuli'], "Invalid task config, check your spelling!!"
    assert session_info['lick_input_setting'] in ['signal_high', 'signal_low'], "Invalid lick input setting"
    assert session_info['biased_side'] in ['left', 'right', 'none'], "Invalid biased side"

    camera_nodes = session_info.get('camera_nodes', [])
    assert isinstance(camera_nodes, list), "camera_nodes must be a list"
    assert len(camera_nodes) > 0, "camera_nodes cannot be empty"
    camera_ids = []
    valid_backends = {'picamera', 'picamera2'}
    for node in camera_nodes:
        assert isinstance(node, dict), "Each camera node must be a dictionary"
        camera_id = node.get('camera_id', '')
        backend = node.get('backend', '')
        host = node.get('host', '')
        assert camera_id, "Each camera node must include camera_id"
        assert backend in valid_backends, "Each camera node backend must be picamera or picamera2"
        assert isinstance(host, str), "Each camera node host must be a string"
        camera_ids.append(camera_id)

    assert len(set(camera_ids)) == len(camera_ids), "camera_id values must be unique"

    if session_info.get('use_multiple_cameras', False):
        required_nodes = [node for node in camera_nodes if node.get('required', True)]
        assert len(required_nodes) >= 2, "Multi-camera mode requires at least two required camera nodes"
        for node in required_nodes:
            assert node.get('host', ''), f"Required camera node {node.get('camera_id', '<unknown>')} is missing host"

    if session_info['visual_stimulus']:
        assert session_info['vis_gratings'], "No visual stimuli specified"
        assert session_info['counterbalance_type'], "No counterbalance type specified"
        assert session_info['task_config'] in ['latent_inference_with_stimuli', 'flush'], "Invalid task config for stimulus task"
        assert session_info['grating_duration'] + session_info['inter_grating_interval'] <= session_info['intertrial_interval'], \
            "Intertrial interval too short for visual stimuli"
        assert session_info['grating_duration'] + session_info['inter_grating_interval'] < np.amin(session_info['dark_period_times']), \
            "Intertrial interval too short for dark period"
        assert session_info['num_sounds'] in [1, 2], "Invalid number of sounds"
        assert session_info['use_dark_period'], "Invalid visual stimulus setting - must use dark periods for visual stimulus task!!"

    if session_info.get('treadmill', False):
        treadmill_setup = session_info.get('treadmill_setup')
        assert isinstance(treadmill_setup, dict), "treadmill_setup must be a dictionary"
        assert 'encoder_a_pin' in treadmill_setup, "treadmill_setup must include encoder_a_pin"
        assert 'encoder_b_pin' in treadmill_setup, "treadmill_setup must include encoder_b_pin"

        encoder_a_pin = treadmill_setup['encoder_a_pin']
        encoder_b_pin = treadmill_setup['encoder_b_pin']
        assert isinstance(encoder_a_pin, int), "encoder_a_pin must be an integer BCM pin number"
        assert isinstance(encoder_b_pin, int), "encoder_b_pin must be an integer BCM pin number"
        assert encoder_a_pin >= 0, "encoder_a_pin must be non-negative"
        assert encoder_b_pin >= 0, "encoder_b_pin must be non-negative"
        assert encoder_a_pin != encoder_b_pin, "encoder_a_pin and encoder_b_pin must be different"

    return session_info


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
