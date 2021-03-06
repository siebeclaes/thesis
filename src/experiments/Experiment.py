import os
import feedback_cpg as sim
from model_variations import generate_temp_model_file, generate_model_variations
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from utils import printProgressBar
import datetime
import generate_model
import cma
import multiprocessing
import numpy as np
import random


def eval_wrapper(variables):
	model_files = variables['model_files']
	closed_loop = variables['closed_loop']
	params = variables['params']
	perturbations = variables['perturbations']
	render = variables['render']
	logging = variables['logging']
	# print(model_files)
	results = []
	for model_file in model_files:
		r = sim.evaluate(model_file, closed_loop, params.tolist(), perturbations, render, logging)
		results.append(r)
	# print(results)
	print("I'm done")
	return results

class Experiment:
	def __init__(self, default_morphology, closed_loop, initial_values, lower_bounds, upper_bounds, variances, max_iters, E_ref=20, perturbation_params=None, variation_params=None, num_variations=0, collection_name='experiments_2', save_in_database=False, experiment_tag=None, experiment_tag_index=0, remarks='', popsize=30):
		self.default_morphology = default_morphology
		self.closed_loop = closed_loop
		self.initial_values = initial_values
		self.lower_bounds = lower_bounds
		self.upper_bounds = upper_bounds
		self.variances = variances
		self.max_iters = max_iters
		self.E_ref = E_ref
		self.perturbation_params = perturbation_params
		self.variation_params = variation_params
		self.num_variations = num_variations
		self.variation_delta_dicts = []
		self.experiment_tag = experiment_tag
		self.experiment_tag_index = experiment_tag_index
		self.remarks = remarks
		self.collection_name = collection_name
		self.save_in_database = save_in_database
		self.popsize = popsize

		self.type = "closed" if self.closed_loop else "open"

		self.init_document()

	def init_document(self):
		self.simulations = []
		self.avg_score_evolution = []
		self.max_score_evolution = []
		self.total_simulated_time = 0
		self.total_computation_time = 0
		self.best_id = 0
		self.best_reward = 0

	def setup_model_variations(self):
		self.model_files = []
		if not self.variation_params:
			self.model_files.append(generate_temp_model_file(self.default_morphology))
		else:
			variation_xml_paths, delta_dicts = generate_model_variations(self.default_morphology, self.variation_params, self.num_variations)
			self.model_files.extend(variation_xml_paths)
			self.variation_delta_dicts = delta_dicts

	def run(self):
		self.setup_model_variations()
		self.run_optimization(logging=False)


	def normalize_initial_values(self):
		initial_normalized = [(x-l) / (u-l) for x, l, u in zip(self.initial_values, self.lower_bounds, self.upper_bounds)]
		return initial_normalized

	def denormalize(self, x):
		array = np.array(len(self.initial_values)*[0.0])
		i = 0
		for var in x:
			array[i] = var*(self.upper_bounds[i]-self.lower_bounds[i]) + self.lower_bounds[i]
			i += 1

		params = np.array(12*[0.0])
		if len(array) == 8:
			# Mapping B
			# Bound gait, so only 1 phase offset parameter and amplitudes are the same for both front and both hind legs
			# The amplitudes are derived from the bounds on the swing
			params[0] = (array[0] - array[2])/2
			params[1] = (array[0] - array[2])/2
			params[2] = (array[1] - array[3])/2
			params[3] = (array[1] - array[3])/2

			params[4] = array[0] - params[0]	
			params[5] = array[1] - params[2]	

			# Amplitudes for CPG should be squared
			params[0] = params[0] * params[0] 
			params[1] = params[1] * params[1]
			params[2] = params[2] * params[2]
			params[3] = params[3] * params[3]

			# frequency times 2 pi
			params[6] = array[4] * 2 * np.pi

			params[7] = array[5]
			params[8] = array[6]

			# Ony 1 phase offset parameter gets optimized
			# this parameter is the offset between the front and hind legs
			# Convert this offset to the 3 offsets needed to generate the CPG signals
			front_hind_offset = array[7]
			params[9] = 0 # Offset FR to FL is 0 in bound gait
			params[10] = front_hind_offset
			params[11] = front_hind_offset

		elif len(array) == 12:
			# Do not impose bound gait: Mapping A
			params[0] = array[0] - array[4]
			params[1] = array[1] - array[4]
			params[2] = array[2] - array[5]
			params[3] = array[3] - array[5]

			# Amplitudes for CPG should be squared
			params[0] = params[0] * params[0] 
			params[1] = params[1] * params[1]
			params[2] = params[2] * params[2]
			params[3] = params[3] * params[3]

			# Copy offsets
			params[4] = array[4]
			params[5] = array[5]

			# frequency times 2 pi
			params[6] = array[6] * 2 * np.pi

			# Copy duty factors
			params[7] = array[7]
			params[8] = array[8]

			# Copy three phase offsets
			params[9] = array[9]
			params[10] = array[10]
			params[11] = array[11]


		return params

	def sample_variations(self, num):
		model_files = []
		variation_delta_dicts = []
		if not self.variation_params:
			model_files.append(generate_temp_model_file(self.default_morphology))
		else:
			variation_xml_paths, delta_dicts = generate_model_variations(self.default_morphology, self.variation_params, num)
			model_files.extend(variation_xml_paths)
			variation_delta_dicts = delta_dicts

		return (model_files, variation_delta_dicts)

	def run_optimization(self, logging=False):
		es = cma.CMAEvolutionStrategy(self.normalize_initial_values(), self.variances,
			{'popsize': self.popsize, 'boundary_handling': 'BoundTransform ','bounds': [0,1], 'maxiter' : self.max_iters,'verbose' :-1})
		# print('Population size: ' + str(es.popsize))
		self.seed = es.opts['seed']

		iteration = 0
		simulation_id = 0
		mp_pool = multiprocessing.Pool(8)

		if self.perturbation_params:
			perturb_cov = np.diag(self.perturbation_params['perturb_variances'])

		while not es.stop():
			solutions = es.ask()

			solution_variations = [self.sample_variations(self.num_variations) for _ in range(len(solutions))]

			# variation_indices = [int(random.uniform(0, len(self.model_files))) for _ in range(len(solutions))]
			# model_files = [self.model_files[i] for i in variation_indices]
			
			if self.perturbation_params:
				solution_perturbations = []
				for _ in range(len(solutions)):
					occurences = np.random.geometric(p=1/self.perturbation_params['expected_occurences']) - 1 # numpy uses shifted geometric
					perturbations = []
					for i in range(occurences):
						perturb_time = np.random.random() * 14
						force_torque = np.random.multivariate_normal(self.perturbation_params['perturb_means'], perturb_cov)
						perturbations.append([perturb_time, list(force_torque)])
					solution_perturbations.append(perturbations)
			else:
				solution_perturbations = [[]]*len(solutions)

			# print("New solutions #" + str(iteration))
			printProgressBar(iteration, self.max_iters-1, prefix = 'Progress:', suffix = 'Complete', length = 50)

			x = [{
				'model_files': variations[0],
				'closed_loop': self.closed_loop,
				'params': self.denormalize(x),
				'render': False,
				'logging': logging,
				'perturbations': p} for x, variations, p in zip(solutions, solution_variations, solution_perturbations)]
			results = mp_pool.map(eval_wrapper, x)

			# Clean temp files
			for var in solution_variations:
				for f in var[0]:
					os.remove(f)

			rewards = []
			max_reward = 0
			avg_reward = 0
			for result, solution, variations, perturbation in zip(results, solutions, solution_variations, solution_perturbations):
				solution_rewards = []

				simulated_time, distance, energy_consumed, action_history, sensor_history = [], [], [], [], []

				for r in result:
					succes, st, d, ec, ah, sh = r
					simulated_time.append(st)
					distance.append(d)
					energy_consumed.append(ec)
					action_history.append(ah)
					sensor_history.append(sh)
					self.total_simulated_time += st
					reward = 0 if d < 0 or not succes else (d * np.tanh(self.E_ref/ec))
					solution_rewards.append(reward)

				reward = sum(solution_rewards) / len(solution_rewards)

				rewards.append(reward*-1) # May need to be a numpy.ndarray

				# variations_delta_dicts = [v[1] for v in variations]
				
				avg_reward += reward
				simulation_dict = {'iter': iteration,
									'cpg_params': self.denormalize(solution).tolist(),
									'simulated_time': simulated_time,
									'distance': distance,
									'energy': energy_consumed,
									'action_history': action_history,
									'sensor_history': sensor_history,
									'reward': reward,
									# 'variation_index': variation_index,
									'perturbation': perturbation,
									# 'variations': variations_delta_dicts,
								}
				self.simulations.append(simulation_dict)

				# update self.best_id
				if reward > self.best_reward:
					self.best_id = simulation_id
					self.best_reward = reward

				if reward > max_reward:
					max_reward = reward

				simulation_id += 1

			avg_reward /= len(solutions)
			self.avg_score_evolution.append(avg_reward)
			self.max_score_evolution.append(max_reward)

			es.tell(solutions, rewards)
			# es.disp()

			iteration += 1

		print("Stopping CMA ES")
		res = es.result()

		if iteration < 2: #restart
			mp_pool.terminate()
			self.init_document()
			return self.run_optimization(logging)
		else:
			document = self.get_document()
			if self.save_in_database:
				self.save_in_db(document)
				self.save_es_object_to_file(es)
			else:
				self.save_to_file(document)
				self.save_es_object_to_file(es)

	def save_in_db(self, document):
		try:
			# Save results in DB
			client = MongoClient('localhost', 27017)
			db = client['thesis']
			experiments_collection = db[self.collection_name]
			insert_result = experiments_collection.insert_one(document)
			return insert_result.inserted_id
		except ServerSelectionTimeoutError:
			self.save_to_file(document)

	def save_to_file(self, document):
		import pickle
		import time
		timestr = time.strftime("%Y%m%d-%H%M%S")

		with open('experiment_logs/' + self.collection_name + '-' + timestr + '.pickle', 'wb') as f:
			pickle.dump(document, f)

	def save_es_object_to_file(self, es):
		import pickle
		import time
		timestr = time.strftime("%Y%m%d-%H%M%S")

		with open('experiment_logs/' + self.collection_name + '-es' + '-' + timestr + '.pickle', 'wb') as f:
			pickle.dump(es, f)

	def get_document(self):
		doc = {}
		doc['type'] = self.type
		doc['timestamp'] = datetime.datetime.utcnow()
		doc['generate_model_version'] = generate_model.get_model_generator_version()
		doc['cpg_version'] = sim.get_cpg_version()
		doc['E_ref'] = self.E_ref
		doc['experiment_tag'] = self.experiment_tag
		doc['experiment_tag_index'] = self.experiment_tag_index
		doc['remarks'] = self.remarks,
		doc['default_morphology'] = self.default_morphology
		doc['optimization'] = 	{'type': 'CMA',
									 'params': {
									 	'initial_values': self.initial_values,
									 	'lower_bounds': self.lower_bounds,
									 	'upper_bounds': self.upper_bounds,
									 	'variances': self.variances,
									 	'max_iters': self.max_iters,
									 	'seed': self.seed,
									 }
								}
		doc['delta_dicts'] = self.variation_delta_dicts
		doc['perturbation_params'] = self.perturbation_params
		doc['variation_params'] = self.variation_params
		doc['results'] = {
						'best_id': self.best_id,
						'total_simulated_time': self.total_simulated_time,
						'total_computation_time': self.total_computation_time,
						'avg_score_evolution': self.avg_score_evolution,
						'max_score_evolution': self.max_score_evolution,
						'simulations': self.simulations,
		}

		return doc


