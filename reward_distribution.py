import numpy as np

def generate_reward_trajectory(scale=0.5, offset=3.0, change_point=20, ntrials=200):
        # initial reward (need to be random)
        rewards_L = [1]
        rewards_R = [1]
        for a in np.arange(np.round(ntrials/change_point)):
                temp = np.random.randn(change_point)*scale
                rewards_L.append(np.cumsum(temp, axis=-1) + offset)
                temp = np.random.randn(change_point)*scale
                rewards_R.append(np.cumsum(temp, axis=-1) + offset)
        rewards_L=np.hstack(rewards_L)
        rewards_R=np.hstack(rewards_R)
        #plt.plot(rewards_L,'b');plt.plot(rewards_R,'r--')
        reward_LR = [rewards_L, rewards_R]
        reward_LR  = np.transpose(np.array(reward_LR))
        reward_LR = reward_LR[0:ntrials,:]
        print(reward_LR)
        return reward_LR
# generate_reward_trajectory()
# session_information['reward']['scale']
# session_information['reward']['offset']
# session_information['reward']['change_point']
# session_information['reward']['ntrials']