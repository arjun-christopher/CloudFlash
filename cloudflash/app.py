from flask import Flask, request, jsonify, render_template, redirect, url_for
from core import ResourceManager, VM, Cloudlet
import time
from flask_socketio import SocketIO, emit
import threading
from prometheus_client import make_wsgi_app, Gauge, Counter, Histogram
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple
import psutil
import os
import subprocess
import atexit
import signal
import sys
from pathlib import Path

# Global variable to store the monitoring process
monitoring_process = None

# Paths
BASE_DIR = Path(__file__).parent.parent
MONITORING_DIR = BASE_DIR / 'cloudflash/monitoring'
DOCKER_COMPOSE_FILE = MONITORING_DIR / 'docker-compose.monitoring.yml'  # Updated to match actual filename

def _run_monitoring_command(command, timeout=30):
    """Helper function to run docker-compose commands with timeout."""
    try:
        monitoring_dir = str(MONITORING_DIR.absolute())
        docker_compose_path = str(DOCKER_COMPOSE_FILE.absolute())
        
        # Use the full path to docker-compose if available
        docker_compose_cmd = 'docker-compose'
        if os.name == 'nt':  # Windows
            docker_compose_cmd = 'docker-compose.exe'
        
        cmd = [docker_compose_cmd, '-f', docker_compose_path] + command
        
        print(f"   - Running: {' '.join(cmd)}")
        
        # Run with timeout
        result = subprocess.run(
            cmd,
            cwd=monitoring_dir,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"❌ Command timed out after {timeout} seconds")
        return None
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return None

