from pymongo import MongoClient
from bson.objectid import ObjectId
import numpy as np

import matplotlib.pyplot as plt

ids = ['58c7fd3098692e19898d2398', '58c7fefa98692e19898d239a', '58c8007e98692e19898d239c', '58c801ed98692e19898d239e', '58c803d598692e19898d23a0', '58c8052998692e19898d23a2', '58c806c098692e19898d23a4', '58c8080798692e19898d23a6', '58c809b398692e19898d23a8', '58c80b5498692e19898d23aa', '58c80ce798692e19898d23ac', '58c80eb398692e19898d23ae', '58c8103c98692e19898d23b0', '58c811b998692e19898d23b2', '58c8135c98692e19898d23b4']

E0 = []
energy = []
distance = []

# E0 = [1,3,5,7,10,13,15,17,20]
# energy = [1,3,5,7,10,13,15,17,20]
# distance = [10,30,50,70,100,130,150,170,200]

client = MongoClient('localhost', 27017)
db = client['thesis']
experiments_collection = db['experiments']

for experiment_id in ids:
	experiment = experiments_collection.find_one({'_id': ObjectId(experiment_id)})
	best_id = experiment['results']['best_id']
	best_run = experiment['results']['simulations'][best_id]

	E0.append(experiment['E0'])
	energy.append(best_run['energy'])
	distance.append(best_run['distance'])

fig, ax1 = plt.subplots()
ax1.plot(E0, energy, color='b')
ax1.set_xlabel('E0')
ax1.set_ylabel('Energy', color='b')
ax1.tick_params('y', colors='b')

ax2 = ax1.twinx()
ax2.plot(E0, distance, color='r')
ax2.set_ylabel('Distance', color='r')
ax2.tick_params('y', colors='r')

# fig.tight_layout()
plt.title('Distance and energy vs energy threshold E0')
plt.show()