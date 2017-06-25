import sys
import numpy as np
import matplotlib.pyplot as plt
import glob
import pickle

def get_experiments(simulations=False):
	file_list = glob.glob('experiment_logs/*.pickle')
	experiments = []

	for filename in file_list:
		with open(filename, 'rb') as f:
			experiment = pickle.load(f)
			experiments.append(experiment)

	return experiments

def plot_score_evolution():
	for ex in get_experiments():
		remark = ex['remarks'][0]
		std_dev = remark.split(' ')[-1]
		std_dev_percent = int(np.ceil(float(std_dev)))
		plt.figure(figsize=(6,6))
		plt.plot(ex['results']['avg_score_evolution'], 'b', ex['results']['max_score_evolution'], 'r')
		plt.savefig('score_evolution_' + str(std_dev_percent) + '.pdf')


if __name__ == '__main__':
	plot_score_evolution()	

	

	
