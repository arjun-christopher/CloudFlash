# 🌩️ CloudFlash - Mini-Project

A cloud resource management system with real-time monitoring, auto-scaling capabilities, and comprehensive observability using Prometheus and Grafana.

## Features

### VM Management
- Create and delete virtual machines
- Configure VM resources (CPU, RAM, Storage, Bandwidth, GPU)
- Monitor VM status and resource utilization

### Cloudlet Management
- Submit and manage cloudlets (compute tasks)
- Set SLA priorities and deadlines
- Track cloudlet status and resource usage

### Real-time Monitoring & Observability
- Live dashboard with resource utilization metrics
- CPU, RAM, storage, bandwidth, and GPU usage visualization
- Auto-scaling status monitoring
- Cloudlet deadline countdown
- Integration with Prometheus and Grafana
- Per-VM resource tracking
- Historical metrics and trends

### Auto-scaling
- Automatic VM scaling based on resource utilization
- Scale up when utilization exceeds 80%
- Scale down when utilization drops below 20%
- Cooldown period to prevent rapid scaling
- Idle VM removal after 2 minutes of inactivity

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

### Monitoring Stack Setup
1. Navigate to the monitoring directory:
   ```bash
   cd cloudflash/monitoring
   ```
2. Start the monitoring stack:
   ```bash
   docker-compose -f docker-compose.monitoring.yml up -d
   ```
3. Access the monitoring tools:
   - **Grafana Dashboard**: http://localhost:3000
     - Username: `admin`
     - Password: `admin`
   - **Prometheus**: http://localhost:9090
   - **CloudFlash App**: http://localhost:5000

## Dashboard Overview

The CloudFlash monitoring dashboard includes the following panels:
1. **Active VMs** - Shows the current number of running VMs
2. **Active Cloudlets** - Shows the current number of active cloudlets
3. **CPU Usage by VM** - Tracks CPU usage for each VM
4. **Memory Usage by VM** - Tracks memory usage for each VM
5. **Bandwidth Usage by VM** - Tracks network bandwidth usage
6. **GPU Usage by VM** - Tracks GPU utilization (if available)

## Usage

### VM Management
- Create VMs through the dashboard interface
- Configure resources (CPU, RAM, Storage, Bandwidth, GPU)
- Monitor VM status and resource usage
- Delete idle VMs

### Cloudlet Management
- Submit cloudlets with resource requirements
- Set SLA priorities (1-3)
- Define deadlines for cloudlets
- Monitor cloudlet status and progress

## Customizing Metrics

### Adding New Metrics
1. In `app.py`:
   ```python
   from prometheus_client import Gauge
   
   # Define a new gauge
   CUSTOM_METRIC = Gauge('custom_metric', 'Description of the custom metric')
   
   # Update the metric value
   CUSTOM_METRIC.set(42)
   ```

### Updating the Dashboard
1. Access Grafana at http://localhost:3000
2. Navigate to the CloudFlash dashboard
3. Click on the panel title and select "Edit"
4. Modify the query or visualization as needed
5. Click "Save" to update the dashboard

## Troubleshooting

### Metrics not showing up in Prometheus
- Ensure the CloudFlash app is running and accessible
- Check the Prometheus targets page at http://localhost:9090/targets
- Verify the `prometheus.yml` configuration points to the correct host and port

### Grafana not showing data
- Check that the Prometheus data source is correctly configured in Grafana
- Verify the time range in the dashboard is appropriate
- Check the Grafana logs for any errors

### High resource usage
- The monitoring stack can be resource-intensive
- Consider adjusting the scrape interval in `prometheus.yml`
- Reduce the retention period for metrics in Prometheus if needed

## Cleaning Up

To stop and remove the monitoring stack:
```bash
cd cloudflash/monitoring
docker-compose -f docker-compose.monitoring.yml down -v
```

This will remove the containers and volumes but keep your configuration files.

## Technical Details

- **Backend**: Python Flask with SocketIO for real-time updates
- **Frontend**: HTML5, CSS3, JavaScript
- **Real-time Updates**: WebSocket communication
- **Auto-scaling**: Thread-based monitoring with cooldown periods
- **Resource Allocation**: Best-fit algorithm for cloudlet placement
- **Monitoring**:
  - Prometheus for metrics collection
  - Grafana for visualization
  - Custom metrics for VM and cloudlet resources
  - Health check endpoints at `/health` and `/metrics`

## Last Modified

Last updated: May 24, 2025
