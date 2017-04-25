import numpy as np
import time
import os

GAME_TITLE = 'Quadruped-v1'
RENDER = False

amplitude = 30
simulation_length = 20 #10 seconds
skip_frames = 5


class CPGControl:
	def __init__(self, mu, offset, omega, d, coupling, phase_offset):
		self.mu = mu
		self.o = offset
		self.omega = omega
		self.d = d
		self.coupling = coupling

		self.closed_loop = False

		self.psi = [ # Bound gait
			[0, 0, phase_offset, phase_offset],
			[0, 0, phase_offset, phase_offset],
			[phase_offset, phase_offset, 0, 0],
			[phase_offset, phase_offset, 0, 0],
		]

		self.gamma = 5
		self.dt = 0.0001
		self.prev_time = -1

		self.r = [1] * 4
		self.phi = [1] * 4
		self.theta = [0] * 4
		self.kappa_r = [1] * 4
		self.kappa_phi = [1] * 4
		self.kappa_o = [1] * 4

	def step_closed_loop(self, forces):
		return step_open_loop() # TODO: implement this

	def step_open_loop(self):
		Fr = [0] * 4
		Fphi = [0] * 4
		Fo = [0] * 4

		return self.step_cpg(Fr, Fphi, Fo)

	def step_cpg(self, Fr, Fphi, Fo):
		actions = []
		# print 'Do iteration'

		for i in range(4):
			d_r = self.gamma * (self.mu[i] + self.kappa_r[i] * Fr[i] - self.r[i] * self.r[i]) * self.r[i]
			d_phi = self.omega[i] + self.kappa_phi[i] * Fphi[i]
			d_o = self.kappa_o[i] * Fo[i]

			# Add phase coupling
			for j in range(4):
				d_phi += self.coupling[i][j] * np.sin(self.phi[j] - self.phi[i] - self.psi[i][j])

			self.r[i] += self.dt * d_r
			self.phi[i] += self.dt * d_phi
			self.o[i] += self.dt * d_o

			two_pi = 2 * 3.141592654

			phi_L = 0
			phi_2pi = self.phi[i] % two_pi
			if phi_2pi < (two_pi * self.d[i]):
				phi_L = phi_2pi / (2 * self.d[i])
			else:
				phi_L = (phi_2pi + two_pi * (1 - 2 * self.d[i])) / (2 * (1 - self.d[i]))

			action = self.r[i] * np.cos(phi_L) + self.o[i]
			actions.append(action)

		return actions

	def get_action(self, time, forces=None):
		num_steps = (int(time/self.dt) - self.prev_time)
		actions = []

		# print num_steps

		for _ in range(num_steps):
			if self.closed_loop:
				actions = self.step_closed_loop(forces)
			else:
				actions = self.step_open_loop()

		self.prev_time = int(time/self.dt)
		return actions

def loadCpgParamsFromFile(filename):
    import pickle
    with open(filename, 'rb') as f:
        params = pickle.load(f)
        # print params
        return loadCpgParams(params)


def loadCpgParams(x):
    from CpgControl import CPGControl

    mu = [x[0], x[1], x[2], x[3]]
    o = [x[4], x[4], x[5], x[5]]
    omega = [x[6], x[6], x[7], x[7]]
    d = [x[8], x[8], x[9], x[9]]
    coupling = [[0, x[10], x[11], x[13]], [x[10], 0, x[12], x[14]], [x[11], x[12], 0, x[15]], [x[13], x[14], x[15], 0]]
    phase_offset = x[16]

    cpg = CPGControl(mu, o, omega, d, coupling, phase_offset)
    return cpg

if __name__ == '__main__':
	# cpg = loadCpgParamsFromFile('5_variations_E0_20.pickle')
	cpg = loadCpgParamsFromFile('2_variations.pickle')

	actions = []
	for time in range(1500):
		action = cpg.get_action(time/100.0)
		actions.append(action)

	with open('2_variations_control_signal.pickle', 'wb') as f:
		import pickle
		pickle.dump(actions, f, 2)

