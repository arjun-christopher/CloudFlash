let vmChart, cloudletChart, slaChart;
let logLines = [];

function addLog(msg) {
    const now = new Date().toLocaleTimeString();
    logLines.unshift(`[${now}] ${msg}`);
    if (logLines.length > 50) logLines = logLines.slice(0, 50);
    document.getElementById('systemLog').innerHTML = logLines.join('<br>');
}

function showSuccessPopup(msg) {
    const popup = document.getElementById('successPopup');
    const popupMsg = document.getElementById('successPopupMsg');
    popupMsg.textContent = msg;
    popup.style.display = 'flex';
    setTimeout(() => {
        popup.style.display = 'none';
    }, 1800);
}

function showErrorPopup(message) {
    const popup = document.getElementById('successPopup');
    const msg = document.getElementById('successPopupMsg');
    msg.innerText = message;
    popup.style.display = 'block';
    popup.style.background = '#fff';
    popup.style.border = '2px solid #e53935';
    popup.style.color = '#1976d2';
    popup.style.boxShadow = '0 4px 32px #1976d244';
    setTimeout(() => {
        popup.style.display = 'none';
        popup.style.background = '';
        popup.style.border = '';
        popup.style.color = '';
    }, 2000);
}

function createVM() {
    const vmData = {
        cpu: parseInt(document.getElementById('vmCpu').value),
        ram: parseInt(document.getElementById('vmRam').value),
        storage: parseInt(document.getElementById('vmStorage').value),
        bandwidth: parseInt(document.getElementById('vmBandwidth').value),
        gpu: parseInt(document.getElementById('vmGpu').value),
        firewall_enabled: document.getElementById('vmFirewall').checked,
        isolation_level: document.getElementById('vmIsolation').value
    };

    fetch('/api/vms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(vmData)
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            const ramUnit = document.getElementById('vmRamUnit').options[document.getElementById('vmRamUnit').selectedIndex].text;
            const storageUnit = document.getElementById('vmStorageUnit').options[document.getElementById('vmStorageUnit').selectedIndex].text;
            addLog(`VM created: ${data.vm_id} [${vmData.cpu} CPU, ${document.getElementById('vmRam').value} ${ramUnit} RAM, ${document.getElementById('vmStorage').value} ${storageUnit} Storage, ${vmData.bandwidth} Mbps Bandwidth, ${vmData.gpu} GPU]`);
            showSuccessPopup('VM created successfully!');
        } else {
            addLog(`Error creating VM: ${data.error}`);
        }
    });
}

function submitCloudlet() {
    const name = document.getElementById('cloudletName').value;
    const cpu = document.getElementById('cloudletCpu').value;
    const ram = document.getElementById('cloudletRam').value * document.getElementById('cloudletRamUnit').value;
    const storage = document.getElementById('cloudletStorage').value * document.getElementById('cloudletStorageUnit').value;
    const bandwidth = document.getElementById('cloudletBandwidth').value;
    const gpu = document.getElementById('cloudletGpu').value;
    const ramUnit = document.getElementById('cloudletRamUnit').options[document.getElementById('cloudletRamUnit').selectedIndex].text;
    const storageUnit = document.getElementById('cloudletStorageUnit').options[document.getElementById('cloudletStorageUnit').selectedIndex].text;
    const sla_priority = document.getElementById('cloudletSLA').value;
    const deadline = parseFloat(document.getElementById('cloudletDeadline').value);
    const execution_time = parseFloat(document.getElementById('cloudletExecTime').value);
    
    // Validate that execution time doesn't exceed deadline
    if (execution_time > deadline) {
        showErrorPopup('Error: Execution time cannot exceed the deadline');
        addLog(`Error: Execution time (${execution_time}s) cannot exceed deadline (${deadline}s)`);
        return;
    }
    
    fetch('/api/cloudlets', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, cpu, ram, storage, bandwidth, gpu, sla_priority, deadline, execution_time})
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            addLog(`Cloudlet submitted: ${data.cloudlet_id} [${cpu} CPU, ${document.getElementById('cloudletRam').value} ${ramUnit} RAM, ${document.getElementById('cloudletStorage').value} ${storageUnit} Storage, ${bandwidth} Mbps Bandwidth, ${gpu} GPU, SLA ${sla_priority}, Deadline ${deadline}s, Exec Time ${execution_time}s]`);
            showSuccessPopup('Cloudlet submitted successfully!');
        } else {
            addLog(`Error submitting cloudlet: ${data.error}`);
        }
    });
}

