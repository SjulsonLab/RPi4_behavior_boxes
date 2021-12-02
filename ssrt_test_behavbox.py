
import behavbox_DT as box
pump = box.Pump()

test_running = True
while test_running:
    reward_duration = float(input("What is the reward duration: \n"))
    reward_size = 91  # this is one whole revolution
    # reward_duration = 1
    pump.reward("center", reward_size, reward_duration)  # currently using left pump for the task
    ask_continue = input('Do you want to continue? (y or n) \n')
    if ask_continue == "n":
        test_running = False
        break



