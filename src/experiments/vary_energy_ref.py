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

EXPERIMENT_TAG = 'vary_energy_ref_1'
NUM_OPTIMIZATION_STEPS = 250
E_0 = 30
NUM_VARIATIONS = 15

def perform_experiment(E_ref):
	from Experiment import Experiment

	lb = [10, 10, 20, 20, -30, -30, 0.5, 0.1, 0.1, 0, 0, 0]
	ub = [40, 40, 40, 40, 0, 15, 4, 0.9, 0.9, 2*np.pi, 2*np.pi, 2*np.pi]

	initial = [35, 35, 30, 30, -5, 5, 0.6, 0.4, 0.4, 0, 0, 0]

	e = Experiment(model_config, False, initial, lb, ub, 0.5, 300, E0=E_ref, variation_params=None, num_variations=1, perturbation_params=None, remarks='E_ref = ' + str(E_ref))
	e.run()

def run():
	# variances = [40, 60, 80, 100, 120, 140, 160]
	variances = [10, 15, 20, 25, 30, 35, 40, 45]

	for variance in variances:
		for _ in range(5):
			perform_experiment(variance)

def get_experiments():
	client = MongoClient('localhost', 27017)
	db = client['thesis']
	experiments_collection = db['gait_transition']

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

	for doc in get_experiments():
		E0 = doc['E0']
		best_simulation_id = doc['results']['best_id']
		best_simulation = doc['results']['simulations'][best_simulation_id]
		d = best_simulation['distance'][0]
		e = best_simulation['energy'][0]
		r = best_simulation['reward']
		params = best_simulation['cpg_params']
		a = params[9]
		b = params[10]
		c = params[11]
		if e/d < 6:
			E_ref.append(E0 )
			phase1.append(a)
			phase2.append(b)
			phase3.append(c)
			reward.append(r)
			distance.append(d)
			energy.append(e)
			ed.append(e/d)

	# save_scatter(E_ref, ed, 'COT_vs_Eref_outliers_removed', 'Eref', 'COT')
	# save_scatter(ed, phase3, 'HindOffset_vs_COT_outliers_removed', 'COT', 'HindOffset')
	# save_scatter(E_ref, energy, 'Energy_vs_Eref_outliers_removed', 'Eref', 'Energy')
	# save_scatter(E_ref, distance, 'Distance_vs_Eref', 'Eref', 'Distance')
	save_scatter(distance, phase3, 'HindOffset_vs_distance_outliers_removed', 'Distance', 'HindOffset')
	save_scatter(energy, phase3, 'HindOffset_vs_energy_outliers_removed', 'Energy', 'HindOffset')

def save_scatter(x, y, title, xlabel, ylabel):
	import matplotlib.pyplot as plt
	plt.figure()
	plt.scatter(x, y)
	plt.xlabel(xlabel)
	plt.ylabel(ylabel)
	plt.title(title)
	plt.savefig('plots/' + title + '.png')

if __name__ == '__main__':
	if len(sys.argv) < 2:
		print('Please specify run or results')

	if sys.argv[1] == 'train':
		run()
	elif sys.argv[1] == 'results':
		view_results()

	

	