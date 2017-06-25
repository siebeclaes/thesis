import sys
import numpy as np
import matplotlib.pyplot as plt
import glob
import pickle


EXPERIMENT_TAG = 'mass_noise_inertia_new'
NUM_OPTIMIZATION_STEPS = 300
POPSIZE = 80
NUM_VARIATIONS = 10
COLLECTION_NAME = 'mass_noise_inertia_new'

def get_experiments(simulations=False):
	file_list = glob.glob('experiment_logs/*.pickle')
	experiments = []

	for filename in file_list:
		with open(filename, 'rb') as f:
			experiment = pickle.load(f)
			experiments.append(experiment)

	return experiments

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
	with open('spring_noise.pickle', 'wb') as f:
		pickle.dump(best_simulations, f)

def plot_score_evolution():
	for ex in get_experiments():
		remark = ex['remarks'][0]
		std_dev = remark.split(' ')[-1]
		std_dev_percent = int(np.ceil(float(std_dev) / 0.179 * 100))
		plt.figure(figsize=(6,6))
		plt.plot(ex['results']['avg_score_evolution'], 'b', ex['results']['max_score_evolution'], 'r')
		plt.savefig('score_evolution_' + str(std_dev_percent) + '.pdf')


if __name__ == '__main__':
	plot_score_evolution()	

	

	
