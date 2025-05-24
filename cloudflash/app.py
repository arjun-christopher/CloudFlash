from flask import Flask, request, jsonify, render_template
from core import ResourceManager, VM, Cloudlet
import time
from flask_socketio import SocketIO, emit
import threading

app = Flask(__name__)
socketio = SocketIO(app)
manager = ResourceManager()
manager.set_metrics_callback(lambda: socketio.emit('metrics_update', manager.get_metrics()))

# --- Helper to broadcast metrics ---
def broadcast_metrics():
    socketio.emit('metrics_update', manager.get_metrics())

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/vms", methods=["POST"])
def create_vm():
    data = request.json
    try:
        cpu = int(data.get("cpu"))
        ram = int(data.get("ram"))
        storage = int(data.get("storage"))
        bandwidth = int(data.get("bandwidth", 1000))
        gpu = int(data.get("gpu", 0))
        vm = VM(cpu, ram, storage, bandwidth, gpu)
        manager.add_vm(vm)
        broadcast_metrics()
        return jsonify({"status": "success", "vm_id": vm.id}), 201
    except Exception as e:
        print("Error in /api/vms:", e)
        return jsonify({"status": "error", "error": str(e)}), 400

@app.route("/api/cloudlets", methods=["POST"])
def submit_cloudlet():
    data = request.json
    try:
        cpu = int(data.get("cpu"))
        ram = int(data.get("ram"))
        storage = int(data.get("storage"))
        bandwidth = int(data.get("bandwidth", 100))
        gpu = int(data.get("gpu", 0))
        sla_priority = int(data.get("sla_priority", 2))
        deadline = int(data.get("deadline", 60))  # seconds from now
        name = data.get("name")
        cloudlet = Cloudlet(cpu, ram, storage, sla_priority, deadline, name, bandwidth, gpu)
        manager.submit_cloudlet(cloudlet)
        broadcast_metrics()
        return jsonify({"status": "success", "cloudlet_id": cloudlet.id}), 201
    except Exception as e:
        print("Error in /api/cloudlets:", e)
        return jsonify({"status": "error", "error": str(e)}), 400

@app.route("/api/cloudlets/complete", methods=["POST"])
def complete_cloudlet():
    data = request.json
    cloudlet_id = data.get("cloudlet_id")
    manager.complete_cloudlet(cloudlet_id)
    broadcast_metrics()
    return jsonify({"status": "success"})

@app.route("/api/cloudlets/<cloudlet_id>", methods=["DELETE"])
def delete_cloudlet(cloudlet_id):
    try:
        result = manager.delete_cloudlet(cloudlet_id)
        broadcast_metrics()
        if result:
            return jsonify({"status": "success", "cloudlet_id": cloudlet_id}), 200
        else:
            return jsonify({"status": "not_found", "cloudlet_id": cloudlet_id}), 404
    except Exception as e:
        print("Error in /api/cloudlets/<cloudlet_id> [DELETE]:", e)
        return jsonify({"status": "error", "error": str(e)}), 400

@app.route("/api/vms/<vm_id>", methods=["DELETE"])
def delete_vm(vm_id):
    try:
        result = manager.delete_vm(vm_id)
        broadcast_metrics()
        if result:
            return jsonify({"status": "success", "vm_id": vm_id}), 200
        else:
            return jsonify({"status": "not_found", "vm_id": vm_id}), 404
    except Exception as e:
        print("Error in /api/vms/<vm_id> [DELETE]:", e)
        return jsonify({"status": "error", "error": str(e)}), 400

@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    return jsonify(manager.get_metrics())

@app.route("/api/vms", methods=["GET"])
def list_vms():
    return jsonify(manager.get_metrics()["vms"])

@app.route("/api/cloudlets", methods=["GET"])
def list_cloudlets():
    return jsonify(manager.get_metrics()["cloudlets"])

class AutoScaler:
    def __init__(self, manager, check_interval=10, cpu_threshold=70, min_vms=1, max_vms=10, cooldown=30):
        self.manager = manager
        self.check_interval = check_interval
        self.cpu_threshold = cpu_threshold
        self.min_vms = min_vms
        self.max_vms = max_vms
        self.cooldown = cooldown
        self.last_scale_time = 0
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        while self.running:
            self.check_and_scale()
            time.sleep(self.check_interval)

    def check_and_scale(self):
        metrics = self.manager.get_metrics()
        avg_cpu = self.calculate_avg_cpu(metrics["vms"])
        now = time.time()

        if now - self.last_scale_time < self.cooldown:
            return  # Cooldown period

        if avg_cpu > self.cpu_threshold and len(metrics["vms"]) < self.max_vms:
            self.manager.add_vm(VM(...))  # Add VM with desired specs
            self.last_scale_time = now
        elif avg_cpu < self.cpu_threshold * 0.5 and len(metrics["vms"]) > self.min_vms:
            idle_vm = self.manager.find_idle_vm()
            if idle_vm:
                self.manager.delete_vm(idle_vm.id)
                self.last_scale_time = now

    def calculate_avg_cpu(self, vms):
        if not vms:
            return 0
        return sum(vm["cpu_usage"] for vm in vms) / len(vms)

if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000)