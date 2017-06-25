import os
import sys
import feedback_cpg as sim
from model_variations import generate_temp_model_file, generate_model_variations
from utils import printProgressBar
import datetime
import generate_model
import multiprocessing
import numpy as np
import random
import glob
import pickle

BASE_MASS = 0.179

def get_best_params(ex):
	best_id = ex['results']['best_id']
	best_simulation = ex['results']['simulations'][best_id]
	params = best_simulation['cpg_params']

	return params

def get_std_dev_percent(ex):
	remark = ex['remarks'][0]
	std_dev = remark.split(' ')[-1]
	std_dev_percent = int(np.ceil(float(std_dev) / BASE_MASS * 100))

	return std_dev_percent

def generate_variations(morphology, test_percentage, num_variations=100):
	mass_std_dev = test_percentage * BASE_MASS/100

	variation_params = {
		'body': {
			'front': {
				
				'mass': {'normal': [0, mass_std_dev**2]},
			},
			'hind': {
				
				'mass': {'normal': [0, mass_std_dev**2]},
			},		
		},
	}

	variation_paths, _ = generate_model_variations(morphology, variation_params, num_variations)
	return variation_paths

def verify_experiment(ex, params=None):
	std_dev_percent = get_std_dev_percent(ex)
	print('Verifying ' + str(std_dev_percent) + '% training noise')

	if params is None:
		params = get_best_params(ex)

	# test_percentages = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
	test_percentages = [22, 24, 26, 28, 30]

	results = {}

	for test_percentage in test_percentages:
		print('Testing on ' + str(test_percentage) + '% test noise')
		successful = []
		fails = []

		variation_paths = generate_variations(ex['default_morphology'], test_percentage)

		test_id = 0
		for path in variation_paths:
			printProgressBar(test_id, 100, prefix = 'Progress:', suffix = 'Complete', length = 50)
			succes, st, d, ec, ah, sh = sim.evaluate(path, False, params, [], False, False)
			if succes and d > 0:
				successful.append((d/10, ec/10))
			else:
				fails.append((d/10, ec/10, st))
			test_id += 1
		printProgressBar(test_id, 100, prefix = 'Progress:', suffix = 'Complete', length = 50)
		print()
		results[test_percentage] = {'successful': successful, 'fails': fails}

	return (std_dev_percent, results)


def verify():
	file_list = glob.glob('mass_noise/experiment_logs/*.pickle')

	results = {}

	for filename in file_list:
		with open(filename, 'rb') as f:
			experiment = pickle.load(f)
			std_dev_percent, res = verify_experiment(experiment)
			results[std_dev_percent] = res

	with open('mass_noise/thick_feet_baseline.pickle', 'rb') as f:
		params = pickle.load(f)

	_, res = verify_experiment(experiment, params=params)
	results[0] = res

	with open('mass_noise/verify_results.pickle', 'wb') as f:
		pickle.dump(results, f)


def plots(abstract=False, presentation=False):
	assert not (abstract and presentation) # Choose one or the other

	with open('mass_noise/verify_results copy.pickle', 'rb') as f:
		results = pickle.load(f)

	percentages, min_speed, avg_speed, max_speed, min_cot, avg_cot, max_cot = [], [], [], [], [], [], []

	plots = {}

	fastest = 0

	for train_percent, verify_results in results.items():
		percentages, avg_speeds, avg_cots = [], [], []

		for key, value in verify_results.items():
			speeds = [x[0] for x in value['successful']]
			speeds.extend([0 for x in value['fails']])

			cots = [x[1]/x[0] for x in value['successful']]

			percentages.append(key)
			avg_speeds.append(np.mean(speeds))
			avg_cots.append(np.mean(cots))

			if np.max(speeds) > fastest:
				fastest = np.max(speeds)

		plots[train_percent] = {'percentages': percentages, 'avg_speeds': avg_speeds, 'avg_cots': avg_cots}

	import matplotlib.pyplot as plt
	import matplotlib as mpl
	if abstract:
		plt.figure(figsize=(7,5))
		plt.switch_backend('TkAgg')
	elif presentation:
		plt.figure(figsize=(4,3))
		mpl.rcParams['axes.color_cycle'] = ['#78B833', '#DD7611', '#16A6C9']
		mpl.rcParams['axes.grid'] = False
	else:
		plt.figure(figsize=(6.5,5))

	for train_percent, plot_data in plots.items():
		percentages = plot_data['percentages']
		avg_speeds = plot_data['avg_speeds']
		avg_cots = plot_data['avg_cots']

		sorted_lists = sorted(zip(percentages, avg_speeds, avg_cots), key=lambda x:x[0])
		percentages, avg_speeds, avg_cots = [[x[i] for x in sorted_lists] for i in range(3)]

	
		plt.plot(percentages, avg_speeds, label=str(train_percent) + '% training')
	
	plt.legend()
	ax = plt.gca()
	ax.yaxis.set_ticks_position('left') # this one is optional but I still recommend it...
	ax.xaxis.set_ticks_position('bottom')
	ax.set_xlim(left=0)
	ax.set_ylim(0, fastest*1.1)

	plt.ylabel('Speed (m/s)')
	plt.xlabel('% test noise')

	if abstract:
		plt.savefig('/Users/Siebe/Dropbox/Thesis/writing/abstract/figures/mass_noise.png', dpi=300)
	elif presentation:
		ax.set_ylim(0, 0.35)
		plt.title('Adding noise on robot mass')
		plt.tight_layout()
		plt.savefig('/Users/Siebe/Dropbox/Thesis/presentation_plots/mass_noise.png', dpi=300)
	else:
		plt.savefig('mass_noise/speed.pgf')

def show():
	with open('mass_noise/verify_results.pickle', 'rb') as f:
		results = pickle.load(f)

	import json
	print(json.dumps(results, sort_keys=True, indent=4))

def extract_params():
	file_list = glob.glob('mass_noise/experiment_logs/*.pickle')

	for filename in file_list:
		with open(filename, 'rb') as f:
			ex = pickle.load(f)
			std_dev_percent = get_std_dev_percent(ex)
			params = get_best_params(ex)

			with open('mass_noise/params/mass_noise_' + str(std_dev_percent) + '.pickle', 'wb') as f2:
				pickle.dump(params, f2, 2)


if __name__ == '__main__':
	if len(sys.argv) < 2:
		print('Please specify verify or plots')

	if sys.argv[1] == 'verify':
		verify()
	elif sys.argv[1] == 'plots':
		plots()
	elif sys.argv[1] == 'abstract':
		plots(abstract=True)
	elif sys.argv[1] == 'presentation':
		plots(presentation=True)
	elif sys.argv[1] == 'show':
		show()
	elif sys.argv[1] == 'params':
		extract_params()


