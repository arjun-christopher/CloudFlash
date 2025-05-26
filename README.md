# 🌩️ CloudFlash - Mini-Project

A comprehensive cloud resource management system with real-time monitoring, auto-scaling capabilities, and full observability using Prometheus. CloudFlash provides an intuitive interface for managing virtual machines (VMs) and cloudlets with advanced resource allocation and monitoring features.

## Features

### Virtual Machine Management
- Create and manage virtual machines with custom resource allocations
- Configure CPU, RAM, storage, bandwidth, and GPU resources
- Real-time monitoring of VM performance and health
- Clean up idle resources automatically
- Secure VM creation with:
  - Firewall controls (enabled by default)
  - Resource isolation levels (Standard/Strict)
  - Visual security indicators in the UI

### Cloudlet Management
- Submit compute tasks with specific resource requirements
- Set SLA priorities and execution deadlines
- Track cloudlet lifecycle from submission to completion
- Monitor resource consumption per cloudlet

### Load Balancing
CloudFlash implements intelligent load balancing to distribute cloudlets across available VMs efficiently:

- **Multiple Algorithm Support**:
  - **Round Robin**: Distributes tasks evenly across all VMs in sequence
  - **Least Loaded**: Assigns tasks to the VM with the most available resources
  - **Weighted Round Robin**: Distributes tasks based on VM capacity
  - **Best Fit**: Selects the VM that best fits the cloudlet's requirements

- **Real-time Algorithm Switching**: Change load balancing strategy on-the-fly
- **Resource-Aware Distribution**: Considers CPU, memory, and other resource constraints
- **Visual Feedback**: Current algorithm is clearly displayed in the UI

### Real-time Monitoring & Observability
- **Live Dashboard**: Instant updates via WebSocket
- **Resource Visualization**: CPU, memory, storage, and network
- **Memory Management**: Page-level allocation details
- **Auto-scaling**: Real-time status and event logging
- **Cloudlet Tracking**: Execution progress with countdown timers
- **System Logs**: Centralized logging of all operations
- **Prometheus Integration**: Deep metrics collection and analysis

### Advanced Memory Management
- Dynamic memory allocation with page-level tracking
- Real-time memory fragmentation analysis
- Visual memory map showing page allocation status
- Memory usage patterns and trends
- Automatic defragmentation when fragmentation exceeds thresholds

### Auto-scaling & Optimization
- **Adaptive Cooldown**: Dynamic cooldown periods based on system load
- **Intelligent Scaling**: Scale up at 80% utilization, down at 20%
- **Idle VM Cleanup**: Automatic removal after 1 minute of inactivity
- **Resource Optimization**: Smart allocation based on workload patterns
- **Real-time Metrics**: Live updates of resource utilization
- **Threshold Alerts**: Notifications for critical resource levels

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
1. Start the CloudFlash application with enhanced monitoring:
   ```bash
   python -m cloudflash.app
   ```
2. Access the monitoring dashboards:
   - **CloudFlash Dashboard**: http://localhost:5000
   - **Prometheus UI**: http://localhost:9090 (for advanced queries)
   - **Metrics Endpoint**: http://localhost:5000/metrics
3. Enable real-time updates:
   - The dashboard automatically connects via WebSocket
   - No additional configuration needed for live updates

## Dashboard Overview

The CloudFlash monitoring dashboard provides comprehensive visibility into your cloud resources:

### Resource Overview
- **Active VMs**: Current count and status of running VMs
- **Active Cloudlets**: Number of cloudlets being processed
- **Resource Utilization**: At-a-glance view of CPU, memory, and storage usage

### Detailed Metrics
1. **CPU Usage**
   - Per-VM CPU utilization
   - Historical trends and spikes
   - Load averages

2. **Memory Management**
   - Real-time memory allocation
   - Page-level visualization
   - Fragmentation analysis
   - Usage patterns and forecasting

3. **Network & Storage**
   - Bandwidth usage by VM
   - Storage I/O metrics
   - Network latency and throughput

4. **GPU Monitoring** (when available)
   - GPU utilization
   - Memory usage
   - Temperature and power metrics

5. **System Logs**
   - Real-time event streaming
   - Filterable by severity
   - Search functionality

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

CloudFlash implements intelligent auto-scaling with these features:

#### Scaling Policies
- **Scale Up**: Triggers when resource usage exceeds 80%
- **Scale Down**: Occurs when usage drops below 20%
- **Adaptive Cooldown**: Dynamic cooldown periods based on:
  - Current system load
  - Historical patterns
  - Resource contention levels

#### Resource Management
- **Idle VM Cleanup**: Inactive VMs removed after 1 minute
- **Smart Allocation**: Resources allocated based on:
  - Workload requirements
  - Priority levels
  - Historical usage patterns
- **Fragmentation Control**: Automatic defragmentation when needed

#### Real-time Adjustments
- Continuous monitoring of resource utilization
- Immediate response to workload changes
- Predictive scaling based on trends

Access these metrics through the CloudFlash monitoring dashboard at http://localhost:5000/prometheus

## Getting Started

### Managing Load Balancing

1. **Change Load Balancing Algorithm**:
   - Locate the Load Balancing banner at the top of the dashboard
   - Select your preferred algorithm from the dropdown
   - Click "Update Algorithm" to apply changes
   - The system will immediately start using the new algorithm for all new cloudlet assignments

2. **Monitoring Load Distribution**:
   - View current algorithm in the Load Balancing banner
   - Monitor VM resource usage in real-time
   - Check system logs for load balancing events and decisions

### Creating Virtual Machines
1. Navigate to the VM Creation panel
2. Configure VM resources:
   - CPU Cores (1-32)
   - RAM (1GB-256GB)
   - Storage (10GB-10TB)
   - Bandwidth (10Mbps-10Gbps)
   - GPU Units (optional)
3. Configure security settings:
   - Enable Firewall (default: enabled)
   - Select Isolation Level (Standard/Strict)
4. Click "Create VM" to deploy
5. Monitor resource usage in real-time

#### Security Settings
- **Firewall**: Controls network access to the VM
  - Default: Enabled
  - Protects against unauthorized access
  - Can be disabled for development/testing

- **Isolation Level**: Controls resource separation between VMs
  - **Standard**: Basic resource isolation
    - Prevents VM interference
    - Good performance balance
  - **Strict**: Enhanced security
    - Stronger resource barriers
    - More secure but resource-intensive

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

## Advanced Configuration

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

## Troubleshooting Guide

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

## Technical Architecture

### Backend
- **Framework**: Python Flask with SocketIO
- **Real-time Updates**: WebSocket communication for live metrics
- **API**: RESTful endpoints for resource management
- **Metrics**: Prometheus client integration
- **Health Checks**: Built-in health monitoring at `/health`

### Frontend
- **UI**: Responsive design with modern CSS
- **Load Balancing**: Intuitive controls for algorithm selection and monitoring
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

*Last updated: May 26, 2025*
