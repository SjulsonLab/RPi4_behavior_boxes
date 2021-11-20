
import behavbox_DT
pump = box.Pump()
box = behavbox_DT

test_running = True
while test_running:
    reward_size = int(input("What is the reward size: \n"))
    pump.reward("left", reward_size)  # currently using left pump for the task
    ask_continue = input('Do you want to continue? (y or n) \n')
    if ask_continue == "n":
        test_running = False
        break





