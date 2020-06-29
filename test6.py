"""
Code to learn avDSR agent
"""

# Setting up 
from deep_rl import *
import matplotlib.pyplot as plt
import torch
from tqdm.notebook import trange, tqdm
import random
import numpy as np
import pickle

select_device(0)

def dqn_feature(**kwargs):
    generate_tag(kwargs)
    kwargs.setdefault('log_level', 0)
    config = Config()
    config.merge(kwargs)

    config.task_fn = lambda: Task(config.game)
    config.eval_env = config.task_fn()

    config.optimizer_fn = lambda params: torch.optim.RMSprop(params, 0.001)
    config.network_fn = lambda: VanillaNet(config.action_dim, FCBody(config.state_dim, hidden_units=(16,)))
    # config.network_fn = lambda: DuelingNet(config.action_dim, FCBody(config.state_dim))
    # config.replay_fn = lambda: Replay(memory_size=int(1e4), batch_size=10)
    config.replay_fn = lambda: Replay(memory_size=int(1e4), batch_size=10)

    config.random_action_prob = LinearSchedule(1.0, 0.1, 3e4)
    config.discount = 0.99
    config.target_network_update_freq = 200
    config.exploration_steps = 0
    # config.double_q = True
    config.double_q = False
    config.sgd_update_frequency = 4
    config.gradient_clip = 5
    config.eval_interval = int(5e3)
    config.max_steps = 1e1
    config.async_actor = False
    agent = DQNAgent(config)
    #run_steps function below
    config = agent.config
    agent_name = agent.__class__.__name__
    t0 = time.time()
    while True:
        if config.save_interval and not agent.total_steps % config.save_interval:
            agent.save('data/%s-%s-%d' % (agent_name, config.tag, agent.total_steps))
        if config.log_interval and not agent.total_steps % config.log_interval:
            t0 = time.time()
        if config.eval_interval and not agent.total_steps % config.eval_interval:
            agent.eval_episodes()
            pass
        if config.max_steps and agent.total_steps >= config.max_steps:
            return agent
            break
        agent.step()
        agent.switch_task()
    return agent



def avdsr_feature(ref, **kwargs):
    kwargs['tag'] = 'Training avDSR based on DQN agents'
    generate_tag(kwargs)
    kwargs.setdefault('log_level', 0)
    config = Config()
    config.merge(kwargs)

    config.task_fn = lambda: Task(config.game)
    config.eval_env = config.task_fn()
    config.c = 1

    config.optimizer_fn = lambda params: torch.optim.RMSprop(params, 0.001)
    config.network_fn = lambda: SRNetCNN(config.action_dim, SRIdentityBody(config.state_dim), 
                                         hidden_units=(2000,), config=0) #CHECK
    config.replay_fn = lambda: Replay(memory_size=int(4e5), batch_size=10)

    config.random_action_prob = LinearSchedule(1, 1, 1e4) # CHECK
    config.discount = 0.99
    config.target_network_update_freq = 200
    config.exploration_steps = 0
    # config.double_q = True
    config.double_q = False
    config.sgd_update_frequency = 4
    config.gradient_clip = 5
    config.max_steps = 3e5+1
    config.async_actor = False
    
    agent = avDSRAgent(config, config.agents, style='DQN')
    if(ref is not None):
        agent.network.load_state_dict(ref, strict=True)

    #run_steps function below
    config = agent.config
    agent_name = agent.__class__.__name__
    t0 = time.time()
    while True:
        if(agent.total_steps in record_iters):
            # Saving the model
            torch.save(agent.network, 'storage/'+ind+'-'+str(agent.total_steps)+'-avdsr.weights')
        if config.log_interval and not agent.total_steps % config.log_interval:
            agent.logger.info('steps %d, %.2f steps/s' % (agent.total_steps, config.log_interval / (time.time() - t0)))
            t0 = time.time()
        if config.max_steps and agent.total_steps >= config.max_steps:
            return agent
            break
        agent.step()
        agent.switch_task()


# To train eps = 1 agent, uncomment below
# ind = '01'
# agents = []
# goals = [21]
# for g in goals:
#     game = 'FourRoomsMatrix-Goal-'+str(g)
#     agents.append(dqn_feature(game=game))
# avdsr = avdsr_feature(game='FourRoomsMatrixNoTerm', agents=agents, choice=0)

# To train eps = 0.9 agent, uncomment below
ind = '17' # 19
style2 = 2 # 1
agents = []
goals = [21]
for g in goals:
    game = 'FourRoomsMatrix-Goal-'+str(g)
    agents.append(dqn_feature(game=game))
record_iters = [0, 1e2, 1e3, 3e3, 1e4, 2e4, 5e4, 1e5, 2e5, 3e5]

if(style2 == 0): # option 2
    avdsr = avdsr_feature(game='Dy-FourRoomsMatrixNoTerm', agents=agents, choice=0, ref=None)
if(style2 == 1): # option 1
    avdsr = avdsr_feature(game='FourRoomsMatrixNoTerm', agents=agents, choice=0, ref=None)
if(style2 == 2): # option 2 init for option 1
    weights = torch.load('storage/15-300000-avdsr.weights').state_dict()
    avdsr = avdsr_feature(game='FourRoomsMatrixNoTerm', agents=agents, choice=0, ref=weights)
    

# Saving the loss function
with open('storage/'+ind+'-loss.p', 'wb') as f:
    pickle.dump(avdsr.loss_vec, f, pickle.HIGHEST_PROTOCOL)