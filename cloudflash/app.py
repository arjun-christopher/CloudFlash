from flask import Flask, request, jsonify, render_template, redirect, url_for
from core import ResourceManager, VM, Cloudlet
from flask_socketio import SocketIO, emit
from prometheus_client import make_wsgi_app, Gauge, Counter, Histogram
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import threading
import json
import atexit
import signal
import sys
import subprocess
import traceback
import socket
import requests
import psutil
import os
from pathlib import Path
import time
from typing import Optional, List, Dict, Any

# Initialize Flask and SocketIO
app = Flask(__name__)
socketio = SocketIO(app)

# Initialize resource manager
manager = ResourceManager()

# Monitoring configuration
MONITORING_DIR = Path(__file__).parent / 'monitoring'
DOCKER_COMPOSE_FILE = MONITORING_DIR / 'docker-compose.monitoring.yml'
monitoring_process = None

# Prometheus metrics
VM_GAUGE = Gauge('vm_count', 'Number of active VMs')
CLOUDLET_GAUGE = Gauge('cloudlet_count', 'Number of active Cloudlets')
CPU_USAGE = Gauge('cpu_usage_percent', 'CPU usage percentage', ['vm_id'])
MEMORY_USAGE = Gauge('memory_usage_mb', 'Memory usage in MB', ['vm_id'])
STORAGE_USAGE = Gauge('storage_usage_gb', 'Storage usage in GB', ['vm_id'])
BANDWIDTH_USAGE = Gauge('bandwidth_usage_mbps', 'Bandwidth usage in Mbps', ['vm_id'])
GPU_USAGE = Gauge('gpu_usage_percent', 'GPU usage percentage', ['vm_id'])
MEMORY_PAGES_TOTAL = Gauge('memory_pages_total', 'Total memory pages')
MEMORY_PAGES_FREE = Gauge('memory_pages_free', 'Free memory pages')
FRAGMENTATION_PERCENT = Gauge('fragmentation_percent', 'Memory fragmentation percentage')
REQUEST_TIME = Histogram('request_latency_seconds', 'Request latency in seconds', ['endpoint', 'method'])

# Add prometheus wsgi middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

# Set up metrics callback
manager.set_metrics_callback(lambda: socketio.emit('metrics_update', manager.get_metrics()))

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
        print("=== Starting monitoring stack...")
        start_result = _run_monitoring_command(['up', '-d'])
        if start_result and start_result.returncode == 0:
            print("✅ Monitoring stack started")
            return True
        else:
            print("=== STDOUT ===\n", start_result.stdout)
            if start_result.stderr:
                print("=== STDERR ===\n", start_result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Unexpected error starting monitoring stack: {e}")
        import traceback
        traceback.print_exc()
        return False

def start_monitoring_async():
    print("\n🔄 Starting monitoring stack in background...")
    try:
        if start_monitoring_stack():
            print("✅ Monitoring stack started successfully")
            print("   - Grafana: http://localhost:3000 (admin/admin)")
            print("   - Prometheus: http://localhost:9090")
        else:
            print("⚠️ Could not start monitoring stack. The application will continue without monitoring.")
            print("   Make sure Docker Desktop is installed and running if you want to use monitoring features.")
    except Exception as e:
        print(f"❌ Error in monitoring thread: {e}")
        import traceback
        traceback.print_exc()

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

def update_prometheus_metrics():
    """Update Prometheus metrics with current resource usage"""
    metrics = manager.get_metrics()
    VM_GAUGE.set(len(metrics.get('vms', [])))
    CLOUDLET_GAUGE.set(len([cl for cl in metrics.get('cloudlets', []) if cl['status'] == 'ACTIVE']))
    
    # Update VM-specific metrics
    for vm in metrics.get('vms', []):
        vm_id = vm.get('id', 'unknown')
        CPU_USAGE.labels(vm_id=vm_id).set(vm.get('cpu_used', 0))
        MEMORY_USAGE.labels(vm_id=vm_id).set(vm.get('ram_used', 0))
        STORAGE_USAGE.labels(vm_id=vm_id).set(vm.get('storage_used', 0) / 1024)  # Convert to GB
        BANDWIDTH_USAGE.labels(vm_id=vm_id).set(vm.get('bandwidth_used', 0))
        GPU_USAGE.labels(vm_id=vm_id).set(vm.get('gpu_used', 0))
    
    # Update memory metrics
    if 'memory' in metrics:
        MEMORY_PAGES_TOTAL.set(metrics['memory'].get('total_pages', 0))
        MEMORY_PAGES_FREE.set(metrics['memory'].get('free_pages', 0))
        FRAGMENTATION_PERCENT.set(metrics['memory'].get('fragmentation', 0))

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
                         metrics=manager.get_metrics())

