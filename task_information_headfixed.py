# Python3: task_information_2022_02_14.py
import collections
import itertools
import random

task_information = collections.OrderedDict()
task_information['experiment_setup'] = 'headfixed'
task_information['treadmill_setup'] = {'present': True}

if task_information['treadmill_setup']['present']:
    task_information['treadmill_setup']['distance_initiation'] = 5  # cm
    task_information['treadmill_setup']['distance_short'] = 7  # cm
    task_information['treadmill_setup']['distance_long'] = 30 # cm
else:
    task_information['treadmill_setup'] = None

task_information['error_repeat'] = True
if task_information['error_repeat']:
    task_information['error_repeat_max'] = 3

# condition setup
task_information['cue'] = ['sound', 'LED', 'sound+LED']
task_information['state'] = ['distance_short', 'distance_long']  # treadmill distance
task_information['choice'] = ['right', 'left']  # lick port
task_information['reward'] = ['small', 'large']  # reward size
task_information['reward_size'] = {'small': 5, 'large': 10}

# define timeout during each condition
task_information['initiation_timeout'] = 5  # s
task_information['cue_timeout'] = 5
task_information['reward_timeout'] = 5

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

# define block_duration and initial block to start the session
block_duration = 2  # each block has this amount of repetition
block_variety = 2
if block_variety > 1:
    initial_block = 1

# now shuffle and make a deck for this session
# shuffle requirement

# # allowing user defined initial_block and initial setup for conditions?
# task_information["initial_block"] = 1
#
# allowing consecutive repeated trial?
consecutive_control = True
if consecutive_control:
    consecutive_max = 3


def generate_block_sequence(number_block, sequence_length, initial_character):
    if not initial_character:
        initial_character = random.randint(1, 2)
    if number_block == 1:
        sequence = [initial_character]
    else:
        if initial_character - 1:
            sequence = [initial_character, initial_character - 1]
        else:
            sequence = [initial_character, initial_character + 1]
    sequence = sequence * sequence_length
    return sequence


# the block list is used for 1) generate a shuffled deck; 2) a list for keeping track of what block is the
# current card is located
block_list = generate_block_sequence(block_variety, block_duration, initial_block)


task_information["block_list"] = list(
    itertools.chain.from_iterable(itertools.repeat(iterate, block_duration) for iterate in block_list))


def generate_deck(duration, consecutive_permit, repetition_max):
    consecutive_count = 0
    row_buffer = -1
    deck_list = []
    for iteration in range(duration):
        row_index = random.randrange(0, 8)
        while True:
            if row_index == row_buffer and consecutive_permit:
                if consecutive_count >= repetition_max:
                    row_index = random.randrange(0, 8)
                else:
                    break
            else:
                break
        row_buffer = row_index
        deck_list.append(row_index)
    return deck_list


def shuffle(block_sequence, duration_block):
    deck = []
    for block in block_sequence:
        deck_list_buffer = generate_deck(duration_block, consecutive_control, consecutive_max)
        current_deck = []
        block_map = task_information['block'][block]
        for row_index in deck_list_buffer:
            current_deck.append(block_map[row_index])
        deck.extend(current_deck)
    return deck


task_information["deck"] = shuffle(block_list, block_duration)
