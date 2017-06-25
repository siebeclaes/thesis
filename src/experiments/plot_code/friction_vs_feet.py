import numpy as np
import matplotlib.pyplot as plt
import pickle
from generate_cpg_control import CPGControl, loadCpgParamsFromFile

friction_params = loadCpgParamsFromFile('full_friction.pickle')
feet_params = loadCpgParamsFromFile('feet_friction.pickle')

friction_actions, feet_actions = [], []

timestep = 0.01 # 10 ms
duration = 3 # seconds

# Get actions for 15 seconds
for time in range(int(duration/timestep)):
	action = friction_params.get_action(time*timestep)
	friction_actions.append(action[3])

	action = feet_params.get_action(time*timestep)
	feet_actions.append(action[3])

print(len(friction_actions))

X = np.arange(0,duration,0.01)

print(len(X))

plt.figure(figsize=(6.5,3.6))
plt.plot(X, friction_actions, label='Friction on entire leg')
plt.plot(X, feet_actions, label='Friction on feet only')
plt.xlabel('Time (s)')
plt.ylabel('CPG output (degrees)')
plt.legend()
plt.tight_layout()

plt.savefig('full_vs_feet_friction.pdf')
plt.savefig('full_vs_feet_friction.pgf')