@app.route('/prometheus')
def prometheus():
    prometheus_url = 'http://localhost:9090'
    
    try:
        # Initialize query parameters
        query_params = []
        
        # List of queries to execute with their labels
        queries = [
            # Resource Counts
            {'expr': 'vm_count', 'label': 'Total VMs', 'unit': 'count'},
            {'expr': 'cloudlet_count', 'label': 'Total Cloudlets', 'unit': 'count'},
            
            # CPU Metrics
            {'expr': 'avg(cpu_usage_percent)', 'label': 'Average CPU Usage', 'unit': '%'},
            {'expr': 'max(cpu_usage_percent)', 'label': 'Peak CPU Usage', 'unit': '%'},
            {'expr': 'min(cpu_usage_percent)', 'label': 'Lowest CPU Usage', 'unit': '%'},
            
            # Memory Metrics
            {'expr': 'avg(memory_usage_mb)', 'label': 'Average Memory Usage', 'unit': 'MB'},
            {'expr': 'max(memory_usage_mb)', 'label': 'Peak Memory Usage', 'unit': 'MB'},
            {'expr': 'min(memory_usage_mb)', 'label': 'Lowest Memory Usage', 'unit': 'MB'},
            
            # Storage Metrics
            {'expr': 'avg(storage_usage_gb)', 'label': 'Average Storage Usage', 'unit': 'GB'},
            {'expr': 'max(storage_usage_gb)', 'label': 'Peak Storage Usage', 'unit': 'GB'},
            {'expr': 'min(storage_usage_gb)', 'label': 'Lowest Storage Usage', 'unit': 'GB'},
            
            # Bandwidth Metrics
            {'expr': 'avg(bandwidth_usage_mbps)', 'label': 'Average Bandwidth', 'unit': 'Mbps'},
            {'expr': 'max(bandwidth_usage_mbps)', 'label': 'Peak Bandwidth', 'unit': 'Mbps'},
            {'expr': 'min(bandwidth_usage_mbps)', 'label': 'Lowest Bandwidth', 'unit': 'Mbps'},
            
            # GPU Metrics
            {'expr': 'avg(gpu_usage_percent)', 'label': 'Average GPU Usage', 'unit': '%'},
            {'expr': 'max(gpu_usage_percent)', 'label': 'Peak GPU Usage', 'unit': '%'},
            {'expr': 'min(gpu_usage_percent)', 'label': 'Lowest GPU Usage', 'unit': '%'},
            
            # Resource Utilization
            {'expr': 'rate(vm_count[5m])', 'label': 'VM Creation Rate', 'unit': 'VMs/5min'}
        ]
        
        # Add proper formatting for each query
        for i, query in enumerate(queries):
            # Basic query parameters
            query_params.append(f'g{i}.expr={query["expr"]}')
            query_params.append(f'g{i}.tab=0')
            query_params.append(f'g{i}.title={query["label"]}')
            query_params.append(f'g{i}.range_input=1h')
            query_params.append(f'g{i}.step=15')
            query_params.append(f'g{i}.end=')
            query_params.append(f'g{i}.start=1h')
            
            # Display settings
            query_params.append(f'g{i}.width=1200')
            query_params.append(f'g{i}.height=250')
            query_params.append(f'g{i}.grid=1')
            query_params.append(f'g{i}.show_legend=1')
            query_params.append(f'g{i}.tooltip=1')
            query_params.append(f'g{i}.legendFormat={query["label"]}')
            
            # Axis settings
            query_params.append(f'g{i}.yaxis=left')
            query_params.append(f'g{i}.yaxis_label={query["label"]}')
            query_params.append(f'g{i}.yaxis_unit={query.get("unit", "")}')
            query_params.append(f'g{i}.yaxis_min=0')
            if query["label"].startswith("Average"):
                query_params.append(f'g{i}.yaxis_max=100')
            else:
                query_params.append(f'g{i}.yaxis_max=')
            
            # Formatting
            query_params.append(f'g{i}.format={query.get("unit", "")}')
            query_params.append(f'g{i}.minspan=1')
            query_params.append(f'g{i}.maxspan=1')
        for i, query in enumerate(queries):
            query_params.append(f'g{i}.expr={query["expr"]}')
            query_params.append(f'g{i}.tab=0')
            query_params.append(f'g{i}.title={query["label"]}')
        
        # Create the final URL with all parameters
        query_url = f"{prometheus_url}/graph?{'&'.join(query_params)}"
            
        # Try to access Prometheus to verify it's running
        response = requests.get(f'{prometheus_url}/api/v1/query', params={'query': 'vm_count'}, timeout=2)
        if response.status_code == 200:
            # Create a dashboard URL with all queries
            dashboard_url = f"{prometheus_url}/graph?{query_url}"
            return redirect(dashboard_url)
        else:
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
    except (requests.exceptions.RequestException, socket.error, OSError):
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
@app.route("/api/vms", methods=["POST"])
def create_vm():
    with REQUEST_TIME.labels(endpoint='/api/vms', method='POST').time():
        data = request.json
        try:
            cpu = int(data.get("cpu"))
            ram = int(data.get("ram"))
            storage = int(data.get("storage"))
            bandwidth = int(data.get("bandwidth", 1000))
            gpu = int(data.get("gpu", 0))
            
            vm = VM(cpu, ram, storage, bandwidth, gpu)
            if manager.add_vm(vm):
                socketio.emit('metrics_update', manager.get_metrics())
                return jsonify({"status": "success", "vm_id": vm.id}), 201
            return jsonify({"status": "error", "error": "Insufficient memory pages"}), 400
        except Exception as e:
            print("Error in /api/vms:", e)
            return jsonify({"status": "error", "error": str(e)}), 400

