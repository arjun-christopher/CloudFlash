# 🌩️ CloudFlash - Mini-Project

A cloud resource management system with real-time monitoring and auto-scaling capabilities.

## Features

- **VM Management**
  - Create and delete virtual machines
  - Configure VM resources (CPU, RAM, Storage, Bandwidth, GPU)
  - Monitor VM status and resource utilization

- **Cloudlet Management**
  - Submit and manage cloudlets (compute tasks)
  - Set SLA priorities and deadlines
  - Track cloudlet status and resource usage

- **Real-time Monitoring**
  - Live dashboard with resource utilization metrics
  - CPU, RAM, and storage usage visualization
  - Auto-scaling status monitoring
  - Cloudlet deadline countdown

- **Auto-scaling**
  - Automatic VM scaling based on resource utilization
  - Scale up when utilization exceeds 80%
  - Scale down when utilization drops below 20%
  - Cooldown period to prevent rapid scaling
  - Idle VM removal after 2 minutes of inactivity

## Setup

1. Install Python dependencies:
```bash
pip install flask flask-socketio
```

2. Run the application:
```bash
python cloudflash/app.py
```

3. Open your browser and navigate to `http://localhost:5000`

## Usage

1. **VM Management**
   - Create VMs through the dashboard interface
   - Configure resources (CPU, RAM, Storage, Bandwidth, GPU)
   - Monitor VM status and resource usage
   - Delete idle VMs

2. **Cloudlet Management**
   - Submit cloudlets with resource requirements
   - Set SLA priorities (1-3)
   - Define deadlines for cloudlets
   - Monitor cloudlet status and progress

3. **Monitoring Dashboard**
   - View real-time resource utilization
   - Monitor auto-scaling status
   - Track cloudlet deadlines and status
   - View VM and cloudlet metrics

## Technical Details

- **Backend**: Python Flask with SocketIO for real-time updates
- **Frontend**: HTML5, CSS3, JavaScript
- **Real-time Updates**: WebSocket communication
- **Auto-scaling**: Thread-based monitoring with cooldown periods
- **Resource Allocation**: Best-fit algorithm for cloudlet placement

## Last Modified

Last updated: May 19, 2025
