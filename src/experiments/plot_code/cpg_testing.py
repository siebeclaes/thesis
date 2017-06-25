#
# This script is used to evaluate the influence of the timestep
# on the integration of the CPG signals using Euler's method
# and RK4.
#

import numpy as np
import matplotlib.pyplot as plt
import time
import os

def get_cpg_values(mu, offset, omega, d, num_samples=1000):
	r = 1
	phi = np.pi*d
	o = offset
	gamma = 5
	dt = 0.0001

	samples = []

	for _ in range(num_samples):
		for iteration in range(int(0.001/dt)):
			d_r = gamma * (mu - r*r)*r
			d_phi = omega
			d_o = 0

			r += dt * d_r
			phi += dt * d_phi
			o += dt * d_o

		two_pi = 2 * 3.141592654

		phi_L = 0
		phi_2pi = phi % two_pi
		if phi_2pi < (two_pi * d):
			phi_L = phi_2pi / (2 * d)
		else:
			phi_L = (phi_2pi + two_pi * (1 - 2 * d)) / (2 * (1 - d))

		action = r * np.cos(phi_L) + o
		samples.append(action)

	return samples

def get_cpg_values_phase(mu, offset, omega, d, phase_offset, num_samples=1000):
	r = [1, 1]
	phi = [np.pi*d] * 2
	o = [offset] * 2
	gamma = 5
	dt = 0.0001

	coupling = [[0,5], [5,0]]
	psi = [[0, phase_offset], [-1*phase_offset, 0]]

	samples = [[], []]

	for _ in range(num_samples):
		for i in range(2):
			for iteration in range(int(0.001/dt)):
				d_r = gamma * (mu - r[i]*r[i])*r[i]
				d_phi = omega
				d_o = 0

				# Phase coupling
				for j in range(2):
					d_phi += coupling[i][j] * np.sin(phi[j] - phi[i] - psi[i][j]);

				r[i] += dt * d_r
				phi[i] += dt * d_phi
				o[i] += dt * d_o

			two_pi = 2 * 3.141592654

			phi_L = 0
			phi_2pi = phi[i] % two_pi
			if phi_2pi < (two_pi * d):
				phi_L = phi_2pi / (2 * d)
			else:
				phi_L = (phi_2pi + two_pi * (1 - 2 * d)) / (2 * (1 - d))

			action = r[i] * np.cos(phi_L) + o[i]
			samples[i].append(action)

	return (samples[0], samples[1])

def rk4(f, x, y, dt, gamma, mu, omega):
    k1 = dt * f(x, y, gamma, mu, omega)
    k2 = dt * f(x + 0.5 * dt, y + 0.5 * k1, gamma, mu, omega)
    k3 = dt * f(x + 0.5 * dt, y + 0.5 * k2, gamma, mu, omega)
    k4 = dt * f(x + dt, y + k3, gamma, mu, omega)
    y = y + (k1 + k2 + k2 + k3 + k3 + k4) / 6
    return y

def dr(t, y, gamma, mu, omega):
	return gamma * (mu - y*y)*y

def dphi(t, y, gamma, mu, omega):
	return omega

def get_cpg_values_rk4(mu, offset, omega, d, phase_offsets, num_samples=1000, dt=0.001):
	r = [1]*4
	phi = [np.pi*d[0], np.pi*d[1], np.pi*d[2], np.pi*d[3]]
	o = offset
	gamma = 0.1

	coupling = [[0,1,1,1], [1,0,1,1], [1,1,0,1], [1,1,1,0]]
	a = phase_offsets[0]
	b = phase_offsets[1]
	c = phase_offsets[2]
	de = a-b
	e = a-c
	f = b-c

	psi = [[0, a, b, c], [-1*a, 0, de, e], [-1*b, -1*de, 0, f], [-1*c, -1*e, -1*f, 0]]

	samples = [[], [], [], []]

	for time_sample in range(num_samples):
		for i in range(4):
			# for iteration in range(int(0.001/dt)):
			
			d_phi = omega[i]
			d_o = 0

			# Phase coupling
			for j in range(4):
				d_phi += coupling[i][j] * np.sin(phi[j] - phi[i] - psi[i][j]);

			r[i] = rk4(dr, time_sample*dt, r[i], dt, gamma, mu[i], omega[i])
			phi[i] += dt * d_phi
			o[i] += dt * d_o

			two_pi = 2 * 3.141592654

			phi_L = 0
			phi_2pi = phi[i] % two_pi
			if phi_2pi < (two_pi * d[i]):
				phi_L = phi_2pi / (2 * d[i])
			else:
				phi_L = (phi_2pi + two_pi * (1 - 2 * d[i])) / (2 * (1 - d[i]))

			action = r[i] * np.cos(phi_L) + o[i]
			samples[i].append(action)

	return (samples[0], samples[1], samples[2], samples[3])