@app.route("/api/cloudlets", methods=["POST"])
@app.route("/api/cloudlets", methods=["POST"])
def submit_cloudlet():
    with REQUEST_TIME.labels(endpoint='/api/cloudlets', method='POST').time():
        data = request.json
        try:
            cpu = int(data.get("cpu"))
            ram = int(data.get("ram"))
            storage = int(data.get("storage"))
            bandwidth = int(data.get("bandwidth", 100))
            gpu = int(data.get("gpu", 0))
            sla_priority = int(data.get("sla_priority", 2))
            deadline = int(data.get("deadline", 60))
            name = data.get("name")
            
            cloudlet = Cloudlet(cpu, ram, storage, sla_priority, deadline, name, bandwidth, gpu)
            manager.submit_cloudlet(cloudlet)
            socketio.emit('metrics_update', manager.get_metrics())
            return jsonify({"status": "success", "cloudlet_id": cloudlet.id}), 201
        except Exception as e:
            print("Error in /api/cloudlets:", e)
            return jsonify({"status": "error", "error": str(e)}), 400

@app.route("/api/cloudlets/complete", methods=["POST"])
@app.route("/api/cloudlets/complete", methods=["POST"])
def complete_cloudlet():
    with REQUEST_TIME.labels(endpoint='/api/cloudlets/complete', method='POST').time():
        data = request.json
        cloudlet_id = data.get("cloudlet_id")
        manager.complete_cloudlet(cloudlet_id)
        socketio.emit('metrics_update', manager.get_metrics())
        return jsonify({"status": "success"})

