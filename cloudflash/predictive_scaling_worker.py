import threading
import time
from predictive_scaling import ResourcePredictor
from core import VM

class PredictiveScaler:
    def __init__(self, manager):
        self.manager = manager
        self.predictor = ResourcePredictor()
        self.interval = 20  # seconds
        self.history = []

    def collect_data(self):
        metrics = self.manager.get_metrics()
        self.history.append({
            'cpu': metrics['utilization']['cpu'],
            'ram': metrics['utilization']['ram'],
            'storage': metrics['utilization']['storage'],
            'bandwidth': sum(vm['bandwidth_used'] for vm in metrics['vms']) / sum(vm['bandwidth_capacity'] for vm in metrics['vms']) * 100 if metrics['vms'] else 0,
            'timestamp': time.time()
        })

        if len(self.history) > 100:
            self.history.pop(0)

    def predict_and_scale(self):
        if len(self.history) < 5:
            return
        self.predictor.train(self.history)
        prediction = self.predictor.predict_next(steps=1)
        predicted_cpu = prediction['cpu'][0]
        predicted_ram = prediction['ram'][0]
        predicted_storage = prediction['storage'][0]
        predicted_bandwidth = prediction['bandwidth'][0]

        self.manager.log(
            f"[PREDICTIVE-SCALER] CPU: {predicted_cpu:.1f}%, RAM: {predicted_ram:.1f}%, Storage: {predicted_storage:.1f}%, Bandwidth: {predicted_bandwidth:.1f}%"
        )

        if (
            predicted_cpu > 80 or 
            predicted_ram > 75 or 
            predicted_storage > 85 or 
            predicted_bandwidth > 80
        ):
            new_vm = VM(cpu=4, ram=8, storage=100, bandwidth=1000, gpu=1)
            self.manager.add_vm(new_vm)
            self.manager.log(f"[PREDICTIVE-SCALER] Scaled up with new VM {new_vm.id}")

    def start(self):
        def run():
            while True:
                self.collect_data()
                self.predict_and_scale()
                time.sleep(self.interval)
        threading.Thread(target=run, daemon=True).start()
