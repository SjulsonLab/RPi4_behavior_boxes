import random


class TaskInformation(object):
    def __init__(self, **kwargs):
        self.name = "two choice habituation task"
        self.deck = [('LED_L', 'left', '1'), ('LED_R',  'right', '2'),
                     ('LED_L', 'left', '1'), ('LED_R',  'right', '2'),
                     ('LED_L', 'left', '1'), ('LED_R', 'right', '2'),
                     ('LED_L', 'left', '1'), ('LED_R', 'right', '2'),
                     ('LED_L', 'left', '1'), ('LED_R', 'right', '2'),
                     ('all',  ('left', 'right'), ('1', '2')), ('all',  ('left', 'right'), ('1', '2')),
                     ('all', ('left', 'right'), ('1', '2')), ('all', ('left', 'right'), ('1', '2')),
                     ('all', ('left', 'right'), ('1', '2')), ('all', ('left', 'right'), ('1', '2')),
                     ('all', ('left', 'right'), ('1', '2')), ('all', ('left', 'right'), ('1', '2')),
                     ('all', ('left', 'right'), ('1', '2')), ('all', ('left', 'right'), ('1', '2')),
                     ]

    def draw_card(self, phase="independent_reward", fraction=0.5):
        row_start = 0
        row_end = len(self.deck)-1

        if phase == 'forced_choice':
            row_end = 1
        elif phase == 'free_choice':
            row_start = 9
        elif phase == 'forced_choice_left':
            row_end = 0
        elif phase == 'forced_choice_right':
            row_start = 1
            row_end = 1
        elif phase == 'habituation':
            row_start = 9
        else:
            if fraction == 0.5:
                row_start = 8
                row_end = 11
            elif fraction == 0.7:
                row_start = 6
            elif fraction == 0.3:
                row_end = 13
            elif fraction == 1:
                row_start = 11

        card = self.deck[random.randint(row_start, row_end)]
        return card

# print(TaskInformation().draw_card())