@app.route("/api/cloudlets/<cloudlet_id>", methods=["DELETE"])
@app.route("/api/cloudlets/<cloudlet_id>", methods=["DELETE"])
def delete_cloudlet(cloudlet_id):
    with REQUEST_TIME.labels(endpoint='/api/cloudlets/<cloudlet_id>', method='DELETE').time():
        try:
            result = manager.delete_cloudlet(cloudlet_id)
            socketio.emit('metrics_update', manager.get_metrics())
            if result:
                return jsonify({"status": "success", "cloudlet_id": cloudlet_id}), 200
            else:
                return jsonify({"status": "not_found", "cloudlet_id": cloudlet_id}), 404
        except Exception as e:
            print("Error in /api/cloudlets/<cloudlet_id> [DELETE]:", e)
            return jsonify({"status": "error", "error": str(e)}), 400

@app.route("/api/vms/<vm_id>", methods=["DELETE"])
@app.route("/api/vms/<vm_id>", methods=["DELETE"])
def delete_vm(vm_id):
    with REQUEST_TIME.labels(endpoint='/api/vms/<vm_id>', method='DELETE').time():
        try:
            result = manager.delete_vm(vm_id)
            socketio.emit('metrics_update', manager.get_metrics())
            if result:
                return jsonify({"status": "success", "vm_id": vm_id}), 200
            else:
                return jsonify({"status": "not_found", "vm_id": vm_id}), 404
        except Exception as e:
            print("Error in /api/vms/<vm_id> [DELETE]:", e)
            return jsonify({"status": "error", "error": str(e)}), 400

@app.route("/api/metrics", methods=["GET"])
@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    with REQUEST_TIME.labels(endpoint='/api/metrics', method='GET').time():
        return jsonify(manager.get_metrics())

@app.route("/api/vms", methods=["GET"])
@app.route("/api/vms", methods=["GET"])
def list_vms():
    with REQUEST_TIME.labels(endpoint='/api/vms', method='GET').time():
        return jsonify(manager.get_metrics()["vms"])

@app.route("/api/cloudlets", methods=["GET"])
@app.route("/api/cloudlets", methods=["GET"])
def list_cloudlets():
    with REQUEST_TIME.labels(endpoint='/api/cloudlets', method='GET').time():
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
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "timestamp": time.time()})

def monitoring():
    """Start monitoring stack if it exists."""
    if MONITORING_DIR.exists() and DOCKER_COMPOSE_FILE.exists():
        print("🚀 Starting monitoring stack...")
        print("   - Prometheus: http://localhost:9090")
        start_monitoring_stack()
    else:
        print("ℹ️  Monitoring stack not found. Running without monitoring.")
        if not MONITORING_DIR.exists():
            print(f"   - Missing directory: {MONITORING_DIR}")
        if not DOCKER_COMPOSE_FILE.exists():
            print(f"   - Missing file: {DOCKER_COMPOSE_FILE}")

        sys.exit(1)

if __name__ == '__main__':
    print("🚀 Starting CloudFlash...")
    print("🔗 Access the application at: http://localhost:5000")
    monitoring()

    # Start the background thread for broadcasting metrics
    try:
        metrics_thread = threading.Thread(target=broadcast_metrics_loop, daemon=True)
        metrics_thread.start()
        print("📊 Metrics broadcasting started")
    except Exception as e:
        print(f"⚠️  Failed to start metrics broadcasting: {e}")
        sys.exit(1)

    try:
        socketio.run(app, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error running application: {e}")
        sys.exit(1)