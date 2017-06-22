import glob
from pymongo import MongoClient
import pickle

file_list = glob.glob('experiment_logs/*.pickle')

client = MongoClient('localhost', 27017)
db = client['thesis']
experiments_collection = db['gait_transition']

for filename in file_list:
	with open(filename, 'rb') as f:
		doc = pickle.load(f)
		insert_result = experiments_collection.insert_one(doc)