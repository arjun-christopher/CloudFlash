import pickle
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import os

class ResourcePredictor:
    def __init__(self):
        self.cpu_model = RandomForestRegressor()
        self.ram_model = RandomForestRegressor()
        self.storage_model = RandomForestRegressor()
        self.bandwidth_model = RandomForestRegressor()
        self.training_steps = 0

    def train(self, history):
        self.training_steps = len(history)
        X = np.array([[i] for i in range(self.training_steps)])
        y_cpu = np.array([entry['cpu'] for entry in history])
        y_ram = np.array([entry['ram'] for entry in history])
        y_storage = np.array([entry['storage'] for entry in history])
        y_bandwidth = np.array([entry['bandwidth'] for entry in history])

        self.cpu_model.fit(X, y_cpu)
        self.ram_model.fit(X, y_ram)
        self.storage_model.fit(X, y_storage)
        self.bandwidth_model.fit(X, y_bandwidth)

    def predict_next(self, steps=1):
        future = np.array([[self.training_steps + i] for i in range(steps)])
        return {
            'cpu': self.cpu_model.predict(future).tolist(),
            'ram': self.ram_model.predict(future).tolist(),
            'storage': self.storage_model.predict(future).tolist(),
            'bandwidth': self.bandwidth_model.predict(future).tolist()
        }

    def save_models(self, path='cloudflash/models/'):
        os.makedirs(path, exist_ok=True)
        
        with open(os.path.join(path, 'cpu_model.pkl'), 'wb') as f:
            pickle.dump(self.cpu_model, f)
        with open(os.path.join(path, 'ram_model.pkl'), 'wb') as f:
            pickle.dump(self.ram_model, f)
        with open(os.path.join(path, 'storage_model.pkl'), 'wb') as f:
            pickle.dump(self.storage_model, f)
        with open(os.path.join(path, 'bandwidth_model.pkl'), 'wb') as f:
            pickle.dump(self.bandwidth_model, f)

    def load_models(self, path='cloudflash/models/'):
        os.makedirs(path, exist_ok=True)
        for model_name in ['cpu', 'ram', 'storage', 'bandwidth']:
            file_path = os.path.join(path, f'{model_name}_model.pkl')
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    setattr(self, f'{model_name}_model', pickle.load(f))
            else:
                print(f"⚠️ Warning: {file_path} not found.")

