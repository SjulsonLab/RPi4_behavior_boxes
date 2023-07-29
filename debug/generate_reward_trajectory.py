def cumsum_positive(input_list):
  for index in range(len(input_list)):
    if index == 0 and input_list[index]<0:
      input_list[index] = -input_list[index]
    elif input_list[index]+input_list[index-1]<0:
      input_list[index] = input_list[index] - input_list[index-1]
    else:
      input_list[index] = input_list[index] + input_list[index-1]
  return input_list

def generate_reward_trajectory(scale=0.5, offset=3.0, change_point=20, ntrials=200):
    # initial reward (need to be random)
    rewards_L = [1]
    rewards_R = [1]
    for a in np.arange(np.round(ntrials / change_point)):
        temp = np.random.randn(change_point) * scale
        # temp = np.random.uniform(low=0.0, high=10, size=(change_point,))

        # print("ay o" + str(temp))
        # while temp < 0:
        #     temp = np.random.randn(change_point) * scale
        rewards_L.append(cumsum_positive(temp) + offset)
        temp = np.random.randn(change_point) * scale
        # temp = np.random.uniform(low=0.0, high=10, size=(change_point,))
        # while temp < 0:
        #     temp = np.random.randn(change_point) * scale
        rewards_R.append(cumsum_positive(temp) + offset)
    rewards_L = np.hstack(rewards_L)
    rewards_R = np.hstack(rewards_R)
    # plt.plot(rewards_L,'b');plt.plot(rewards_R,'r--')
    reward_LR = [rewards_L, rewards_R]
    reward_LR = np.transpose(np.array(reward_LR))
    reward_LR = reward_LR[0:ntrials, :]
    # print(reward_LR)
    return reward_LR

# from reward_distribution import generate_reward_trajectory
scale = 0.5
offset = 3.0
change_point = 20
ntrials = 100

reward_distribution_list = generate_reward_trajectory(scale, offset, change_point, ntrials)

print(reward_distribution_list)