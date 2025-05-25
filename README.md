# 🌩️ CloudFlash - Mini-Project

A comprehensive cloud resource management system with real-time monitoring, auto-scaling capabilities, and full observability using Prometheus. CloudFlash provides an intuitive interface for managing virtual machines (VMs) and cloudlets with advanced resource allocation and monitoring features.

## Features

### Virtual Machine Management
- Create and manage virtual machines with custom resource allocations
- Configure CPU, RAM, storage, bandwidth, and GPU resources
- Real-time monitoring of VM performance and health
- Clean up idle resources automatically

### Cloudlet Management
- Submit compute tasks with specific resource requirements
- Set SLA priorities and execution deadlines
- Track cloudlet lifecycle from submission to completion
- Monitor resource consumption per cloudlet

### Real-time Monitoring & Observability
- Interactive dashboard with live metrics
- CPU, memory, storage, and network visualization
- Memory management visualization with page-level details
- Auto-scaling status and alerts
- Cloudlet execution tracking with countdown timers
- Deep integration with Prometheus for monitoring

### Auto-scaling & Optimization
- Automatic scaling based on resource thresholds (80% scale up, 20% scale down)
- Configurable cooldown periods to prevent rapid scaling
- Automatic cleanup of idle VMs after 1 minute (reduced from 2 minutes)
- Resource optimization recommendations
- Memory fragmentation monitoring and visualization

## Setup

### Prerequisites
1. Python 3.7+ with pip
2. Docker and Docker Compose (for monitoring stack)
3. Required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

### Basic Setup
1. Run the application:
   ```bash
   python -m cloudflash.app
   ```
2. Open your browser and navigate to `http://localhost:5000`

### Monitoring Setup
1. Start the CloudFlash application:
   ```bash
   python -m cloudflash.app
   ```
2. Access the monitoring dashboard at:
   - **CloudFlash Monitoring**: http://localhost:5000/prometheus
   - **Prometheus UI**: http://localhost:9090 (for advanced queries)

## Dashboard Overview

The CloudFlash monitoring dashboard includes the following panels:

1. **Active VMs** - Shows the current number of running VMs
2. **Active Cloudlets** - Shows the current number of active cloudlets
3. **CPU Usage by VM** - Tracks CPU usage for each VM
4. **Memory Management** - Detailed memory metrics including:
   - Total and free memory pages
   - Memory fragmentation percentage
   - Visual memory map showing page allocation
   - Real-time updates of memory usage patterns
5. **Bandwidth Usage by VM** - Tracks network bandwidth usage
6. **GPU Usage by VM** - Tracks GPU utilization (if available)
7. **System Log** - Real-time log of system events and operations

### Memory Management Panel

The memory management panel provides detailed insights into your system's memory usage:

- **Total Pages**: Total number of memory pages available in the system
- **Free Pages**: Number of currently available memory pages
- **Fragmentation %**: Percentage of memory that is fragmented
- **Memory Map**: Visual representation of memory allocation
  - Green: Free memory
  - Red: Used memory
  - Yellow: Fragmented memory

### Auto-scaling Behavior

- **Scale Up**: Triggers when resource usage exceeds 80%
- **Scale Down**: Occurs when usage drops below 20%
- **Idle VM Cleanup**: Inactive VMs are automatically removed after 1 minute

Access these metrics through the CloudFlash monitoring dashboard at http://localhost:5000/prometheus

## 🚀 Getting Started

### Creating Virtual Machines
1. Navigate to the VM Creation panel
2. Configure VM resources:
   - CPU Cores (1-32)
   - RAM (1GB-256GB)
   - Storage (10GB-10TB)
   - Bandwidth (10Mbps-10Gbps)
   - GPU Units (optional)
3. Click "Create VM" to deploy
4. Monitor resource usage in real-time

### Submitting Cloudlets
1. Go to the Cloudlet Submission panel
2. Enter cloudlet details:
   - Name (for identification)
   - Resource requirements
   - SLA Priority (1-3)
   - Deadline (in seconds)
3. Click "Submit Cloudlet" to queue for execution
4. Track progress in the Cloudlet List

### Monitoring Resources
- View real-time metrics in the responsive dashboard
- Monitor memory usage with detailed page-level visualization
- Track fragmentation and memory allocation patterns
- Check the system log for events and alerts
- Access detailed metrics in the Prometheus dashboard at http://localhost:5000/prometheus
- Monitor system health at `/health` endpoint

