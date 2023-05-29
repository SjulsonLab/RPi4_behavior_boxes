import random


class TaskInformation(object):
    def __init__(self, **kwargs):
        self.name = "model_based_reinforcement_learning_task"
        self.deck = [('LED_L', 'left', '1'), ('LED_R',  'right', '2'), ('all',  ('left', 'right'), ('1', '2'))]

    def draw_card(self, phase="final"):
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
        card = self.deck[random.randint(row_start, row_end)]
        return card

# print(TaskInformation().draw_card())
