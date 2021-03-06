import operator
from generate_model import generate_xml_model
import tempfile
import numpy as np
import os

def dict_elementwise_operator(left, right, operator=operator.add):
	combined = {}
	for leftkey, leftvalue in left.items():
		if leftkey in right:
			# Perform elementwise operation
			if isinstance(leftvalue, dict):
				assert(isinstance(right[leftkey], dict))
				combined[leftkey] = dict_elementwise_operator(leftvalue, right[leftkey], operator)
			elif isinstance(leftvalue, str):
				assert(isinstance(right[leftkey], str))
				combined[leftkey] = leftvalue
			else:
				combined[leftkey] = operator(leftvalue, right[leftkey])
		else:
			# key from left dict not found in right, copy left key/value into result
			combined[leftkey] = leftvalue

	return combined


def extract_sample_variables(d, top_path=''):
	path = []
	mean = []
	var = []
	bindings = {}

	for key, value in d.items():
		current_path = top_path + '.' + key if top_path != '' else key
		if key == 'normal':
			path.append(top_path)
			mean.append(value[0])
			var.append(value[1])
		elif isinstance(value, dict):
			p, m, v, b = extract_sample_variables(value, current_path)
			path.extend(p)
			mean.extend(m)
			var.extend(v)
			for target_path, bound_paths in b.items():
				z = bindings.get(target_path, [])
				z.extend(bound_paths)
				bindings[target_path] = z
		elif isinstance(value, str):
			bound_paths = bindings.get(value, [])
			bound_paths.append(current_path)
			bindings[value] = bound_paths

	return (path, mean, var, bindings)


def insert_in_dict(d, path, value):
	p = path.split('.')
	current_d = d
	counter = 1
	for level in p:
		if not level in current_d:
			if counter == len(p):
				current_d[level] = value
				return
			else:
				current_d[level] = {}
		
		current_d = current_d[level]
		counter += 1


def sample_multivariate_from_dict(d, num_samples=1):
	sample_paths, sample_mean, sample_var, bindings = extract_sample_variables(d)
	cov = np.diag(sample_var)
	samples = np.random.multivariate_normal(sample_mean, cov, num_samples)

	delta_dicts = []

	for sample in samples:
		delta_dict = {}
		delta_dicts.append(delta_dict)
		for path, delta in zip(sample_paths, sample):
			insert_in_dict(delta_dict, path, delta)
			if path in bindings:
				# Apply delta also to the bound paths
				for bound_path in bindings[path]:
					insert_in_dict(delta_dict, bound_path, delta)

	return delta_dicts


def generate_temp_model_file(config):
	fd, xml_path = tempfile.mkstemp(suffix='.xml', prefix='model')
	generate_xml_model(xml_path, config)

	# This is necessary to avoid leaking the file descriptor
	# Removing this line leads to an `OSError: [Errno 24] Too many open files:`
	# See: https://www.logilab.org/blogentry/17873
	os.close(fd)

	return xml_path


def generate_model_variations(base_config, variation_params, num=1):
	"""Generate model variations based on a base config dictionary
	and a dictionary of the variation parameters. These parameters
	specify the mean and variance of the normal distribution used to
	sample the new model config.

	returns a tuple: (variation_xml_paths, delta_dicts)
	
	"""

	variation_xml_paths = []
	delta_dicts = sample_multivariate_from_dict(variation_params, num_samples=num)

	for delta in delta_dicts:
		config = dict_elementwise_operator(base_config, delta, operator=operator.add)
		variation_xml_paths.append(generate_temp_model_file(config))

	return (variation_xml_paths, delta_dicts)