function deleteCloudletById(cloudletId) {
    if (!cloudletId) return;
    if (!confirm('Are you sure you want to delete this cloudlet?')) return;
    fetch(`/api/cloudlets/${cloudletId}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                addLog(`Cloudlet deleted: ${cloudletId}`);
                showSuccessPopup('Cloudlet deleted successfully!');
            } else if (data.status === 'not_found') {
                addLog(`Cloudlet not found: ${cloudletId}`);
                showErrorPopup('Cloudlet not found!');
            } else {
                addLog(`Error deleting cloudlet: ${data.error}`);
                showErrorPopup('Error deleting cloudlet!');
            }
        });
}

function deleteVmById(vmId) {
    if (!vmId) return;
    if (!confirm('Are you sure you want to delete this VM? All running cloudlets on this VM will be deallocated and reallocated if possible.')) return;
    fetch(`/api/vms/${vmId}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                addLog(`VM deleted: ${vmId}`);
                showSuccessPopup('VM deleted successfully!');
            } else if (data.status === 'not_found') {
                addLog(`VM not found: ${vmId}`);
                showErrorPopup('Cannot delete VM: Cloudlets are running on it!');
            } else {
                addLog(`Error deleting VM: ${data.error}`);
                showErrorPopup('Cannot delete VM: Cloudlets are running on it!');
            }
        });
}

function completeCloudletById(cloudletId) {
    if (!cloudletId) return;
    if (!confirm('Mark this cloudlet as completed?')) return;
    fetch('/api/cloudlets/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cloudlet_id: cloudletId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            addLog(`Cloudlet completed: ${cloudletId}`);
            showSuccessPopup('Cloudlet marked as completed!');
        } else {
            addLog(`Error completing cloudlet: ${data.error}`);
            showErrorPopup('Error completing cloudlet!');
        }
    });
}