if __name__ == '__main__':
	# lb = [0, 0, 0, 0, -1, -4, 0.5, 0.5, 0.2, 0.2, 0, 0, 0, 0, 0, 0, 0]
	# ub = [2, 2, 2, 2, 2, 4, 10, 10, 0.7, 0.7, 1, 1, 1, 1, 1, 1, 2*np.pi]

	# initial = [1, 1, 1, 1, 0, 0, 2, 2, 0.2, 0.2, 0, 1, 1, 1, 1, 0, np.pi]
	
	# mu is target amplitude raised to power 2
	# omega frequency should be multiplied by 2*pi

	# MODEL PARAMETERS
	model_config = {
		'body': {
		'front': {
			'width': 14,
			'height': 3,
			'length': 8,
			'mass': 0.179,
		},
		'middle': {
			'width': 5,
			'height': 0.25,
			'length': 8,
			'mass': 0.030,
		},
		'hind': {
			'width': 9,
			'height': 2.5,
			'length': 6,
			'mass': 0.179,
		},		
	},
	'battery_weight': 0.117,
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

	variation_params = {'legs': {
			'FL': {
				'tibia_length': {'normal': [0, 0.2]},
			},
			'FR': {
				'tibia_length': {'normal': [0, 0.2]},
			},
			'BL': {
				'tibia_length': {'normal': [0, 0.2]},
			},
			'BR': {
				'tibia_length': {'normal': [0, 0.2]},
			},
		},
	}

	variation_params_spring = {'legs': {
			'FL': {
				'spring_stiffness': {'normal': [0, 20]},
			},
			'FR': {
				'spring_stiffness': {'normal': [0, 20]},
			},
			'BL': {
				'spring_stiffness': {'normal': [0, 20]},
			},
			'BR': {
				'spring_stiffness': {'normal': [0, 20]},
			},
		},
	}

	perturb_params = {'expected_occurences': 3, 'perturb_means': [100]*6, 'perturb_variances': [50]*6}

	lb = [30, 30, 0, 0, -30, -40, 0.5, 0.1, 0.1, 0, 0, 0]
	ub = [60, 60, 20, 20, 30, 0, 5, 0.9, 0.9, 2*np.pi, 2*np.pi, 2*np.pi]

	initial = [35, 35, 10, 10, 0, -20, 0.6, 0.4, 0.4, 0, 0, 0]

	remark = 'tanh reward function E_ref = 50 max swing hind legs +20 degrees'

	e = Experiment(model_config, False, initial, lb, ub, 0.5, 300, E0=50, variation_params=None, num_variations=1, perturbation_params=None, remarks=remark)
	e.run()

