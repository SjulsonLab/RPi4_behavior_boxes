# Python3: task_information_2022_02_14.py
import random


class TaskInformation(object):
    def __init__(self, **kwargs):
        self.name = "model_based_reinforcement_learning_task"
        self.block = {
            1: [
                # block_1 forced component
                ('LED', 'distance_short', 'right', 'large', '2'),  # 0, 1 index for corresponding condition setup
                ('LED', 'distance_long', 'left', 'large', '1'),  # forced choice block 1

                ('sound', 'distance_short', 'left', 'small', '3'),
                # column 0 is cue, 1 is state, 2 is choice, 3 is reward_amount
                ('sound', 'distance_long', 'right', 'small', '4'),

                # each row is a combination of the condition parameter for block 1
                # block_1 free component
                # modification on block_1 free component
                ('sound+LED', 'distance_short', ('left', 'right'), ('small', 'large'), ('3','2')),
                ('sound+LED', 'distance_long', ('left', 'right'), ('large', 'small'), ('1','4'))
                """old version"""
                # ('sound+LED', 'distance_short', 'right', 'large', '2'),  # free choice block 1
                # ('sound+LED', 'distance_short', 'left', 'small', '3'),  # LED
                # # 0, 1 index for corresponding condition setup, 2 in column 0
                # ('sound+LED', 'distance_long', 'left', 'large', '1'),  # means both cues are on
                # ('sound+LED', 'distance_long', 'right', 'small', '4')
                """old version ends here"""
            ],
            2: [
                # block_2 forced component
                ('LED', 'distance_short', 'right', 'small', '2'),  # 0, 1 index for corresponding condition setup
                ('LED', 'distance_long', 'left', 'small', '1'),  # forced choice block 1

                ('sound', 'distance_short', 'left', 'large', '3'),
                # column 0 is cue, 1 is state, 2 is choice, 3 is reward_amount
                ('sound', 'distance_long', 'right', 'large', '4'),

                # each row is a combination of the condition parameter for block 1
                # modification on block_1 free component
                ('sound+LED', 'distance_short', ('left', 'right'), ('large', 'small'), ('3','2')),
                ('sound+LED', 'distance_long', ('left', 'right'), ('small', 'large'), ('1','4'))
                """old version"""
                # ('sound+LED', 'distance_short', 'right', 'small', '2'),  # free choice block 1
                # ('sound+LED', 'distance_short', 'left', 'large', '3'),
                # # 0, 1 index for corresponding condition setup, 2 in column 0
                # ('sound+LED', 'distance_long', 'left', 'small', '1'),  # means both cues are on # sound
                # ('sound+LED', 'distance_long', 'right', 'large', '4')
                """old version ends here"""
            ]}

    def draw_card(self, block_key, phase="final"):
        row_start = 0
        row_end = 6
        if phase == 'final':
            pass
        elif phase == 'forced_choice':
            row_end = 3
        elif phase == 'free_choice':
            """old version"""
            row_start = 4
            # row_end = 7
            """old version ends here"""
            row_start = 4
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
