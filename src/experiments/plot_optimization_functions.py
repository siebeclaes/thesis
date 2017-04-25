import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import random

def fun(distance, energy):
  # return 0 if distance < 0 else (10-0.01*(energy-30)**2)*(distance)
  return 0 if distance < 0 else (distance * np.tanh(60/energy))

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

distance_range = np.arange(-1.0, 5.0, 0.05)
energy_range = np.arange(0, 50.0, 0.05)

X, Y = np.meshgrid(distance_range, energy_range)
zs = np.array([fun(x,y) for x,y in zip(np.ravel(X), np.ravel(Y))])
Z = zs.reshape(X.shape)

ax.plot_surface(X, Y, Z)

ax.set_xlabel('Distance')
ax.set_ylabel('Energy')
ax.set_zlabel('Reward')

plt.show()