from pymongo import MongoClient
import matplotlib.pyplot as plt
import numpy as np
import pickle
import os

SIMULATION_LENGTH = 10

max_speed, max_power, max_cot = 0, 0, 0

def filter_high_cot(simulations, max_cot):
	return [sim for sim in simulations if sim['energy'][0]/sim['distance'][0] < max_cot]

def get_hind_offset(params):
	a = params[9]
	b = params[10]
	c = params[11]

	return np.abs(b-c)

def is_running_gait(params):
	hind_offset = get_hind_offset(params)

	if hind_offset > 4 or hind_offset < 2:
		return True
	else:
		return False

def hind_offset_vs_eref(simulations):
	plt.switch_backend('tkagg') 
	e_ref, phase3 = [], []

	for simulation in simulations:
		er = simulation['E_ref']
		d = simulation['distance'][0]
		e = simulation['energy'][0]

		params = simulation['cpg_params']
		e_ref.append(er)
		phase3.append(get_hind_offset(params))

	plt.figure()
	plt.scatter(e_ref, phase3, color='blue')
	plt.yticks([0, np.pi, np.pi*2],
           [r'$0$', r'$\pi$', r'$2\pi$'])
	plt.savefig("hind_offset_vs_pref.pdf")

def hind_offset_vs_distance(simulations):
	distance, phase3 = [], []

	for simulation in simulations:
		d = simulation['distance'][0]
		params = simulation['cpg_params']
		distance.append(d)
		phase3.append(get_hind_offset(params))

	plt.figure()
	plt.scatter(distance, phase3, color='blue')
	plt.yticks([0, np.pi, np.pi*2],
           [r'$0$', r'$\pi$', r'$2\pi$'])
	plt.show()

def hind_offset_vs_energy(simulations):
	energy, phase3 = [], []

	for simulation in simulations:
		e = simulation['energy'][0]
		params = simulation['cpg_params']
		energy.append(e)
		phase3.append(get_hind_offset(params))

	plt.figure()
	plt.scatter(energy, phase3, color='blue')
	plt.yticks([0, np.pi, np.pi*2],
           [r'$0$', r'$\pi$', r'$2\pi$'])
	plt.show()

def hind_offset_vs_cot(simulations):
	cots, offsets = [], []

	for simulation in simulations:
		e = simulation['energy'][0]
		d = simulation['distance'][0]
		cot = e/d
		params = simulation['cpg_params']
		cots.append(cot)
		offsets.append(get_hind_offset(params))

	plt.figure()
	plt.scatter(cots, offsets, color='blue')
	plt.yticks([0, np.pi, np.pi*2],
           [r'$0$', r'$\pi$', r'$2\pi$'])
	plt.show()

def speed_vs_cot(simulations, folder):
	global max_speed, max_cot

	cots_walking, distances_walking = [], []
	cots_running, distances_running = [], []

	max_speed = 0
	max_speed_er = 0

	for simulation in simulations:
		er = simulation['E_ref']
		e = simulation['energy'][0]
		d = simulation['distance'][0]

		speed = d / SIMULATION_LENGTH # m/s
		power = e / SIMULATION_LENGTH

		if speed > max_speed:
			max_speed = speed
			max_speed_er = er

		params = simulation['cpg_params']
		
		if is_running_gait(params):
			cots_running.append(power/speed)
			distances_running.append(speed)
		else:
			cots_walking.append(power/speed)
			distances_walking.append(speed)

	print(max_speed)
	print(max_speed_er)

	plt.figure(figsize=(6.5,5))
	plt.scatter(cots_walking, distances_walking, color='#5DA5DA', label='Walking gait')
	plt.scatter(cots_running, distances_running, color='#F15854', label='Running gait')
	plt.ylabel('Speed (m/s)')
	plt.xlabel('Cost of transportation (speed / power)')

	ax = plt.gca()
	ax.yaxis.set_ticks_position('left') # this one is optional but I still recommend it...
	ax.xaxis.set_ticks_position('bottom')
	ax.set_xlim(0, max_cot * 1.1)
	ax.set_ylim(0, max_speed * 1.1)

	plt.legend()

	plt.savefig(os.path.join(folder, "speed_vs_cot.pdf"))
	# plt.savefig("/Users/Siebe/Dropbox/Thesis/writing/figures/speed_vs_cot.pgf")

