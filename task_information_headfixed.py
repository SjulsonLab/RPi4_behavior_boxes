# Python3: task_information_2022_02_14.py
import random


class TaskInformation(object):
    def __init__(self, **kwargs):
        self.name = "model_based_reinforcement_learning_task"
        self.block = {
            1: [
                # block_1 forced component
                ('LED', 'distance_short', 'right', 'large'),  # forced choice block 1
                ('LED', 'distance_long', 'left', 'large'),  # 0, 1 index for corresponding condition setup
                ('sound', 'distance_short', 'left', 'small'),
                # column 0 is cue, 1 is state, 2 is choice, 3 is reward_amount
                ('sound', 'distance_long', 'right', 'small'),
                # each row is a combination of the condition parameter for block 1
                # block_1 free component
                ('sound+LED', 'distance_short', 'right', 'large'),  # free choice block 1
                ('sound+LED', 'distance_short', 'left', 'small'),
                # 0, 1 index for corresponding condition setup, 2 in column 0
                ('sound+LED', 'distance_long', 'right', 'small'),  # means both cues are on
                ('sound+LED', 'distance_long', 'right', 'large')],
            2: [
                # block_2 forced component
                ('LED', 'distance_short', 'right', 'small'),  # forced choice block 2
                ('LED', 'distance_long', 'left', 'small'),  # 0, 1 index for corresponding condition setup
                ('sound', 'distance_short', 'left', 'large'),
                # column 0 is cue, 1 is state, 2 is choice, 3 is reward_amount
                ('sound', 'distance_long', 'right', 'large'),
                # each row is a combination of the condition parameter for block 1
                # block_2 free component
                ('sound+LED', 'distance_short', 'right', 'small'),  # free choice block 2
                ('sound+LED', 'distance_short', 'left', 'large'),
                # 0, 1 index for corresponding condition setup, None in column 0
                ('sound+LED', 'distance_long', 'right', 'large'),  # means both cues are on
                ('sound+LED', 'distance_long', 'right', 'small')]}

    def draw_card(self, block_key, phase):
        row_start = 0
        row_end = 7
        if phase == 'forced_choice':
            row_end = 3
        elif phase == 'free_choice':
            row_start = 4
            row_end = 7
        elif phase == 'forced_choice_LED':
            row_end = 1
        elif phase == 'forced_choice_sound':
            row_start = 2
            row_end = 3
        block_map = self.block[block_key]
        row_index = random.randint(row_start, row_end)
        print(str(row_index))
        card = block_map[row_index]

        return card
# print(TaskInformation().draw_card(2,'free_choice'))