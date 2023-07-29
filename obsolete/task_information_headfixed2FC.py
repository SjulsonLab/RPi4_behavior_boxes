import random


class TaskInformation(object):
    def __init__(self, **kwargs):
        self.name = "model_based_reinforcement_learning_task"
        self.block = {
            1: [
                # block_1 forced component
                ('LED_L', 'left', 'large', '1'),  # forced choice block 1
                ('LED_R',  'right', 'small', '2'),  # 0, 1 index for corresponding condition setup
                # block_1 free component
                ('all',  ('left', 'right'), ('large', 'small'), ('1','2'))
              ],
            2: [
                # block_2 forced component
                ('LED_L', 'left', 'small', '1'),  # forced choice block 1
                ('LED_R', 'right', 'large', '2'),  # 0, 1 index for corresponding condition setup
                ('all',  ('left', 'right'), ('small', 'large'), ('1','2'))
            ]}

    def draw_card(self, block_key, phase="final"):
        row_start = 0
        row_end = 2
        if phase == 'final':
            pass
        elif phase == 'forced_choice':
            row_end = 1
        elif phase == 'free_choice':
            row_start = 2
        elif phase == 'forced_choice_left':
            row_end = 0
        elif phase == 'forced_choice_right':
            row_start = 1
            row_end = 1
        block_map = self.block[block_key]
        row_index = random.randint(row_start, row_end)
        print(str(row_index))
        card = block_map[row_index]

        return card
# print(TaskInformation().draw_card(2,'free_choice'))