function updateCharts(metrics) {
    // Update scaling status display
    const scalingStatus = document.getElementById('scalingStatus');
    if (scalingStatus) {
        scalingStatus.textContent = metrics.scaling_status;
        scalingStatus.className = 'scaling-status ' + (metrics.scaling_status === 'Disabled' ? 'disabled' : 'active');
    }
    
    // Update memory metrics if available
    if (metrics.memory) {
        const totalPages = metrics.memory.total_pages || 0;
        const freePages = metrics.memory.free_pages || 0;
        const usedPages = totalPages - freePages;
        const fragmentation = metrics.memory.fragmentation || 0;
        
        // Update metric displays
        document.getElementById('totalPages').textContent = totalPages;
        document.getElementById('freePages').textContent = freePages;
        document.getElementById('fragmentation').textContent = `${fragmentation.toFixed(1)}%`;
        
        // Update memory map visualization
        const memoryMap = document.getElementById('memoryMap');
        if (memoryMap) {
            // Clear existing visualization
            memoryMap.innerHTML = '';
            
            // Create a simplified visualization (max 100 blocks for performance)
            const maxBlocks = 100;
            const scale = Math.max(1, Math.ceil(totalPages / maxBlocks));
            const displayPages = Math.min(maxBlocks, totalPages);
            
            for (let i = 0; i < displayPages; i++) {
                const page = document.createElement('div');
                page.className = 'memory-page';
                
                // Determine if this block represents used or free memory
                const startPage = i * scale;
                const endPage = Math.min((i + 1) * scale, totalPages);
                const freeInThisBlock = Math.max(0, Math.min(freePages - startPage, endPage - startPage));
                const usedInThisBlock = (endPage - startPage) - freeInThisBlock;
                
                if (usedInThisBlock > 0 && freeInThisBlock > 0) {
                    // Partially used block (fragmented)
                    page.classList.add('fragmented');
                    page.title = `Pages ${startPage+1}-${endPage}: ${usedInThisBlock} used, ${freeInThisBlock} free`;
                } else if (usedInThisBlock > 0) {
                    // Fully used block
                    page.classList.add('used');
                    page.title = `Pages ${startPage+1}-${endPage}: Used`;
                } else {
                    // Free block
                    page.classList.add('free');
                    page.title = `Pages ${startPage+1}-${endPage}: Free`;
                }
                
                memoryMap.appendChild(page);
            }
            
            // Add legend if there's enough space
            if (!document.getElementById('memoryLegend')) {
                const legend = document.createElement('div');
                legend.id = 'memoryLegend';
                legend.style.display = 'flex';
                legend.style.justifyContent = 'center';
                legend.style.gap = '12px';
                legend.style.marginTop = '12px';
                legend.style.fontSize = '12px';
                
                const addLegendItem = (color, label) => {
                    const item = document.createElement('div');
                    item.style.display = 'flex';
                    item.style.alignItems = 'center';
                    item.style.gap = '4px';
                    
                    const swatch = document.createElement('div');
                    swatch.style.width = '12px';
                    swatch.style.height = '12px';
                    swatch.style.borderRadius = '2px';
                    swatch.style.backgroundColor = color;
                    
                    item.appendChild(swatch);
                    item.appendChild(document.createTextNode(label));
                    return item;
                };
                
                legend.appendChild(addLegendItem('#4caf50', 'Free'));
                legend.appendChild(addLegendItem('#f44336', 'Used'));
                legend.appendChild(addLegendItem('#ff9800', 'Fragmented'));
                
                memoryMap.parentNode.insertBefore(legend, memoryMap.nextSibling);
            }
        }
    }

    // Update utilization display
    const utilization = metrics.utilization;
    const utilizationDisplay = document.getElementById('utilizationDisplay');
    if (utilizationDisplay) {
        utilizationDisplay.innerHTML = `
            <div class="utilization-item">
                <span>CPU: ${utilization.cpu.toFixed(1)}%</span>
            </div>
            <div class="utilization-item">
                <span>RAM: ${utilization.ram.toFixed(1)}%</span>
            </div>
            <div class="utilization-item">
                <span>Storage: ${utilization.storage.toFixed(1)}%</span>
            </div>
            <div class="utilization-item">
                <span>Average: ${utilization.average.toFixed(1)}%</span>
            </div>
        `;
    }

    if (metrics.scaling) {
        const scalingInfo = document.createElement('div');
        scalingInfo.style = 'margin-top: 10px; font-size: 0.9em; color: #333;';
        const nextScaleTime = new Date(metrics.scaling.next_possible_scale * 1000).toLocaleTimeString();
        scalingInfo.innerHTML = `
            <strong>Scaling Cooldown:</strong> ${metrics.scaling.adaptive_cooldown.toFixed(1)}s<br>
            <strong>Next Allowed Scale Time:</strong> ${nextScaleTime}
        `;
        document.getElementById('utilizationDisplay')?.appendChild(scalingInfo);
    }    

    // Check if metrics has utilization data
    if (!metrics.utilization) {
        console.warn('No utilization data in metrics:', metrics);
        return;
    }
    const avgUtil = metrics.utilization.average || 0;
    const fill = document.getElementById('avgUtilFill');
    const label = document.getElementById('avgUtilPercent');

    fill.style.width = `${avgUtil.toFixed(1)}%`;
    label.innerText = `${avgUtil.toFixed(1)}%`;

    if (avgUtil < 50) {
        fill.style.background = '#4caf50'; // Green
    } else if (avgUtil < 80) {
        fill.style.background = '#ffb300'; // Amber
    } else {
        fill.style.background = '#e53935'; // Red
    }

    // VM Utilization - Handle case where metrics.vms is undefined
    const vms = metrics.vms || [];
    const vmLabels = vms.length > 0 ? vms.map(vm => `VM-${vm.id ? vm.id.slice(-4) : '?'}`) : ['No VMs'];
    
    // Helper function to safely calculate utilization
    const calculateUtilization = (used, capacity) => {
        if (used === undefined || capacity === undefined || capacity === 0) return 0;
        return (used / capacity) * 100;
    };
    
    const cpu = vms.length > 0 ? vms.map(vm => calculateUtilization(vm.cpu_used, vm.cpu_capacity)) : [0];
    const ram = vms.length > 0 ? vms.map(vm => calculateUtilization(vm.ram_used, vm.ram_capacity)) : [0];
    const storage = vms.length > 0 ? vms.map(vm => calculateUtilization(vm.storage_used, vm.storage_capacity)) : [0];
    const bandwidth = vms.length > 0 ? vms.map(vm => calculateUtilization(vm.bandwidth_used, vm.bandwidth_capacity)) : [0];
    const gpu = vms.length > 0 ? vms.map(vm => calculateUtilization(vm.gpu_used, vm.gpu_capacity)) : [0];

    if (!vmChart) {
        vmChart = new Chart(document.getElementById('vmChart'), {
            type: 'bar',
            data: {
                labels: vmLabels,
                datasets: [
                    { label: 'CPU %', data: cpu, backgroundColor: '#1976d2' },
                    { label: 'RAM %', data: ram, backgroundColor: '#64b5f6' },
                    { label: 'Storage %', data: storage, backgroundColor: '#90caf9' },
                    { label: 'Bandwidth %', data: bandwidth, backgroundColor: '#a5d6a7' },
                    { label: 'GPU %', data: gpu, backgroundColor: '#ce93d8' }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Utilization %'
                        }
                    }
                }
            }
        });
    } else {
        vmChart.data.labels = vmLabels;
        vmChart.data.datasets[0].data = cpu;
        vmChart.data.datasets[1].data = ram;
        vmChart.data.datasets[2].data = storage;
        vmChart.data.datasets[3].data = bandwidth;
        vmChart.data.datasets[4].data = gpu;
        vmChart.update();
    }

    // Cloudlet Status - Initialize with default values if cloudlets is not defined
    const cloudlets = metrics.cloudlets || [];
    const statusCounts = { WAITING: 0, PENDING: 0, ACTIVE: 0, COMPLETED: 0, FAILED: 0 };
    
    // Only try to process if we have cloudlets
    if (Array.isArray(cloudlets)) {
        cloudlets.forEach(cl => {
            if (cl && cl.status) {
                statusCounts[cl.status] = (statusCounts[cl.status] || 0) + 1;
            }
        });
    }

    if (!cloudletChart) {
        cloudletChart = new Chart(document.getElementById('cloudletChart'), {
            type: 'doughnut',
            data: {
                labels: Object.keys(statusCounts).map(label => label.charAt(0).toUpperCase() + label.slice(1).toLowerCase()),
                datasets: [{ data: Object.values(statusCounts), backgroundColor: ['#1976d2', '#64b5f6', '#90caf9', '#43a047', '#e53935'] }]
            }
        });
    } else {
        cloudletChart.data.datasets[0].data = Object.values(statusCounts);
        cloudletChart.update();
    }

    // SLA Compliance (percentage of completed cloudlets before deadline)
    const completed = cloudlets.filter(cl => cl.status === 'COMPLETED');
    const slaMet = completed.filter(cl => cl.completion_time && cl.completion_time <= cl.deadline).length;
    const slaMissed = completed.length - slaMet;
    if (!slaChart) {
        slaChart = new Chart(document.getElementById('slaChart'), {
            type: 'pie',
            data: {
                labels: ['SLA Met', 'SLA Missed'],
                datasets: [{ data: [slaMet, slaMissed], backgroundColor: ['#1976d2', '#e53935'] }]
            }
        });
    } else {
        slaChart.data.datasets[0].data = [slaMet, slaMissed];
        slaChart.update();
    }

    // Update VM Table
    const vmTableBody = document.getElementById('vmTable')?.querySelector('tbody');
    if (vmTableBody) {
        vmTableBody.innerHTML = '';
    metrics.vms.forEach(vm => {
        vmTableBody.innerHTML += `
            <tr>
                <td><span title="${vm.id}">${vm.id.slice(0,8)}</span></td>
                <td>${vm.cpu_capacity}</td>
                <td>${vm.ram_capacity}</td>
                <td>${vm.storage_capacity}</td>
                <td>${vm.bandwidth_capacity}</td>
                <td>${vm.gpu_capacity}</td>
                <td>${vm.status.charAt(0).toUpperCase() + vm.status.slice(1).toLowerCase()}</td>
                <td><button onclick="deleteVmById('${vm.id}')" style="color:#fff;background:#e53935;border:none;padding:2px 8px;border-radius:4px;cursor:pointer;">Delete</button></td>
            </tr>
        `;
    });
    }

    // Update Cloudlet Table
    const cloudletTableBody = document.getElementById('cloudletTable')?.querySelector('tbody');
    if (cloudletTableBody) {
        cloudletTableBody.innerHTML = '';
    metrics.cloudlets.forEach(cl => {
        let actions = `<button onclick="deleteCloudletById('${cl.id}')" style="color:#fff;background:#e53935;border:none;padding:2px 8px;border-radius:4px;cursor:pointer;">Delete</button>`;
        if (cl.status === 'ACTIVE') {
            actions = `<button onclick="completeCloudletById('${cl.id}')" style="color:#fff;background:#43a047;border:none;padding:2px 8px;margin-right:6px;border-radius:4px;cursor:pointer;">Complete</button>` + actions;
        }
        
        // Calculate progress and determine color based on SLA priority and time remaining
        let progressBar = '';
        let progressText = '';
        
        if (cl.status === 'COMPLETED' || cl.status === 'FAILED') {
            // For completed/failed cloudlets, show full green bar
            progressBar = '<div class="progress-bar-container"><div class="progress-bar" style="width: 100%; background: #4CAF50;"></div></div>';
            progressText = '100%';
        } else if (cl.status === 'ACTIVE' && cl.start_time) {
            const now = Date.now() / 1000; // Current time in seconds
            const startTime = parseFloat(cl.start_time);
            let progress = 0;
            let timeLeft = 0;
            let color = '#4CAF50'; // Default green
            
            // Get execution time from cloudlet (default to 30s if not provided)
            const executionTime = parseFloat(cl.execution_time) || 30;
            
            // Calculate progress based on time elapsed since start
            const elapsed = Math.max(0, now - startTime);
            progress = Math.min(100, (elapsed / executionTime) * 100);
            timeLeft = Math.max(0, executionTime - elapsed);
            
            // Get SLA priority (default to 2 if not provided)
            const slaPriority = parseInt(cl.sla_priority) || 2;
            
            // Calculate time percentage remaining
            const timePercentage = ((executionTime - elapsed) / executionTime) * 100;
            
            // Determine color based on SLA priority and time remaining
            if (timePercentage < 20) {
                color = slaPriority >= 3 ? '#f44336' : '#ff9800'; // Red for high priority, orange for others
            } else if (timePercentage < 50) {
                color = slaPriority >= 2 ? '#ff9800' : '#4CAF50'; // Orange for medium/high, green for low
            }
            
            progressBar = `
                <div class="progress-bar-container" title="${Math.round(progress)}% complete (${timeLeft.toFixed(1)}s remaining)">
                    <div class="progress-bar" style="width: ${progress}%; background: ${color};">
                        <span class="progress-text">${Math.round(progress)}%</span>
                    </div>
                </div>
            `;
            progressText = `${Math.round(progress)}%`;
        } else {
            progressBar = '<div class="progress-bar-container"><div class="progress-bar" style="width: 0%; background: #9e9e9e;"></div></div>';
            progressText = '0%';
        }
        
        cloudletTableBody.innerHTML += `
            <tr style="${cl.time_critical && cl.status !== 'COMPLETED' ? 'color: red; font-weight: bold; text-shadow: 0 0 3px red;' : ''}">
                <td>${cl.name}</td>
                <td>${cl.vm_id ? cl.vm_id.slice(0,8) : 'N/A'}</td>
                <td>${cl.cpu}</td>
                <td>${cl.ram}</td>
                <td>${cl.storage}</td>
                <td>${cl.bandwidth}</td>
                <td>${cl.gpu}</td>
                <td>${cl.status.charAt(0).toUpperCase() + cl.status.slice(1).toLowerCase()}</td>
                <td>${progressBar}</td>
                <td>${actions}</td>
            </tr>
        `;
    });
    }

    // Show auto-scaling status
    let autoscale = metrics.auto_scaling ? 'Enabled' : 'Disabled';
    document.getElementById('autoscaleStatus')?.remove();
    const dash = document.querySelector('.dashboard');
    if (dash) {
        const statusDiv = document.createElement('div');
        statusDiv.id = 'autoscaleStatus';
        statusDiv.style = 'text-align:center;margin:12px 0;font-weight:bold;color:#1976d2;';
        statusDiv.innerText = `Auto-Scaling: ${autoscale}`;
        dash.prepend(statusDiv);
    }
}

