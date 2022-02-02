import behavbox_DT as box

##### Import the pump object and define parameters for reward method
pump = box.Pump
which_pump = "left"  # could be "center" or "right"
reward_size = 12  # in mL
reward_duration = 0.01  # fastest

##### Call the reward method to deliver the reward
pump.reward(which_pump, reward_size, reward_duration)