def start_monitoring_stack():
    """Start the monitoring stack using Docker Compose."""
    try:
        print("🔍 Checking Docker...")
        # Check if Docker is running
        try:
            docker_info = subprocess.run(
                ['docker', 'info'], 
                capture_output=True, 
                text=True
            )
            if docker_info.returncode != 0:
                print("❌ Docker is not running or not installed.")
                if docker_info.stderr:
                    print(f"   - Error: {docker_info.stderr.strip()}")
                print("   - Please start Docker Desktop and try again.")
                return False
        except FileNotFoundError:
            print("❌ Docker is not installed. Please install Docker Desktop from https://www.docker.com/products/docker-desktop/")
            return False
            
        print("✅ Docker is running")
        
        # Get the absolute paths
        monitoring_dir = str(MONITORING_DIR.absolute())
        docker_compose_path = str(DOCKER_COMPOSE_FILE.absolute())
        
        print(f"📂 Monitoring directory: {monitoring_dir}")
        print(f"📄 Using compose file: {docker_compose_path}")
        
        # Stop any existing containers first
        print("🛑 Stopping any existing monitoring containers...")
        stop_result = _run_monitoring_command(['down', '--remove-orphans'])
        
        # Start the monitoring containers
        print("🚀 Starting monitoring stack...")
        start_result = _run_monitoring_command(['up', '-d'])
        
        if start_result and start_result.returncode == 0:
            print("✅ Monitoring stack started successfully")
            print("   - Grafana: http://localhost:3000 (admin/admin)")
            print("   - Prometheus: http://localhost:9090")
            return True
        else:
            print("❌ Failed to start monitoring stack")
            if start_result:
                if start_result.stdout:
                    print("=== STDOUT ===\n", start_result.stdout)
                if start_result.stderr:
                    print("=== STDERR ===\n", start_result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Unexpected error starting monitoring stack: {e}")
        import traceback
        traceback.print_exc()
        return False

def stop_monitoring():
    """Stop the monitoring stack."""
    global monitoring_process
    if monitoring_process:
        try:
            subprocess.run(
                ['docker-compose', '-f', str(DOCKER_COMPOSE_FILE), 'down', '-v'],
                cwd=str(MONITORING_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            monitoring_process = None
            print("\n🛑 Monitoring stack stopped and cleaned up.")
        except Exception as e:
            print(f"❌ Error stopping monitoring stack: {e}")

def cleanup():
    """Cleanup function to be called on exit."""
    stop_monitoring()
    print("\n👋 Goodbye!")

# Register cleanup function
atexit.register(cleanup)

def signal_handler(sig, frame):
    """Handle interrupt signals."""
    print("\n🛑 Received interrupt signal. Cleaning up...")
    cleanup()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Initialize Flask app and SocketIO
app = Flask(__name__)
socketio = SocketIO(app)

# Initialize resource manager
manager = ResourceManager()
manager.set_metrics_callback(lambda: socketio.emit('metrics_update', manager.get_metrics()))

# Prometheus metrics
REQUEST_TIME = Histogram('request_latency_seconds', 'Request latency in seconds',
                       ['endpoint', 'method'])
VM_GAUGE = Gauge('vm_count', 'Number of active VMs')
CLOUDLET_GAUGE = Gauge('cloudlet_count', 'Number of active cloudlets')
CPU_USAGE = Gauge('cpu_usage_percent', 'CPU usage percentage', ['vm_id'])
MEMORY_USAGE = Gauge('memory_usage_mb', 'Memory usage in MB', ['vm_id'])
STORAGE_USAGE = Gauge('storage_usage_gb', 'Storage usage in GB', ['vm_id'])
BANDWIDTH_USAGE = Gauge('bandwidth_usage_mbps', 'Bandwidth usage in Mbps', ['vm_id'])
GPU_USAGE = Gauge('gpu_usage_percent', 'GPU usage percentage', ['vm_id'])

# Add prometheus wsgi middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(
    app.wsgi_app, {
        '/metrics': make_wsgi_app()
    }
)

def update_prometheus_metrics():
    """Update Prometheus metrics with current resource usage"""
    metrics = manager.get_metrics()
    
    # Update VM and Cloudlet counts
    VM_GAUGE.set(len(metrics.get('vms', [])))
    CLOUDLET_GAUGE.set(len(metrics.get('cloudlets', [])))
    
    # Update resource usage per VM
    for vm in metrics.get('vms', []):
        vm_id = vm.get('id', 'unknown')
        CPU_USAGE.labels(vm_id=vm_id).set(vm.get('cpu_used', 0))
        MEMORY_USAGE.labels(vm_id=vm_id).set(vm.get('ram_used', 0))
        STORAGE_USAGE.labels(vm_id=vm_id).set(vm.get('storage_used', 0) / 1024)  # Convert MB to GB
        BANDWIDTH_USAGE.labels(vm_id=vm_id).set(vm.get('bandwidth_used', 0))
        GPU_USAGE.labels(vm_id=vm_id).set(vm.get('gpu_used', 0))

# Update metrics every 5 seconds
def metrics_updater():
    while True:
        update_prometheus_metrics()
        time.sleep(5)

# Start metrics updater in a background thread
metrics_thread = threading.Thread(target=metrics_updater, daemon=True)
metrics_thread.start()

# --- Helper to broadcast metrics ---
def broadcast_metrics():
    socketio.emit('metrics_update', manager.get_metrics())

@app.route('/')
def index():
    # Ensure monitoring stack is running
    if MONITORING_DIR.exists() and DOCKER_COMPOSE_FILE.exists():
        start_monitoring_stack()
    return render_template('index.html', 
                         vms=manager.get_vms(), 
                         cloudlets=manager.get_cloudlets(),
                         metrics=manager.get_metrics())

@app.route('/monitoring')
def monitoring():
    """Redirect to Grafana dashboard with fallback."""
    try:
        # Try to check if Grafana is accessible
        import socket
        socket.create_connection(('localhost', 3000), timeout=1)
        return redirect('http://localhost:3000')
    except (socket.error, OSError):
        return """
        <html>
        <head><title>CloudFlash</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>⚠️ Grafana Not Running</h1>
            <p>Grafana is not currently running. To enable monitoring:</p>
            <ol style="text-align: left; max-width: 600px; margin: 20px auto;">
                <li>Install Docker Desktop from <a href="https://www.docker.com/products/docker-desktop/" target="_blank">docker.com</a></li>
                <li>Start Docker Desktop</li>
                <li>Restart the CloudFlash application</li>
            </ol>
            <p><a href="/">← Back to CloudFlash</a></p>
        </body>
        </html>
        """, 503

@app.route('/prometheus')
def prometheus():
    """Redirect to Prometheus UI with fallback."""
    try:
        # Try to check if Prometheus is accessible
        import socket
        socket.create_connection(('localhost', 9090), timeout=1)
        return redirect('http://localhost:9090')
    except (socket.error, OSError):
        return """
        <html>
        <head><title>CloudFlash</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>⚠️ Prometheus Not Running</h1>
            <p>Prometheus is not currently running. To enable monitoring:</p>
            <ol style="text-align: left; max-width: 600px; margin: 20px auto;">
                <li>Install Docker Desktop from <a href="https://www.docker.com/products/docker-desktop/" target="_blank">docker.com</a></li>
                <li>Start Docker Desktop</li>
                <li>Restart the CloudFlash application</li>
            </ol>
            <p><a href="/">← Back to CloudFlash</a></p>
        </body>
        </html>
        """, 503

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

@app.route('/metrics')
def metrics():
    return make_wsgi_app()

def broadcast_metrics_loop():
    """Background thread to broadcast metrics to all connected clients."""
    while True:
        try:
            socketio.emit('metrics_update', manager.get_metrics())
            time.sleep(1)  # Update every second
        except Exception as e:
            print(f"Error broadcasting metrics: {e}")
            time.sleep(5)  # Wait longer if there's an error

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "timestamp": time.time()})

