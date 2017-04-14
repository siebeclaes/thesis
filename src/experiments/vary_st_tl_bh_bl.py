import sys
import numpy as np
from pymongo import MongoClient
import feedback_cpg as sim
from model_variations import generate_temp_model_file, generate_model_variations
import multiprocessing


# MODEL PARAMETERS
model_config = {
	'body': {
		'width': 15,
		'height': 3,
		'length': 25
	},
	'legs': {
		'FL': {
			'motor': {
				'width': 3.6,
				'length': 3.6,
				'height': 5.06,
				'leg_attachment_height': 3.3,
			},
			'position': 'front',
			'leg_attachment_height_offset': 0, # height offset of the leg attachment point relative to the middle of height of the body
			'leg_attachment_length_offset': 3, # offset of leg attachment point relative to front of body
			'femur_length': 7,
			'femur_angle': 25, # angle between femur and vertical in degrees
			'tibia_length': 8.5,
			'spring_length': 2.5,
			'femur_spring_tibia_joint_dst': 4.5,
			'tibia_spring_to_joint_dst': 3.5,
			'hip_damping': 0.2,
			'knee_damping': 0.2,
			'spring_stiffness': 400,
			'actuator_kp': 254,
		},
		'FR': {
			'motor': {
				'width': 3.6,
				'length': 3.6,
				'height': 5.06,
				'leg_attachment_height': 3.3,
			},
			'position': 'front',
			'leg_attachment_height_offset': 0, # height offset of the leg attachment point relative to the middle of height of the body
			'leg_attachment_length_offset': 3, # offset of leg attachment point relative to front of body
			'femur_length': 7,
			'femur_angle': 25, # angle between femur and vertical in degrees
			'tibia_length': 8.5,
			'spring_length': 2.5,
			'femur_spring_tibia_joint_dst': 4.5,
			'tibia_spring_to_joint_dst': 3.5,
			'hip_damping': 0.2,
			'knee_damping': 0.2,
			'spring_stiffness': 400,
			'actuator_kp': 254,
		},
		'BL': {
			'motor': {
				'width': 3.6,
				'length': 3.6,
				'height': 5.06,
				'leg_attachment_height': 3.3,
			},
			'position': 'back',
			'leg_attachment_height_offset': 0, # height offset of the leg attachment point relative to the middle of height of the body
			'leg_attachment_length_offset': 3, # offset of leg attachment point relative to front of body
			'femur_length': 7,
			'femur_angle': 0, # angle between femur and vertical in degrees
			'tibia_length': 8.5,
			'spring_length': 2.5,
			'femur_spring_tibia_joint_dst': 4.5,
			'tibia_spring_to_joint_dst': 3.5,
			'hip_damping': 0.2,
			'knee_damping': 0.2,
			'spring_stiffness': 400,
			'actuator_kp': 254,
		},
		'BR': {
			'motor': {
				'width': 3.6,
				'length': 3.6,
				'height': 5.06,
				'leg_attachment_height': 3.3,
			},
			'position': 'back',
			'leg_attachment_height_offset': 0, # height offset of the leg attachment point relative to the middle of height of the body
			'leg_attachment_length_offset': 3, # offset of leg attachment point relative to front of body
			'femur_length': 7,
			'femur_angle': 0, # angle between femur and vertical in degrees
			'tibia_length': 8.5,
			'spring_length': 2.5,
			'femur_spring_tibia_joint_dst': 4.5,
			'tibia_spring_to_joint_dst': 3.5,
			'hip_damping': 0.2,
			'knee_damping': 0.2,
			'spring_stiffness': 400,
			'actuator_kp': 254,
		},
	},
}

EXPERIMENT_TAG = 'vary_st_tl_bh_bl'
NUM_OPTIMIZATION_STEPS = 200
E_0 = 30
# NUM_VARIATIONS = 15

def perform_experiment(num_variations):
	from Experiment import Experiment
	variation_params_spring = {'body': {
		'length': {'normal': [0, 1]},
		'height': {'normal': [0, 0.3]},
		},
		'legs': {
			'FL': {
				'tibia_length': {'normal': [0, 0.9]},
				'spring_stiffness': {'normal': [0, 40]},
			},
			'FR': {
				'tibia_length': {'normal': [0, 0.9]},
				'spring_stiffness': {'normal': [0, 40]},
			},
			'BL': {
				'tibia_length': {'normal': [0, 0.9]},
				'spring_stiffness': {'normal': [0, 40]},
			},
			'BR': {
				'tibia_length': {'normal': [0, 0.9]},
				'spring_stiffness': {'normal': [0, 40]},
			},
		},
	}
	
	lb = [15, 15, 15, 15, -30, -30, 0.5, 0.5, 0.2, 0.2, 0, 0, 0, 0, 0, 0, 0]
	ub = [45, 45, 45, 45, 30, 30, 3, 3, 0.7, 0.7, 1, 1, 1, 1, 1, 1, 2*np.pi]

	initial = [25, 25, 25, 25, 0, 0, 0.6, 0.6, 0.2, 0.2, 0, 1, 1, 1, 1, 0, np.pi]

	e = Experiment(model_config, False, initial, lb, ub, 0.5, NUM_OPTIMIZATION_STEPS, E_0, variation_params=variation_params_spring, num_variations=num_variations, perturbation_params=None, experiment_tag=EXPERIMENT_TAG, experiment_tag_index=num_variations)
	e.run()

