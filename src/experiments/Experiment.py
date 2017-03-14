import feedback_cpg as sim
import generate_model
from pymongo import MongoClient
import datetime
import cma
import multiprocessing
import numpy as np


def eval_wrapper(variables):
	model_file = variables['model_file']
	closed_loop = variables['closed_loop']
	params = variables['params']
	render = variables['render']
	logging = variables['logging']
	return sim.evaluate(model_file, closed_loop, params.tolist(), render, logging)

class Experiment:
	def __init__(self, default_morphology, closed_loop, initial_values, lower_bounds, upper_bounds, variances, max_iters, E0=20):
		self.default_morphology = default_morphology
		self.closed_loop = closed_loop
		self.initial_values = initial_values
		self.lower_bounds = lower_bounds
		self.upper_bounds = upper_bounds
		self.variances = variances
		self.max_iters = max_iters
		self.E0 = E0

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

	def normalize_initial_values(self):
		initial_normalized = [(x-l) / (u-l) for x, l, u in zip(self.initial_values, self.lower_bounds, self.upper_bounds)]
		return initial_normalized

	def denormalize(self, x):
		array = np.array(len(self.initial_values)*[0.0])
		i = 0
		for var in x:
			array[i] = var*(self.upper_bounds[i]-self.lower_bounds[i]) + self.lower_bounds[i]
			i += 1

		return array

	def run_optimization(self, model_file, logging=False):
		es = cma.CMAEvolutionStrategy(self.normalize_initial_values(), self.variances,
			{'boundary_handling': 'BoundTransform ','bounds': [0,1], 'maxiter' : self.max_iters,'verbose' :0})
		
		iteration = 0
		simulation_id = 0
		mp_pool = multiprocessing.Pool(8)

		while not es.stop():
			solutions = es.ask()
			print("New solutions #" + str(iteration))
			x = [{'model_file': model_file, 'closed_loop': self.closed_loop, 'params': self.denormalize(x), 'render': False, 'logging': logging} for x in solutions]
			results = mp_pool.map(eval_wrapper, x)

			rewards = []
			max_reward = 0
			avg_reward = 0
			for result, solution in zip(results, solutions):
				succes, simulated_time, distance, energy_consumed, action_history, sensor_history = result
	
				# reward = 0 if distance < 0 or not succes else 1.447812*9.81*distance/(energy_consumed+20)
				reward = 0 if distance < 0 or not succes else 1.447812*9.81*distance*np.tanh(energy_consumed/self.E0)

				rewards.append(reward*-1) # May need to be a numpy.ndarray
				self.total_simulated_time += simulated_time
				avg_reward += reward
				simulation_dict = {'iter': iteration,
									'cpg_params': self.denormalize(solution).tolist(),
									'simulated_time': simulated_time,
									'distance': distance,
									'energy': energy_consumed,
									'action_history': action_history,
									'sensor_history': sensor_history,
									'reward': reward,
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
			es.disp()

			iteration += 1

		print("Stopping CMA ES")
		res = es.result()

		if iteration < 2: #restart
			self.init_document()
			return self.run_optimization(model_file, logging)
		else:
			# Save results in DB
			client = MongoClient('localhost', 27017)
			db = client['thesis']
			experiments_collection = db['experiments']
			insert_result = experiments_collection.insert_one(self.get_document())
			return insert_result.inserted_id

	def get_document(self):
		doc = {}
		doc['type'] = self.type
		doc['timestamp'] = datetime.datetime.utcnow()
		doc['generate_model_version'] = generate_model.get_model_generator_version()
		doc['cpg_version'] = sim.get_cpg_version()
		doc['E0'] = self.E0
		doc['remarks'] = 'Reward function: 0 if distance < 0 or not succes else 1.447812*9.81*distance*np.tanh(energy_consumed/' + str(self.E0) + ') increased upper bound on omega'
		doc['default_morphology'] = self.default_morphology
		doc['optimization'] = 	{'type': 'CMA',
									 'params': {
									 	'initial_values': self.initial_values,
									 	'lower_bounds': self.lower_bounds,
									 	'upper_bounds': self.upper_bounds,
									 	'variances': self.variances,
									 	'max_iters': self.max_iters
									 }
								}
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
	lb = [0, 0, 0, 0, -1, -4, 0.5, 0.5, 0.2, 0.2, 0, 0, 0, 0, 0, 0, 0]
	ub = [2, 2, 2, 2, 2, 4, 10, 10, 0.7, 0.7, 1, 1, 1, 1, 1, 1, 2*np.pi]

	initial = [1, 1, 1, 1, 0, 0, 2, 2, 0.2, 0.2, 0, 1, 1, 1, 1, 0, np.pi]

	e = Experiment({}, False, initial, lb, ub, 0.5, 400, 7)
	e.run_optimization('/Users/Siebe/Dropbox/Thesis/Scratches/model.xml')