// --- Load Balancing Functions ---
function updateLoadBalancing() {
    const algorithm = document.getElementById('lbAlgorithm').value;
    
    fetch('/api/settings/algorithm', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ algorithm: algorithm })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            document.getElementById('currentAlgorithm').textContent = 
                `Current: ${algorithm.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}`;
            showSuccessPopup(`Load balancing algorithm updated to: ${algorithm.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}`);
        } else {
            showErrorPopup(data.message || 'Failed to update algorithm');
        }
    })
    .catch(error => {
        console.error('Error updating algorithm:', error);
        showErrorPopup('Failed to update load balancing algorithm');
    });
}

// Initialize the current algorithm display
function initLoadBalancing() {
    try {
        const lbAlgorithmEl = document.getElementById('lbAlgorithm');
        const currentAlgorithmEl = document.getElementById('currentAlgorithm');
        
        // Only proceed if elements exist
        if (!lbAlgorithmEl || !currentAlgorithmEl) {
            console.warn('Load balancing UI elements not found');
            return false;
        }
        
        fetch('/api/settings/algorithm')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data && data.current_algorithm) {
                    lbAlgorithmEl.value = data.current_algorithm;
                    currentAlgorithmEl.textContent = 
                        `Current: ${data.current_algorithm.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}`;
                    console.log('Load balancing algorithm initialized:', data.current_algorithm);
                } else {
                    console.warn('No current algorithm found in response');
                }
                return true;
            })
            .catch(error => {
                console.error('Error loading algorithm settings:', error);
                return false;
            });
            
        return true; // Elements exist, initialization started
    } catch (error) {
        console.error('Error in initLoadBalancing:', error);
        return false;
    }
}