def speed_vs_power(simulations, folder):
	global max_speed, max_power

	energies_walking, distances_walking = [], []
	energies_running, distances_running = [], []

	for simulation in simulations:
		er = simulation['E_ref']
		e = simulation['energy'][0]
		d = simulation['distance'][0]

		speed = d / SIMULATION_LENGTH # m/s
		power = e / SIMULATION_LENGTH

		params = simulation['cpg_params']
		
		if is_running_gait(params):
			energies_running.append(power)
			distances_running.append(speed)
		else:
			energies_walking.append(power)
			distances_walking.append(speed)

	plt.figure(figsize=(6.5,5))
	plt.scatter(energies_walking, distances_walking, color='#5DA5DA', label='Walking gait')
	plt.scatter(energies_running, distances_running, color='#F15854', label='Running gait')
	plt.ylabel('Speed (m/s)')
	plt.xlabel('Power')

	ax = plt.gca()
	ax.yaxis.set_ticks_position('left') # this one is optional but I still recommend it...
	ax.xaxis.set_ticks_position('bottom')
	ax.set_xlim(0, max_power*1.1)
	ax.set_ylim(0, max_speed*1.1)

	plt.legend()

	plt.savefig(os.path.join(folder, "speed_vs_power.pdf"))
	# plt.savefig("/Users/Siebe/Dropbox/Thesis/writing/figures/speed_vs_cot.pgf")
	# plt.show()

def cot_vs_pref(simulations, folder):
	global max_cot

	p_refs = {}
	p_refs_walking, cots_walking = [], []
	p_refs_running, cots_running = [], []

	for simulation in simulations:
		pr = simulation['E_ref'] / SIMULATION_LENGTH
		e = simulation['energy'][0]
		d = simulation['distance'][0]
		params = simulation['cpg_params']

		cot = e/d # Cost of transportation

		cots = p_refs.get(pr, [])
		cots.append(cot)
		p_refs[pr] = cots

		if is_running_gait(params):
			p_refs_running.append(pr)
			cots_running.append(cot)
		else:
			p_refs_walking.append(pr)
			cots_walking.append(cot)

	W, Z = [], []

	for p_ref in p_refs.keys():
		cots = p_refs[p_ref]
		W.append(p_ref)
		Z.append(np.mean(cots))

	sorted_lists = sorted(zip(W, Z), key=lambda x:x[0])
	W, Z = [[x[i] for x in sorted_lists] for i in range(2)]

	# plt.figure()
	plt.scatter(p_refs_walking, cots_walking, color='#5DA5DA', label='Walking gait')
	plt.scatter(p_refs_running, cots_running, color='#F15854', label='Running gait')
	plt.xlabel('Reference power P_ref')
	plt.ylabel('Cost of transportation (speed / power)')

	ax = plt.gca()
	ax.yaxis.set_ticks_position('left') # this one is optional but I still recommend it...
	ax.xaxis.set_ticks_position('bottom')
	ax.set_xlim(left=0)
	ax.set_ylim(0, max_cot*1.1)

	plt.plot(W, Z)

	plt.legend()

	# plt.savefig(os.path.join(folder, "cot_vs_pref.pdf"))

