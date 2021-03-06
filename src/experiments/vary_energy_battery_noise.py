import sys
import numpy as np
from pymongo import MongoClient
import feedback_cpg as sim
from model_variations import generate_temp_model_file, generate_model_variations
import multiprocessing


# MODEL PARAMETERS
model_config = {
	'battery_weight': 0.117,
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

variation_params = {'body': {
		'length': {'normal': [0, 1]},
		'height': {'normal': [0, 0.3]},
		},
		'legs': {
			'FL': {
				'tibia_length': {'normal': [0, 0.5]},
				'spring_stiffness': {'normal': [0, 20]},
			},
			'FR': {
				'tibia_length': 'legs.FL.tibia_length',
				'spring_stiffness': {'normal': [0, 20]},
			},
			'BL': {
				'tibia_length': {'normal': [0, 0.5]},
				'spring_stiffness': {'normal': [0, 20]},
			},
			'BR': {
				'tibia_length': 'legs.BL.tibia_length',
				'spring_stiffness': {'normal': [0, 20]},
			},
		},
		'battery_weight': {'normal': [0, 15]},
	}

EXPERIMENT_TAG = 'battery_noise'
NUM_OPTIMIZATION_STEPS = 300
NUM_VARIATIONS = 15
COLLECTION_NAME = 'battery_noise'

def perform_experiment(E_ref):
	from Experiment import Experiment

	lb = [10, 10, 20, 20, -30, -30, 0.5, 0.1, 0.1, 0, 0, 0]
	ub = [40, 40, 40, 40, 0, 15, 4, 0.9, 0.9, 2*np.pi, 2*np.pi, 2*np.pi]

	initial = [35, 35, 30, 30, -5, 5, 1, 0.4, 0.4, 0, 0, 0]

	e = Experiment(model_config, False, initial, lb, ub, 0.3, NUM_OPTIMIZATION_STEPS, E_ref=E_ref, variation_params=variation_params, num_variations=NUM_VARIATIONS, collection_name=COLLECTION_NAME,  perturbation_params=None, remarks='E_ref = ' + str(E_ref))
	e.run()

def run():
	e_refs = [5, 10, 15]

	for _ in range(5):
		for e_ref in e_refs:
			perform_experiment(e_ref)

def get_experiments():
	client = MongoClient('localhost', 27017)
	db = client['thesis']
	experiments_collection = db[COLLECTION_NAME]

	return experiments_collection.find()

def eval_wrapper(variables):
	model_file = variables['model_file']
	closed_loop = variables['closed_loop']
	params = variables['params']
	perturbations = variables['perturbations']
	render = variables['render']
	logging = variables['logging']
	return sim.evaluate(model_file, closed_loop, params, perturbations, render, logging)


def view_results():
	distance, energy, phase1, phase2, phase3, ed, reward, E_ref = [], [], [], [], [], [], [], []
	best_simulations = []
	for doc in get_experiments():
		E0 = doc.get('E0', None)
		if E0 is None:
			E0 = doc.get('E_ref')
		best_simulation_id = doc['results']['best_id']
		best_simulation = doc['results']['simulations'][best_simulation_id]
		best_simulation['E_ref'] = E0
		best_simulations.append(best_simulation)

	import pickle
	with open('battery_noise.pickle', 'wb') as f:
		pickle.dump(best_simulations, f)

if __name__ == '__main__':
	if len(sys.argv) < 2:
		print('Please specify run or results')

	if sys.argv[1] == 'train':
		run()
	elif sys.argv[1] == 'results':
		view_results()

	

	