// --- Socket.IO Real-Time Updates ---
const socket = io();
socket.on('metrics_update', (metrics) => {
    updateCharts(metrics);
});

socket.on('system_log', ({ log }) => {
    addLog(log);
});

function applyPreset() {
    const preset = document.getElementById('vmPreset').value;
    if (preset === 'small') {
        document.getElementById('vmCpu').value = 2;
        document.getElementById('vmRam').value = 4;
        document.getElementById('vmRamUnit').value = 1; // GB
        document.getElementById('vmStorage').value = 40;
        document.getElementById('vmStorageUnit').value = 1; // GB
        document.getElementById('vmBandwidth').value = 500;
        document.getElementById('vmGpu').value = 0;
    } else if (preset === 'medium') {
        document.getElementById('vmCpu').value = 4;
        document.getElementById('vmRam').value = 8;
        document.getElementById('vmRamUnit').value = 1;
        document.getElementById('vmStorage').value = 100;
        document.getElementById('vmStorageUnit').value = 1;
        document.getElementById('vmBandwidth').value = 1000;
        document.getElementById('vmGpu').value = 1;
    } else if (preset === 'large') {
        document.getElementById('vmCpu').value = 8;
        document.getElementById('vmRam').value = 16;
        document.getElementById('vmRamUnit').value = 1;
        document.getElementById('vmStorage').value = 200;
        document.getElementById('vmStorageUnit').value = 1;
        document.getElementById('vmBandwidth').value = 2000;
        document.getElementById('vmGpu').value = 2;
    }
}

