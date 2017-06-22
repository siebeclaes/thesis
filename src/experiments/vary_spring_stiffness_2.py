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
			'spring_stiffness': 211,
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
			'spring_stiffness': 211,
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
			'spring_stiffness': 211,
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
			'spring_stiffness': 211,
			'actuator_kp': 254,
		},
	},
}

EXPERIMENT_TAG = 'vary_spring_stiffness_2'
NUM_OPTIMIZATION_STEPS = 250
E_0 = 30
NUM_VARIATIONS = 10

def perform_experiment(spring_stiffness_stdev, E_ref):
	from Experiment import Experiment
	variation_params_spring = {'legs': {
			'FL': {
				'spring_stiffness': {'normal': [0, spring_stiffness_stdev**2]},
			},
			'FR': {
				'spring_stiffness': {'normal': [0, spring_stiffness_stdev**2]},
			},
			'BL': {
				'spring_stiffness': {'normal': [0, spring_stiffness_stdev**2]},
			},
			'BR': {
				'spring_stiffness': {'normal': [0, spring_stiffness_stdev**2]},
			},
		},
	}

	remark = 'vary spring stiffness E_ref = ' + str(E_ref) + ' stdev spring stiffness = ' + str(spring_stiffness_stdev)

	lb = [30, 30, 30, 30, -30, -30, 0.5, 0.2, 0.2, 0, 0, 0]
	ub = [60, 60, 60, 60, 30, 30, 3, 0.7, 0.7, 2*np.pi, 2*np.pi, 2*np.pi]

	initial = [35, 35, 35, 35, 0, 0, 0.6, 0.4, 0.4, 0, 0, 0]

	e = Experiment(model_config, False, initial, lb, ub, 0.5, NUM_OPTIMIZATION_STEPS, E0=E_ref, variation_params=variation_params_spring, num_variations=NUM_VARIATIONS, perturbation_params=None, remarks=remark)
	e.run()

def run():
	stdevs = [20]
	E_refs = [20, 30, 40, 50, 60]

	for stdev in stdevs:
		for E_ref in E_refs:
			perform_experiment(stdev, E_ref)

def get_experiments():
	client = MongoClient('localhost', 27017)
	db = client['thesis']
	experiments_collection = db['experiments_2']

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
	num_variations = 40
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

	rewards, distances, energies = [], [], []

	for result in results:
		succes, simulated_time, distance, energy_consumed, action_history, sensor_history = result

		# reward = 0 if distance < 0 or not succes else 1.447812*9.81*distance/(energy_consumed+20)
		reward = 0 if distance < 0 or not succes else (10-0.01*(energy_consumed-experiment['E0'])**2)*(distance)
		rewards.append(reward)
		distances.append(distance)
		energies.append(energy_consumed)

	return (rewards, distances, energies)

def test_results():
	import matplotlib.pyplot as plt
	indices, mins, avgs, maxs, stds = [], [], [], [], []
	avg_distance = []
	avg_energy = []
	stds_distance = []
	stds_energy = []

	for doc in get_experiments():
		rewards, distances, energies = test_experiment(doc)
		percentage = int(np.sqrt(doc['experiment_tag_index']) / 400 * 100)

		indices.append(percentage)
		# mins.append(min(rewards))
		avgs.append(sum(rewards)/len(rewards))
		avg_distance.append(sum(distances)/len(distances))
		avg_energy.append(sum(energies)/len(energies))
		# maxs.append(max(rewards))
		# print(np.std(rewards))
		stds.append(np.std(rewards))
		stds_distance.append(np.std(distances))
		stds_energy.append(np.std(energies))

	plt.figure()
	plt.errorbar(indices, avgs, yerr=stds, color='blue', label='Average')
	plt.ylim(ymin=0)
	plt.xlabel('standard deviation % of mean')
	plt.ylabel('Reward')
	plt.legend()
	plt.title('Varying spring stiffness standard deviation')

	plt.show()

	plt.figure()
	plt.errorbar(indices, avg_distance, yerr=stds_distance, color='red', label='Average distance')
	plt.ylim(ymin=0)
	plt.xlabel('standard deviation % of mean')
	plt.ylabel('Distance')
	plt.legend()
	plt.title('Varying spring stiffness standard deviation')

	plt.show()

	plt.figure()
	plt.errorbar(indices, avg_energy, yerr=stds_energy, color='green', label='Average energy')
	plt.ylim(ymin=0)
	plt.xlabel('standard deviation % of mean')
	plt.ylabel('Energy')
	plt.legend()
	plt.title('Varying spring stiffness standard deviation')

	plt.show()


def view_results():
	import matplotlib.pyplot as plt
	print('Showing results...')
	client = MongoClient('localhost', 27017)
	db = client['thesis']
	experiments_collection = db['experiments_2']

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

	

	