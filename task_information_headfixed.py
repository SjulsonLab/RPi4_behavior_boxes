# Python3: task_information_2022_02_14.py
import random
from datetime import datetime
import pysistence, collections
import socket

task_information = collections.OrderedDict()
task_information['experiment_setup'] = 'headfixed'
task_information['treadmill_setup'] = {'present': True}

if task_information['treadmill_setup']['present']:
    task_information['treadmill_setup']['distance_initiation'] = 3 #cm
    task_information['treadmill_setup']['distance_short'] = 5 #cm
    task_information['treadmill_setup']['distance_max'] = None
else:
    task_information['treadmill_setup'] = None

task_information['error_repeat'] = True
if task_information['error_repeat']:
    task_information['error_repeat_max'] = 3

# condition setup
task_information['cue'] = ['sound', 'LED']
task_information['state'] = ['distance_short', 'distance_long'] # treadmill distance
task_information['choice'] = ['right', 'left'] # lick port
task_information['reward'] = ['small', 'large'] # reward size

# block setup
task_information['block']['forced_1'] = [
                                (1, 0, 0, 1), # forced choice block 1
                                (1, 1, 1, 1), # 0, 1 index for corresponding condition setup
                                (0, 0, 1, 0), # column 0 is cue, 1 is state, 2 is choice, 3 is reward_amount
                                (0, 1, 0, 0)] # each row is a combination of the condition parameter for block 1

task_information['block']['forced_2'] = [
                                (1, 0, 0, 0), # forced choice block 2
                                (1, 1, 1, 0), # 0, 1 index for corresponding condition setup
                                (0, 0, 1, 1), # column 0 is cue, 1 is state, 2 is choice, 3 is reward_amount
                                (0, 1, 0, 1)] # each row is a combination of the condition parameter for block 1

task_information['block']['free_1'] = [
                                (None, 0, 0, 1), # free choice block 1
                                (None, 0, 1, 0), # 0, 1 index for corresponding condition setup, None in column 0
                                (None, 1, 0, 0), # means both cues are on
                                (None, 1, 0, 1)] # each row is a combination of the condition parameter for block 1

task_information['block']['free_2'] = [
                                (None, 0, 0, 0), # free choice block 2
                                (None, 0, 1, 1), # 0, 1 index for corresponding condition setup, None in column 0
                                (None, 1, 0, 1), # means both cues are on
                                (None, 1, 0, 0)] # each row is a combination of the condition parameter for block 1

# now shuffle and make a deck for this session
# shuffle requirement
initial_condition = 0 # 0,1,2,3 row number
consecutive_control = True
if consecutive_control:
    consecutive_max = 3
duration_1_forced = 30
duration_1_free = 30
duration_2_forced = 30
duration_2_free = 30

# task_information['block_1_forced_deck'] = []
row_buffer = -1
consecutive_count = 0

def generate_deck(duration):
    deck_list = []
    for iteration in range(duration):
        row_index = random.randrange(0, 4)
        while True:
            if row_index == row_buffer and consecutive_control:
                if consecutive_count >= consecutive_max:
                    row_index = random.randrange(0,4)
                else:
                    break
            else:
                break
        row_buffer = row_index
        deck_list.append(row_index)
    return deck_list

task_information["deck_list"] = {}
task_information["deck_list"]["block_1_forced"] = generate_deck(duration_1_forced)
task_information["deck_list"]["block_2_forced"] = generate_deck(duration_2_forced)
task_information["deck_list"]["block_1_free"] = generate_deck(duration_1_free)
task_information["deck_list"]["block_2_free"] = generate_deck(duration_2_free)