def start_monitoring_async():
    """Start the monitoring stack in a separate thread."""
    print("\n🔄 Starting monitoring stack in background...")
    try:
        if start_monitoring_stack():
            print("✅ Monitoring stack started successfully")
            print("   - Grafana: http://localhost:3000 (admin/admin)")
            print("   - Prometheus: http://localhost:9090")
        else:
            print("⚠️  Could not start monitoring stack. The application will continue without monitoring.")
            print("   Make sure Docker Desktop is installed and running if you want to use monitoring features.")
    except Exception as e:
        print(f"❌ Error in monitoring thread: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("🚀 Starting CloudFlash...")
    print("🔗 Access the application at: http://localhost:5000")
    
    # Check if monitoring should be started
    if MONITORING_DIR.exists() and DOCKER_COMPOSE_FILE.exists():
        # Start monitoring in a separate thread
        monitoring_thread = threading.Thread(target=start_monitoring_async, daemon=True)
        monitoring_thread.start()
    else:
        print("ℹ️  Monitoring stack not found. Running without monitoring.")
        if not MONITORING_DIR.exists():
            print(f"   - Missing directory: {MONITORING_DIR}")
        if not DOCKER_COMPOSE_FILE.exists():
            print(f"   - Missing file: {DOCKER_COMPOSE_FILE}")
    
    # Start the background thread for broadcasting metrics
    try:
        metrics_thread = threading.Thread(target=broadcast_metrics_loop, daemon=True)
        metrics_thread.start()
        print("📊 Metrics broadcasting started")
    except Exception as e:
        print(f"⚠️  Failed to start metrics broadcasting: {e}")
    
    try:
        # Start the Flask development server
        print("\nStarting server...")
        print("   - Application: http://localhost:5000")
        print("   - Stop the server with CTRL+C")
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
    finally:
        # Ensure monitoring stack is stopped when the application exits
        if MONITORING_DIR.exists() and DOCKER_COMPOSE_FILE.exists():
            print("\n🛑 Stopping monitoring stack...")
            try:
                subprocess.run(
                    ['docker-compose', '-f', str(DOCKER_COMPOSE_FILE), 'down'],
                    cwd=str(MONITORING_DIR),
                    capture_output=True,
                    text=True
                )
                print("✅ Monitoring stack stopped")
            except Exception as e:
                print(f"❌ Error stopping monitoring stack: {e}")