def get_cpg_values_warning(mu, offset, omega, d, phase_offsets, num_samples=1000, dt=0.001):
	r = [1]*4
	phi = [np.pi*d[0], np.pi*d[1], np.pi*d[2], np.pi*d[3]]
	o = offset
	gamma = 0.1

	coupling = [[0,1,1,1], [1,0,1,1], [1,1,0,1], [1,1,1,0]]
	a = phase_offsets[0]
	b = phase_offsets[1]
	c = phase_offsets[2]
	de = a-b
	e = a-c
	f = b-c

	psi = [[0, a, b, c], [-1*a, 0, de, e], [-1*b, -1*de, 0, f], [-1*c, -1*e, -1*f, 0]]

	samples = [[], [], [], []]

	for _ in range(num_samples):
		for i in range(4):
			for iteration in range(int(0.001/dt)):
				d_r = gamma * (mu[i] - r[i]*r[i])*r[i]
				d_phi = omega[i]
				d_o = 0

				# Phase coupling
				for j in range(4):
					d_phi += coupling[i][j] * np.sin(phi[j] - phi[i] - psi[i][j]);

				r[i] += dt * d_r
				phi[i] += dt * d_phi
				o[i] += dt * d_o

			two_pi = 2 * 3.141592654

			phi_L = 0
			phi_2pi = phi[i] % two_pi
			if phi_2pi < (two_pi * d[i]):
				phi_L = phi_2pi / (2 * d[i])
			else:
				phi_L = (phi_2pi + two_pi * (1 - 2 * d[i])) / (2 * (1 - d[i]))

			action = r[i] * np.cos(phi_L) + o[i]
			samples[i].append(action)

	return (samples[0], samples[1], samples[2], samples[3])

def main():
	times = np.arange(0, 1, 0.001)
	cpg_values_1 = np.array(get_cpg_values(1, 0, 2*2*np.pi, 0.2))
	cpg_values_2 = np.array(get_cpg_values(1, 0, 2*2*np.pi, 0.5))
	cpg_values_3 = np.array(get_cpg_values(1, 0, 2*2*np.pi, 0.7))
	cpg_values_4 = np.array(get_cpg_values(1, 0, 2*2*np.pi, 0.9))

	# row and column sharing
	f, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, sharex='col', sharey='row')
	ax1.plot(times, cpg_values_1, color='red', linewidth='1.5')
	ax1.set_title('Influence of duty factor on CPG shape')
	ax2.plot(times, cpg_values_2, color='green', linewidth='1.5')
	ax3.plot(times, cpg_values_3, color='blue', linewidth='1.5')
	ax4.plot(times, cpg_values_4, color='orange', linewidth='1.5')

	plt.show()

def main_phase():
	times = np.arange(0, 1, 0.001)
	cpg_values_1, cpg_values_2 = get_cpg_values_phase(1, 0, 1*2*np.pi, 0.8, np.pi, 10000)
	cpg_values_1 = np.array(cpg_values_1)
	cpg_values_2 = np.array(cpg_values_2)

	print(times.shape)
	print(cpg_values_1.shape)
	print(cpg_values_2.shape)
	plt.figure()
	plt.plot(cpg_values_1, 'r', cpg_values_2, 'b')

	# row and column sharing
	# f, ((ax1, ax2)) = plt.subplots(1, 2, sharex='col', sharey='row')
	# ax1.plot(times, cpg_values_1, color='red', linewidth='1.5')
	# ax1.set_title('Influence of duty factor on CPG shape')
	# ax2.plot(times, cpg_values_2, color='green', linewidth='1.5')
	# ax3.plot(times, cpg_values_3, color='blue', linewidth='1.5')
	# ax4.plot(times, cpg_values_4, color='orange', linewidth='1.5')
	plt.show()



def test_warning(amp):
	sol = [ 0.10839304,  0.00219942,  0.98315549,  0.99946004,  0.01733793,  0.14904551, 0.35625864,  0.99789528,  0.99547354,  0.02387772,  0.00372621,  0.16972309]
	# x = [  1.10568162e+03,   9.03963306e+02,   3.52116065e+03,   4.00326418e+03, -2.89597240e+01,  -2.32929519e+01,   1.09761294e+01,   8.98316224e-01, 7.96378833e-01,   1.50028123e-01,   2.34124879e-02,   1.06640163e+00]
	x = [  1.10568162e+03,   9.03963306e+02,   amp**2,   4.00326418e+03, -2.89597240e+01,  0,   2*np.pi,   0.5, 0.5,   0,0,0]

	mu = [x[0], x[1], x[2], x[3]]
	o = [x[4], x[4], x[5], x[5]]
	omega = [x[6], x[6], x[6], x[6]]
	d = [x[7], x[7], x[8], x[8]]
	phase_offsets = [x[9], x[10], x[11]]

	_, _, euler_1, _ = get_cpg_values_warning(mu, o, omega, d, phase_offsets, 1000, 0.001)
	_, _, euler_2, _ = get_cpg_values_warning(mu, o, omega, d, phase_offsets, 1000, 0.002)
	_, _, rk4_1, _ = get_cpg_values_rk4(mu, o, omega, d, phase_offsets, 1000, 0.001)
	_, _, rk4_2, _ = get_cpg_values_rk4(mu, o, omega, d, phase_offsets, 1000, 0.002)

	second = np.arange(0, 1, 0.001)

	# plt.switch_backend('tkagg')

	# row and column sharing
	f, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, sharex='col', sharey='row', figsize=(6.5,5))
	ax1.plot(second, euler_1)
	ax2.plot(second, euler_2)
	ax3.plot(second, rk4_1)
	ax4.plot(second, rk4_2)
	ax3.set_xlabel('Time (s)')
	ax4.set_xlabel('Time (s)')
	ax1.set_ylabel('CPG output (degrees)')
	ax3.set_ylabel('CPG output (degrees)')
	
	plt.savefig('../plots/euler_rk4.pgf')

	# plt.figure()
	# plt.subplot(221)
	# plt.plot(second, euler_1)
	# plt.subplot(222)
	# plt.plot(second, euler_2)
	# plt.subplot(223)
	# plt.plot(second, rk4_1)
	# plt.subplot(224)
	# plt.plot(second, rk4_2)
	# # plt.show()
	# plt.savefig('euler_rk4.pgf')


if __name__ == '__main__':
	# for i in range(20):
	# 	test_warning(i*5)
	test_warning(80)