function applyCloudletPreset() {
    const preset = document.getElementById('cloudletPreset').value;
    if (preset === 'light') {
        document.getElementById('cloudletCpu').value = 1;
        document.getElementById('cloudletRam').value = 2;
        document.getElementById('cloudletRamUnit').value = 1;
        document.getElementById('cloudletStorage').value = 5;
        document.getElementById('cloudletStorageUnit').value = 1;
        document.getElementById('cloudletBandwidth').value = 100;
        document.getElementById('cloudletGpu').value = 0;
        document.getElementById('cloudletSLA').value = 2;
        document.getElementById('cloudletDeadline').value = 60;
    } else if (preset === 'moderate') {
        document.getElementById('cloudletCpu').value = 2;
        document.getElementById('cloudletRam').value = 4;
        document.getElementById('cloudletRamUnit').value = 1;
        document.getElementById('cloudletStorage').value = 10;
        document.getElementById('cloudletStorageUnit').value = 1;
        document.getElementById('cloudletBandwidth').value = 200;
        document.getElementById('cloudletGpu').value = 0;
        document.getElementById('cloudletSLA').value = 2;
        document.getElementById('cloudletDeadline').value = 90;
    } else if (preset === 'heavy') {
        document.getElementById('cloudletCpu').value = 4;
        document.getElementById('cloudletRam').value = 8;
        document.getElementById('cloudletRamUnit').value = 1;
        document.getElementById('cloudletStorage').value = 20;
        document.getElementById('cloudletStorageUnit').value = 1;
        document.getElementById('cloudletBandwidth').value = 500;
        document.getElementById('cloudletGpu').value = 1;
        document.getElementById('cloudletSLA').value = 3;
        document.getElementById('cloudletDeadline').value = 120;
    }
}

