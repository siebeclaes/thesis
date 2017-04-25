import sys
import numpy as np
from pymongo import MongoClient
import matplotlib.pyplot as plt


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

EXPERIMENT_TAG = 'vary_femur_length_1'
NUM_OPTIMIZATION_STEPS = 150
E_0 = 30
NUM_VARIATIONS = 15

def perform_experiment(femur_length_variance):

	print('Experiment "' + EXPERIMENT_TAG + '": ' + str(femur_length_variance))

	from Experiment import Experiment
	variation_params_spring = {'legs': {
			'FL': {
				'femur_length': {'normal': [0, femur_length_variance]},
			},
			'FR': {
				'femur_length': {'normal': [0, femur_length_variance]},
			},
			'BL': {
				'femur_length': {'normal': [0, femur_length_variance]},
			},
			'BR': {
				'femur_length': {'normal': [0, femur_length_variance]},
			},
		},
	}

	lb = [15, 15, 15, 15, -30, -30, 0.5, 0.5, 0.2, 0.2, 0, 0, 0, 0, 0, 0, 0]
	ub = [45, 45, 45, 45, 30, 30, 3, 3, 0.7, 0.7, 1, 1, 1, 1, 1, 1, 2*np.pi]

	initial = [25, 25, 25, 25, 0, 0, 0.6, 0.6, 0.2, 0.2, 0, 1, 1, 1, 1, 0, np.pi]

	e = Experiment(model_config, False, initial, lb, ub, 0.5, NUM_OPTIMIZATION_STEPS, E_0, variation_params=variation_params_spring, num_variations=NUM_VARIATIONS, perturbation_params=None, experiment_tag=EXPERIMENT_TAG, experiment_tag_index=femur_length_variance)
	e.run()

def run():
	variances = [0.1, 0.3, 0.5, 0.7, 1]

	for variance in variances:
		perform_experiment(variance)

def view_results():
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
	axarr[0].plot(indices, mins, color='green', label='Minimum')
	axarr[0].plot(indices, avgs, color='blue', label='Average')
	axarr[0].plot(indices, maxs, color='red', label='Maximum')
	axarr[0].set_xlabel('Femur length standard deviation')
	axarr[0].set_ylabel('Reward')
	axarr[0].legend()

	axarr[1].plot(indices, stds, color='yellow', label='Standard deviation')
	axarr[0].set_xlabel('Femur length standard deviation')
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

	if sys.argv[1] == 'run':
		run()
	elif sys.argv[1] == 'results':
		view_results()

	

	