# Python3: task_information_2022_02_14.py
import random
import pysistence, collections

task_information = collections.OrderedDict()
task_information['experiment_setup'] = 'headfixed'
task_information['treadmill_setup'] = {'present': True}

if task_information['treadmill_setup']['present']:
    task_information['treadmill_setup']['distance_initiation'] = 3  # cm
    task_information['treadmill_setup']['distance_short'] = 5  # cm
    task_information['treadmill_setup']['distance_max'] = None
else:
    task_information['treadmill_setup'] = None

task_information['error_repeat'] = True
if task_information['error_repeat']:
    task_information['error_repeat_max'] = 3

# condition setup
task_information['cue'] = ['sound', 'LED']
task_information['state'] = ['distance_short', 'distance_long']  # treadmill distance
task_information['choice'] = ['right', 'left']  # lick port
task_information['reward'] = ['small', 'large']  # reward size
task_information['reward_size'] = {'small': 10, 'large': 20}

# define timeout during each condition
task_information['initiation_timeout'] = 3 #s
task_information['cue_timeout'] = 3
task_information['reward_timeout'] = 3

# block setup
task_information['block'] = {}
task_information['block'][1] = [
    # block_1 forced component
    (1, 0, 0, 1),  # forced choice block 1
    (1, 1, 1, 1),  # 0, 1 index for corresponding condition setup
    (0, 0, 1, 0),  # column 0 is cue, 1 is state, 2 is choice, 3 is reward_amount
    (0, 1, 0, 0),  # each row is a combination of the condition parameter for block 1
    # block_1 free component
    (2, 0, 0, 1),  # free choice block 1
    (2, 0, 1, 0),  # 0, 1 index for corresponding condition setup, 2 in column 0
    (2, 1, 0, 0),  # means both cues are on
    (2, 1, 0, 1)]  # each row is a combination of the condition parameter for block 1

task_information['block'][2] = [
    # block_2 forced component
    (1, 0, 0, 0),  # forced choice block 2
    (1, 1, 1, 0),  # 0, 1 index for corresponding condition setup
    (0, 0, 1, 1),  # column 0 is cue, 1 is state, 2 is choice, 3 is reward_amount
    (0, 1, 0, 1),  # each row is a combination of the condition parameter for block 1
    # block_2 free component
    (2, 0, 0, 0),  # free choice block 2
    (2, 0, 1, 1),  # 0, 1 index for corresponding condition setup, None in column 0
    (2, 1, 0, 1),  # means both cues are on
    (2, 1, 0, 0)]  # each row is a combination of the condition parameter for block 1

# now shuffle and make a deck for this session
# shuffle requirement

# allowing user defined initial_block and initial setup for conditions?
task_information["initial_block"] = 1

# allowing consecutive repeated trial?
consecutive_control = True
if consecutive_control:
    consecutive_max = 3

block_length_list = {
    1: 10,
    2: 10
}
task_information['block_name_list'] = [block_length_list.keys()]

def generate_deck(duration, consecutive_control, consecutive_max):
    consecutive_count = 0
    row_buffer = -1
    deck_list = []
    for iteration in range(duration):
        row_index = random.randrange(0, 8)
        while True:
            if row_index == row_buffer and consecutive_control:
                if consecutive_count >= consecutive_max:
                    row_index = random.randrange(0, 8)
                else:
                    break
            else:
                break
        row_buffer = row_index
        deck_list.append(row_index)
    return deck_list

block_length = 10
block_list = []
initial_block = 1  # False if no initial block


def shuffle(block_length, block_list, initial_block):
    if initial_block:
        block_list.append(initial_block)
        block_list.extend([random.randrange(1, 3) for i in range(block_length - 1)])
    else:
        block_list = [random.randrange(1, 3) for i in range(block_length)]

    deck = []
    for block in block_list:
        deck_list_buffer = generate_deck(block_length_list[1], consecutive_control, consecutive_max)
        current_deck = []
        block_map = task_information['block'][block]
        for row_index in deck_list_buffer:
            current_deck.append(block_map[row_index])
        deck.extend(current_deck)
    return deck


task_information["deck"] = shuffle(block_length, block_list, initial_block)