// Function to initialize the application
function initializeApp() {
    try {
        console.log('Initializing application...');
        
        // Initialize load balancing UI
        const lbInitSuccess = initLoadBalancing();
        console.log('Load balancing initialization:', lbInitSuccess ? 'success' : 'elements not found');
        
        // Initial chart update with minimal metrics and all required properties
        updateCharts({ 
            utilization: { average: 0 },
            vms: [],
            cloudlets: [],
            active_cloudlets: 0,
            completed_cloudlets: 0,
            failed_cloudlets: 0,
            pending_cloudlets: 0,
            waiting_cloudlets: 0,
            active_vms: 0,
            total_vms: 0,
            total_cloudlets: 0,
            sla_violations: 0
        });
        
        // Request initial metrics from the server
        fetch('/api/metrics')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(metrics => {
                console.log('Received initial metrics:', metrics);
                if (metrics) {
                    updateCharts(metrics);
                }
            })
            .catch(error => {
                console.error('Error fetching initial metrics:', error);
            });
            
        // Set up socket.io connection for real-time updates
        const socket = io();
        socket.on('connect', () => {
            console.log('Connected to server via Socket.IO');
        });
        
        socket.on('metrics_update', (metrics) => {
            console.log('Received metrics update:', metrics);
            updateCharts(metrics);
        });
        
        socket.on('system_log', ({ log }) => {
            addLog(log);
        });
        
    } catch (error) {
        console.error('Error during initialization:', error);
    }
}

// Check if the DOM is already loaded
if (document.readyState === 'loading') {
    // Loading hasn't finished yet, wait for the 'DOMContentLoaded' event
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    // DOM is already ready, initialize immediately
    initializeApp();
}