def speed_vs_pref(simulations, folder):
	global max_speed

	p_refs = {}
	p_refs_walking, distances_walking = [], []
	p_refs_running, distances_running = [], []

	for simulation in simulations:
		pr = simulation['E_ref'] / SIMULATION_LENGTH
		e = simulation['energy'][0]
		d = simulation['distance'][0]
		params = simulation['cpg_params']

		speed = d / SIMULATION_LENGTH

		speeds = p_refs.get(pr, [])
		speeds.append(speed)
		p_refs[pr] = speeds

		if is_running_gait(params):
			p_refs_running.append(pr)
			distances_running.append(speed)
		else:
			p_refs_walking.append(pr)
			distances_walking.append(speed)

	W, Z = [], []

	for p_ref in p_refs.keys():
		speeds = p_refs[p_ref]
		W.append(p_ref)
		Z.append(np.mean(speeds))

	sorted_lists = sorted(zip(W, Z), key=lambda x:x[0])
	W, Z = [[x[i] for x in sorted_lists] for i in range(2)]

	plt.figure()
	plt.scatter(p_refs_walking, distances_walking, color='#5DA5DA', label='Walking gait')
	plt.scatter(p_refs_running, distances_running, color='#F15854', label='Running gait')
	plt.xlabel('Reference power P_ref')
	plt.ylabel('Speed (m/s)')

	ax = plt.gca()
	ax.yaxis.set_ticks_position('left') # this one is optional but I still recommend it...
	ax.xaxis.set_ticks_position('bottom')
	ax.set_xlim(left=0)
	ax.set_ylim(0, max_speed*1.1)

	plt.plot(W, Z)

	plt.legend()

	plt.savefig(os.path.join(folder, 'speed_vs_pref.pdf'))

def power_vs_pref(simulations, folder):
	global max_power

	p_refs = {}
	p_refs_walking, powers_walking = [], []
	p_refs_running, powers_running = [], []

	for simulation in simulations:
		pr = simulation['E_ref'] / SIMULATION_LENGTH
		e = simulation['energy'][0]
		d = simulation['distance'][0]
		params = simulation['cpg_params']

		power = e / SIMULATION_LENGTH

		powers = p_refs.get(pr, [])
		powers.append(power)
		p_refs[pr] = powers

		if is_running_gait(params):
			p_refs_running.append(pr)
			powers_running.append(power)
		else:
			p_refs_walking.append(pr)
			powers_walking.append(power)

	W, Z = [], []

	for p_ref in p_refs.keys():
		powers = p_refs[p_ref]
		W.append(p_ref)
		Z.append(np.mean(powers))

	sorted_lists = sorted(zip(W, Z), key=lambda x:x[0])
	W, Z = [[x[i] for x in sorted_lists] for i in range(2)]

	plt.figure()
	plt.scatter(p_refs_walking, powers_walking, color='#5DA5DA', label='Walking gait')
	plt.scatter(p_refs_running, powers_running, color='#F15854', label='Running gait')
	plt.xlabel('Reference power P_ref')
	plt.ylabel('Power (W)')

	ax = plt.gca()
	ax.yaxis.set_ticks_position('left') # this one is optional but I still recommend it...
	ax.xaxis.set_ticks_position('bottom')
	ax.set_xlim(left=0)
	ax.set_ylim(0, max_power*1.1)

	plt.plot(W, Z)

	plt.legend()

	plt.savefig(os.path.join(folder, 'power_vs_pref.pdf'))

def get_axis_limits(folders):
	global max_speed, max_power, max_cot

	for folder in folders:
		simulation_file = os.path.join(folder, 'simulations.pickle')
		with open(simulation_file, 'rb') as f:
			simulations = pickle.load(f)

			for simulation in simulations:
				er = simulation['E_ref']
				e = simulation['energy'][0]
				d = simulation['distance'][0]

				speed = d / SIMULATION_LENGTH # m/s
				power = e / SIMULATION_LENGTH
				cot = e / d

				if speed > max_speed:
					max_speed = speed

				if power > max_power:
					max_power = power

				if cot > max_cot:
					max_cot = cot

	print(max_speed)
	print(max_power)
	print(max_cot)

def main():
	folders = ['correct_inertia', 'correct_uniform', 'correct_uniform_battery', 'heavy']
	# folders = ['correct_inertia']
	get_axis_limits(folders)

	subplots = (221, 222, 223, 224)
	plt.figure()
	for folder, sp in zip(folders, subplots):
		plt.subplot(sp)
		simulation_file = os.path.join(folder, 'simulations.pickle')
		with open(simulation_file, 'rb') as f:
			simulations = pickle.load(f)
			# cot_vs_pref(simulations, folder)
			# speed_vs_pref(simulations, folder)
			# power_vs_pref(simulations, folder)
			# speed_vs_cot(simulations, folder)
			# speed_vs_power(simulations, folder)

	plt.savefig('speed_vs_power_combined.pdf')

if __name__ == '__main__':
	main()
