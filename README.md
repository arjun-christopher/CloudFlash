# 🌩️ CloudFlash - Mini-Project

A comprehensive cloud resource management system with real-time monitoring, auto-scaling capabilities, and full observability using Prometheus. CloudFlash provides an intuitive interface for managing virtual machines (VMs) and cloudlets with advanced resource allocation, security controls, and monitoring features.

## Features

### Virtual Machine Management
- Create and manage virtual machines with custom resource allocations
- Configure CPU, RAM, storage, bandwidth, and GPU resources
- Real-time monitoring of VM performance and health
- Clean up idle resources automatically
- Preset configurations for quick VM setup (Small, Medium, Large)
- Secure VM creation with:
  - Firewall controls (enabled by default)
  - Resource isolation levels (Standard/Strict)
  - Visual security indicators in the UI
  - Dynamic security controls based on isolation level

### Cloudlet Management
- Submit compute tasks with specific resource requirements
- Set SLA priorities and execution deadlines
- Track cloudlet lifecycle from submission to completion with real-time progress tracking
- Monitor resource consumption per cloudlet
- Preset configurations for common cloudlet types (Small, Medium, Large, GPU-Intensive, Memory-Intensive)
- Visual progress indicators with SLA-based coloring:
  - **Green**: On track with SLA (more than 50% of execution time remaining)
  - **Orange**: Approaching deadline (20-50% of execution time remaining for medium/high priority, or <20% for low priority)
  - **Red**: Critical (less than 20% of execution time remaining for high priority)
- Progress bar shows completion percentage and time remaining (240px wide for better visibility)
- Automatic status updates as cloudlets progress through their lifecycle
- Detailed logging for cloudlet lifecycle:
  - [STARTED]: When cloudlet begins execution
  - [ALLOCATED]: When cloudlet is assigned to a VM
  - [COMPLETED]: When cloudlet finishes execution
  - [DEADLINE MISSED]: When cloudlet fails to complete on time
  - [SLA ESCALATED]: When cloudlet's priority is increased due to time constraints
  - [SLA WARNING]: When cloudlet is approaching its deadline
- Input validation to prevent invalid configurations (e.g., execution time exceeding deadline)

### Load Balancing
CloudFlash implements intelligent load balancing to distribute cloudlets across available VMs efficiently:

- **Multiple Algorithm Support**:
  - **Round Robin**: Distributes tasks evenly across all VMs in sequence
  - **Least Loaded**: Assigns tasks to the VM with the most available resources
  - **Weighted Round Robin**: Distributes tasks based on VM capacity
  - **Best Fit**: Selects the VM that best fits the cloudlet's requirements

- **Real-time Algorithm Switching**: Change load balancing strategy on-the-fly with immediate effect
- **Resource-Aware Distribution**: Considers CPU, memory, GPU, and other resource constraints
- **Visual Feedback**: Current algorithm is clearly displayed in the UI with visual indicators
- **Dynamic Adjustment**: Automatically adjusts distribution based on real-time system load
- **Algorithm Persistence**: Remembers the selected algorithm across page refreshes

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
- **Predictive Scaling**: Advanced machine learning-based scaling decisions
  - Uses historical resource usage patterns to forecast future needs
  - Triggers scaling based on predicted resource utilization
  - Checks every 40 seconds with 5 data points for accurate predictions
  - Maximum 10 predictive VMs per system
  - Prevents over-provisioning by capping VM count
  - Scale-up prevented when max VM limit is reached
- **Resource Thresholds**:
  - CPU: Scale up when predicted usage > 80%
  - RAM: Scale up when predicted usage > 75%
  - Storage: Scale up when predicted usage > 85%
  - Bandwidth: Scale up when predicted usage > 80%
- **New VM Configuration**:
  - 4 CPU cores
  - 8GB RAM
  - 100GB Storage
  - 1000Mbps Bandwidth
  - 1 GPU unit
- **Smart Allocation**: Resources allocated based on:
  - Workload requirements
  - Priority levels
  - Historical usage patterns
- **Real-time Metrics**: Live updates of resource utilization
- **Threshold Alerts**: Notifications for critical resource levels

## User Interface

### Enhanced UX Features
- **Responsive Design**: Works on desktop and tablet devices
- **Visual Feedback**: Clear status indicators and progress bars
- **Success/Error Notifications**: Non-intrusive popup notifications for user actions
- **Input Validation**: Prevents invalid configurations before submission
- **Security-First Approach**: Clear visual indicators for security settings

### Security Features
- **Firewall Protection**: Enable/disable firewall per VM
- **Resource Isolation**: Choose between Standard and Strict isolation levels
- **Visual Security Indicators**: Clear indication of security status
- **Secure Defaults**: Security features enabled by default

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

#### Predictive Scaling
- **Resource Forecast**: Uses machine learning models to predict future resource needs
- **Training Data**: Collects historical usage patterns every 20 seconds
- **Prediction Window**: Uses 5 data points for accurate predictions
- **Decision Making**: Makes scaling decisions based on predicted resource utilization

#### Scaling Policies
- **Scale Up**: Triggers when predicted resource usage exceeds thresholds:
  - CPU: 80%
  - RAM: 75%
  - Storage: 85%
  - Bandwidth: 80%
- **New VM Specification**:
  - 4 CPU cores
  - 8GB RAM
  - 100GB Storage
  - 1000Mbps Bandwidth
  - 1 GPU unit

#### Real-time Adjustments
- Continuous monitoring of resource utilization
- Immediate response to workload changes
- Predictive scaling based on historical trends
- Detailed logging of scaling operations

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

### Auto-scaling & Resource Management

#### Scaling Behavior
- **Scale-up**: Triggers when resource usage exceeds 80%
  - Adaptive cooldown between 3-10 seconds based on utilization patterns
  - Minimum 3-second cooldown during high utilization spikes
  - Maximum 10-second cooldown during stable periods

- **Scale-down**: Occurs when utilization drops below 20%
  - Only removes one VM at a time to prevent over-scaling
  - Respects the same cooldown periods as scale-up

#### Idle VM Management
- **Idle VM Termination**: VMs are automatically removed after 40 seconds of inactivity
  - A VM is considered idle when it has no running cloudlets
  - Last activity time is tracked for each VM
  - Memory is properly deallocated before VM termination
  - Ensures efficient resource utilization by removing underutilized instances

#### VM Consolidation & Migration
- **Automatic VM Consolidation**:
  - Runs periodically to identify underutilized VMs
  - Targets VMs with 2 or fewer cloudlets
  - Migrates cloudlets to more suitable VMs when possible
  - Removes empty VMs after successful migration

- **Live Migration Process**:
  1. Identifies underutilized VMs
  2. For each cloudlet on the VM:
     - Finds a suitable target VM using the current load balancing algorithm
     - Migrates the cloudlet if a better target is found
     - Rolls back if migration fails
  3. Removes the source VM if empty after migration

- **Migration Safety**:
  - Uses locking to ensure thread safety
  - Maintains cloudlet state during migration
  - Preserves execution context (restarts timers if needed)
  - Logs all migration attempts and rollbacks

#### Monitoring & Logging
- Real-time resource utilization tracking
- Detailed logging of all scaling and migration events
- Adaptive cooldown periods based on system load
- Consolidated logging to prevent duplicate entries

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

*Last updated: May 28, 2025*
