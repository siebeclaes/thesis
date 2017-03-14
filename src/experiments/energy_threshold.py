from Experiment import Experiment
import numpy as np

lb = [0, 0, 0, 0, -1, -4, 0.5, 0.5, 0.2, 0.2, 0, 0, 0, 0, 0, 0, 0]
ub = [2, 2, 2, 2, 2, 4, 10, 10, 0.7, 0.7, 1, 1, 1, 1, 1, 1, 2*np.pi]

initial = [1, 1, 1, 1, 0, 0, 2, 2, 0.2, 0.2, 0, 1, 1, 1, 1, 0, np.pi]

ids = []

iterations = 250

thresholds = [1,3,5,7,10,13,15,17,20,23,25,28,30,35,40]

for E0 in thresholds:
	e = Experiment({}, False, initial, lb, ub, 0.5, iterations, E0)
	result_id = e.run_optimization('/Users/Siebe/Dropbox/Thesis/Scratches/model.xml')
	ids.append(result_id)

print(ids)