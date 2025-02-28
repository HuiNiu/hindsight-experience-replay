import torch
from rl_modules.models import actor
from arguments import get_args
import gym
import numpy as np
from datetime import datetime
from envs.gym_robotics import *

# process the inputs
def process_inputs(o, g, o_mean, o_std, g_mean, g_std, args):
    o_clip = np.clip(o, -args.clip_obs, args.clip_obs)
    g_clip = np.clip(g, -args.clip_obs, args.clip_obs)
    o_norm = np.clip((o_clip - o_mean) / (o_std), -args.clip_range, args.clip_range)
    g_norm = np.clip((g_clip - g_mean) / (g_std), -args.clip_range, args.clip_range)
    inputs = np.concatenate([o_norm, g_norm])
    inputs = torch.tensor(inputs, dtype=torch.float32)
    return inputs

if __name__ == '__main__':
    args = get_args()
    # load the model param
    model_path = args.model_path + "/model.pt"
    # model_path = 'saved_models/HandManipulateBlockRotateZ-v0_Nov29_10-50-16_hier_False/model.pt'
    # model_path = args.save_dir + args.env_name + '/model.pt'
    o_mean, o_std, g_mean, g_std, model = torch.load(model_path, map_location=lambda storage, loc: storage)
    # create the environment
    env = gym.make(args.env_name)
    # get the env param
    observation = env.reset()
    # get the environment params
    env_params = {'obs': observation['observation'].shape[0], 
                  'goal': observation['desired_goal'].shape[0], 
                  'action': env.action_space.shape[0], 
                  'action_max': env.action_space.high[0],
                  'action_space': env.action_space
                  }
    # create the actor network
    actor_network = actor(env_params, args.cuda)
    actor_network.load_state_dict(model)
    actor_network.eval()
    distance_list = []
    success = 0.
    for i in range(args.demo_length):
        observation = env.reset()
        # start to do the demo
        obs = observation['observation']
        g = observation['desired_goal']
        sum_d = 0.
        for t in range(env._max_episode_steps):
            # env.render()
            inputs = process_inputs(obs, g, o_mean, o_std, g_mean, g_std, args)
            with torch.no_grad():
                pi = actor_network(inputs)
            action = pi.detach().numpy().squeeze()
            # put actions into the environment
            observation_new, reward, _, info = env.step(action)
            # calcualte distance to goal
            d_pos, d_rot = env.env._goal_distance(observation_new['achieved_goal'], observation_new['desired_goal'])
            sum_distance = -(10. * d_pos + d_rot)
            sum_d += sum_distance
            obs = observation_new['observation']
            if info['is_success']:
                success += 1
                break
        distance_list.append(sum_d)
        print('the episode is: {}, is success: {}'.format(i, info['is_success']))

    print("mean distance", np.mean(distance_list))
    print("average success", success / args.demo_length)