### Auto-scaling
- The system automatically scales based on resource utilization
- Scale-up triggers at 80% resource usage
- Scale-down occurs below 20% utilization
- Idle VMs are automatically removed after 2 minutes

## 🛠️ Advanced Configuration

### Custom Metrics
Add custom metrics to track additional system parameters:

```python
# In app.py
from prometheus_client import Gauge, Counter, Histogram

# Example: Track custom application metrics
CUSTOM_METRIC = Gauge('app_custom_metric', 'Description of your custom metric')
REQUEST_COUNTER = Counter('app_requests_total', 'Total number of requests')
LATENCY_HISTOGRAM = Histogram('app_request_latency_seconds', 'Request latency in seconds')

# Update metrics in your route handlers
@app.route('/api/endpoint')
def my_endpoint():
    start_time = time.time()
    # Your endpoint logic here
    LATENCY_HISTOGRAM.observe(time.time() - start_time)
    REQUEST_COUNTER.inc()
    return jsonify({"status": "success"})
```

### Prometheus Customization
1. **Access Prometheus**: http://localhost:9090
   - Use PromQL queries to visualize metrics
   - Example: `rate(cloudflash_http_requests_total[5m])`

### Alert Configuration
1. **In Prometheus**:
   - Create alert rules in prometheus.yml
   - Set up notification channels (Email, Slack, etc.)

2. **Example Alert Rules**:
   - High CPU usage: `avg(rate(cloudflash_cpu_usage_percent[5m])) by (instance) > 80`
   - Memory pressure: `avg(cloudflash_memory_usage_bytes / cloudflash_memory_total_bytes * 100) by (instance) > 75`

## 🐛 Troubleshooting Guide

### Monitoring Issues

#### Prometheus Not Scraping Metrics
```
# Check Prometheus targets
http://localhost:9090/targets

# Verify CloudFlash is listed as UP
# If DOWN, check:
# 1. Is the app running? (http://localhost:5000/health)
# 2. Are the host and port correct in prometheus.yml?
# 3. Is there a firewall blocking the connection?
```

#### Prometheus Issues
1. **No Data in Graphs**
   - Check the time range selector (top-right)
   - Verify the PromQL query is correct
   - Check for errors in the Prometheus logs:
     ```bash
     docker logs $(docker ps -q --filter name=prometheus)
     ```

### Application Issues

#### High Resource Usage
```yaml
# In monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s  # Increase to reduce load
  evaluation_interval: 15s
  scrape_timeout: 10s
```

#### Monitoring Stack Not Starting
1. Check Docker logs:
   ```bash
   cd cloudflash/monitoring
   docker-compose -f docker-compose.monitoring.yml logs
   ```

2. Verify Docker is running:
   ```bash
   docker info
   ```

3. Check port conflicts:
   ```bash
   # Linux/macOS
   lsof -i :3000 -i :9090 -i :5000
   
   # Windows
   netstat -ano | findstr "3000 9090 5000"
   ```

### Common Errors
- **"Connection refused" errors**: Ensure all services are running and ports are available
- **Missing metrics**: Verify metrics are being exposed at `/metrics`
- **Permission issues**: Run Docker commands with appropriate permissions

For additional help, please [open an issue](https://github.com/yourusername/CloudFlash/issues) with details about your environment and the error messages you're seeing.

## Cleaning Up

To stop and remove the monitoring stack:
```bash
cd cloudflash/monitoring
docker-compose -f docker-compose.monitoring.yml down -v
```

This will remove the containers and volumes but keep your configuration files.

## 🛠️ Technical Architecture

### Backend
- **Framework**: Python Flask with SocketIO
- **Real-time Updates**: WebSocket communication for live metrics
- **API**: RESTful endpoints for resource management
- **Metrics**: Prometheus client integration
- **Health Checks**: Built-in health monitoring at `/health`

### Frontend
- **UI**: Responsive design with modern CSS
- **Visualization**: Dynamic charts using Chart.js
- **Real-time Updates**: Automatic refresh of metrics and status

### Monitoring Stack
- **Prometheus**: Metrics collection, visualization, and alerting
- **Custom Metrics**:
  - VM resource usage
  - Cloudlet execution metrics
  - System health indicators
  - Auto-scaling events

### Resource Management
- **VM Management**: Create, monitor, and scale virtual machines
- **Cloudlet Scheduler**: Intelligent task allocation
- **Auto-scaling**: Dynamic resource adjustment based on load

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- Flask and Flask-SocketIO for the web framework
- Prometheus for monitoring and metrics
- Chart.js for visualizations

---

Last updated: May 25, 2025