def run():
	variances = [5, 10, 15, 20]
	# variances = [i**2 for i in np.arange(0.1, 1.6, 0.1)]

	for variance in variances:
		perform_experiment(variance)

def get_experiments():
	client = MongoClient('localhost', 27017)
	db = client['thesis']
	experiments_collection = db['experiments']

	return experiments_collection.find({'experiment_tag': EXPERIMENT_TAG})

def eval_wrapper(variables):
	model_file = variables['model_file']
	closed_loop = variables['closed_loop']
	params = variables['params']
	perturbations = variables['perturbations']
	render = variables['render']
	logging = variables['logging']
	return sim.evaluate(model_file, closed_loop, params, perturbations, render, logging)

def test_experiment(experiment):
	num_variations = 30
	default_morphology = experiment['default_morphology']
	variation_params = experiment['variation_params']
	model_files, delta_dicts = generate_model_variations(default_morphology, variation_params, num_variations)
	solution_perturbations = [[]] * len(model_files)

	cpg_params = experiment['results']['simulations'][experiment['results']['best_id']]['cpg_params']
	logging = False
	render = False

	mp_pool = multiprocessing.Pool(8)

	x = [{'model_file': model_file, 'closed_loop': False, 'params': cpg_params, 'render': False, 'logging': logging, 'perturbations': p} for model_file, p in zip(model_files, solution_perturbations)]
	results = mp_pool.map(eval_wrapper, x)

	rewards = []

	for result in results:
		succes, simulated_time, distance, energy_consumed, action_history, sensor_history = result

		# reward = 0 if distance < 0 or not succes else 1.447812*9.81*distance/(energy_consumed+20)
		reward = 0 if distance < 0 or not succes else (10-0.01*(energy_consumed-experiment['E0'])**2)*(distance)
		rewards.append(reward)

	return rewards

def test_results():
	import matplotlib.pyplot as plt
	indices, mins, avgs, maxs, stds = [], [], [], [], []

	for doc in get_experiments():
		rewards = test_experiment(doc)
		indices.append(np.sqrt(doc['experiment_tag_index']))
		# mins.append(min(rewards))
		avgs.append(sum(rewards)/len(rewards))
		# maxs.append(max(rewards))
		stds.append(np.std(rewards))

	plt.figure()
	plt.errorbar(indices, avgs, yerr=stds, color='blue', label='Average')
	plt.xlabel('Number of variations in training sample')
	plt.ylabel('Reward')
	plt.legend()

	plt.show()


def view_results():
	import matplotlib.pyplot as plt
	print('Showing results...')
	client = MongoClient('localhost', 27017)
	db = client['thesis']
	experiments_collection = db['experiments']

	indices, mins, avgs, maxs, stds = [], [], [], [], []

	for doc in experiments_collection.find({'experiment_tag': EXPERIMENT_TAG}):
		variation_best = analyze_variation_performance(doc)
		indices.append(np.sqrt(doc['experiment_tag_index']))
		mins.append(min(variation_best))
		avgs.append(sum(variation_best)/len(variation_best))
		maxs.append(max(variation_best))
		stds.append(np.std(variation_best))

	f, axarr = plt.subplots(2, sharex=True)

	# TODO: include std deviation reward on same plot (bars around point)
	axarr[0].plot(indices, mins, color='green', label='Minimum')
	axarr[0].plot(indices, avgs, color='blue', label='Average')
	axarr[0].plot(indices, maxs, color='red', label='Maximum')
	axarr[0].set_xlabel('Spring stiffness standard deviation')
	axarr[0].set_ylabel('Reward')
	axarr[0].legend()

	axarr[1].plot(indices, stds, color='yellow', label='Standard deviation')
	axarr[0].set_xlabel('Spring stiffness standard deviation')
	axarr[1].set_ylabel('Std deviation')

	plt.show()

def analyze_variation_performance(experiment):
    variation_best = [0] * len(experiment['delta_dicts'])

    for simulation in experiment['results']['simulations']:
        variation_index = simulation['variation_index']
        reward = simulation['reward']

        if reward > variation_best[variation_index]:
            variation_best[variation_index] = reward

    return variation_best


if __name__ == '__main__':
	if len(sys.argv) < 2:
		print('Please specify run or results')

	if sys.argv[1] == 'train':
		run()
	elif sys.argv[1] == 'train_results':
		view_results()
	elif sys.argv[1] == 'test':
		test_results()

	

	