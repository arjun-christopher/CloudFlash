import threading
import uuid
import time
from enum import Enum, auto
from collections import deque

# --- ENUMS AND CONSTANTS ---

class CloudletStatus(Enum):
    WAITING = auto()
    PENDING = auto()
    ACTIVE = auto()
    COMPLETED = auto()
    FAILED = auto()

class VMStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    SCALING = auto()
    TERMINATED = auto()

# --- VM CLASS ---

class VM:
    def __init__(self, cpu, ram, storage, bandwidth=1000, gpu=0):
        self.id = str(uuid.uuid4())
        self.cpu_capacity = cpu
        self.ram_capacity = ram
        self.storage_capacity = storage
        self.bandwidth_capacity = bandwidth  # Mbps
        self.gpu_capacity = gpu
        self.cpu_used = 0
        self.ram_used = 0
        self.storage_used = 0
        self.bandwidth_used = 0
        self.gpu_used = 0
        self.status = VMStatus.IDLE
        self.lock = threading.Lock()
        self.last_activity = time.time()
        self.cloudlets = set()

    def can_allocate(self, cpu, ram, storage, bandwidth=0, gpu=0):
        return (
            self.cpu_capacity - self.cpu_used >= cpu and
            self.ram_capacity - self.ram_used >= ram and
            self.storage_capacity - self.storage_used >= storage and
            self.bandwidth_capacity - self.bandwidth_used >= bandwidth and
            self.gpu_capacity - self.gpu_used >= gpu
        )

    def allocate(self, cloudlet):
        with self.lock:
            if self.can_allocate(cloudlet.cpu, cloudlet.ram, cloudlet.storage, cloudlet.bandwidth, cloudlet.gpu):
                self.cpu_used += cloudlet.cpu
                self.ram_used += cloudlet.ram
                self.storage_used += cloudlet.storage
                self.bandwidth_used += cloudlet.bandwidth
                self.gpu_used += cloudlet.gpu
                self.cloudlets.add(cloudlet.id)
                self.status = VMStatus.RUNNING
                self.last_activity = time.time()
                return True
            return False

    def deallocate(self, cloudlet):
        with self.lock:
            if cloudlet.id in self.cloudlets:
                self.cpu_used -= cloudlet.cpu
                self.ram_used -= cloudlet.ram
                self.storage_used -= cloudlet.storage
                self.bandwidth_used -= cloudlet.bandwidth
                self.gpu_used -= cloudlet.gpu
                self.cloudlets.remove(cloudlet.id)
                if not self.cloudlets:
                    self.status = VMStatus.IDLE
                self.last_activity = time.time()

# --- CLOUDLET CLASS ---

class Cloudlet:
    def __init__(self, cpu, ram, storage, sla_priority, deadline, name=None, bandwidth=100, gpu=0):
        self.id = str(uuid.uuid4())
        self.name = name or f"Cloudlet-{self.id[:8]}"
        self.cpu = cpu
        self.ram = ram
        self.storage = storage
        self.bandwidth = bandwidth  # Mbps
        self.gpu = gpu
        self.sla_priority = int(sla_priority)
        self.deadline = time.time() + deadline
        self.status = CloudletStatus.WAITING
        self.vm_id = None
        self.creation_time = time.time()
        self.start_time = None
        self.completion_time = None

# --- RESOURCE MANAGER & SCHEDULER ---

class ResourceManager:
    def __init__(self):
        # Auto-scaling configuration
        self.SCALING_UP_THRESHOLD = 0.8  # Scale up when utilization exceeds 80%
        self.SCALING_DOWN_THRESHOLD = 0.2  # Scale down when utilization is below 20%
        self.IDLE_TIME_THRESHOLD = 120  # 2 minutes in seconds
        self.SCALING_COOLDOWN = 10  # 10 seconds cooldown between scaling operations
        
        self.vms = []
        self.cloudlets = []
        self.pending_queue = deque()
        self.lock = threading.RLock()
        self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self.metrics_callback = None  # Will be set by Flask app if present
        self.last_scaling_time = 0  # Track last scaling operation
        self.monitor_thread.start()

    def set_metrics_callback(self, cb):
        self.metrics_callback = cb

    def add_vm(self, vm):
        with self.lock:
            self.vms.append(vm)
            # After adding a VM, immediately try to allocate any waiting/pending cloudlets
            self._allocate_cloudlets()

    def submit_cloudlet(self, cloudlet):
        with self.lock:
            self.cloudlets.append(cloudlet)
            self.pending_queue.append(cloudlet)
            cloudlet.status = CloudletStatus.WAITING
            # Immediately try to allocate after submission
            self._allocate_cloudlets()

    def _monitor(self):
        while True:
            self._allocate_cloudlets()
            self._scale_vms()
            self._check_deadlines()
            if self.metrics_callback:
                self.metrics_callback()
            time.sleep(1)

    def _allocate_cloudlets(self):
        with self.lock:
            # Prioritize by SLA, then by creation time
            sorted_queue = sorted(self.pending_queue, key=lambda c: (-c.sla_priority, c.creation_time))
            for cloudlet in sorted_queue:
                if cloudlet.status not in [CloudletStatus.WAITING, CloudletStatus.PENDING]:
                    continue
                vm = self._find_vm_for_cloudlet(cloudlet)
                if vm:
                    allocated = vm.allocate(cloudlet)
                    if allocated:
                        cloudlet.status = CloudletStatus.ACTIVE
                        cloudlet.vm_id = vm.id
                        cloudlet.start_time = time.time()
                        self.pending_queue.remove(cloudlet)
                else:
                    # If no VM can serve, just mark as pending. Do NOT trigger scaling or create new VMs here.
                    cloudlet.status = CloudletStatus.PENDING

    def _find_vm_for_cloudlet(self, cloudlet):
        # Best fit: least loaded VM that can fit
        candidates = [vm for vm in self.vms if vm.can_allocate(cloudlet.cpu, cloudlet.ram, cloudlet.storage, cloudlet.bandwidth, cloudlet.gpu) and vm.status != VMStatus.TERMINATED]
        if not candidates:
            return None
        return min(candidates, key=lambda vm: (vm.cpu_used + vm.ram_used + vm.storage_used))

    def _scale_vms(self):
        """Auto-scale VMs based on resource utilization"""
        if time.time() - self.last_scaling_time < self.SCALING_COOLDOWN:
            return  # Prevent too frequent scaling

        with self.lock:
            # If there are no VMs and pending cloudlets, create a VM immediately
            if not self.vms and self.pending_queue:
                cloudlet = self.pending_queue[0]
                # Create a VM with enough resources to accommodate the cloudlet
                new_vm = VM(
                    cpu=cloudlet.cpu,
                    ram=cloudlet.ram,
                    storage=cloudlet.storage,
                    bandwidth=cloudlet.bandwidth,
                    gpu=cloudlet.gpu
                )
                self.add_vm(new_vm)
                print(f"Auto-scaling: Created initial VM {new_vm.id} for cloudlet {cloudlet.id}")
                self.last_scaling_time = time.time()
                return

            # Calculate overall resource utilization
            total_cpu = sum(vm.cpu_capacity for vm in self.vms)
            total_ram = sum(vm.ram_capacity for vm in self.vms)
            total_storage = sum(vm.storage_capacity for vm in self.vms)
            
            used_cpu = sum(vm.cpu_used for vm in self.vms)
            used_ram = sum(vm.ram_used for vm in self.vms)
            used_storage = sum(vm.storage_used for vm in self.vms)
            
            if total_cpu == 0 or total_ram == 0 or total_storage == 0:
                return  # Prevent division by zero

            cpu_utilization = used_cpu / total_cpu
            ram_utilization = used_ram / total_ram
            storage_utilization = used_storage / total_storage
            
            # Calculate average utilization
            avg_utilization = (cpu_utilization + ram_utilization + storage_utilization) / 3
            
            # Scale up if utilization is high
            if avg_utilization > self.SCALING_UP_THRESHOLD:
                # Create a VM with medium configuration
                new_vm = VM(
                    cpu=4,
                    ram=8,
                    storage=100,
                    bandwidth=1000,
                    gpu=1
                )
                self.add_vm(new_vm)
                print(f"Auto-scaling: Created new VM {new_vm.id} due to high utilization")
                self.last_scaling_time = time.time()
            
            # Scale down if utilization is low
            elif avg_utilization < self.SCALING_DOWN_THRESHOLD:
                # Remove idle VMs
                current_time = time.time()
                for vm in self.vms[:]:  # Create a copy to safely remove items
                    if vm.status == VMStatus.IDLE and \
                       (current_time - vm.last_activity) > self.IDLE_TIME_THRESHOLD:
                        self.vms.remove(vm)
                        print(f"Auto-scaling: Removed idle VM {vm.id}")
                        self.last_scaling_time = time.time()
                        break  # Remove one VM at a time to prevent aggressive scaling down

    def _scale_up(self):
        """Create a new VM with medium configuration"""
        # Create a medium VM as default
        new_vm = VM(
            cpu=4,
            ram=8,
            storage=100,
            bandwidth=1000,
            gpu=1
        )
        self.add_vm(new_vm)
        print(f"Scaled up: Created new VM {new_vm.id}")

    def _scale_down(self):
        """Remove idle VMs"""
        current_time = time.time()
        for vm in self.vms[:]:  # Create a copy to safely remove items
            if vm.status == VMStatus.IDLE and \
               (current_time - vm.last_activity) > self.IDLE_TIME_THRESHOLD:
                self.vms.remove(vm)
                print(f"Scaled down: Removed idle VM {vm.id}")
                break  # Remove one VM at a time to prevent aggressive scaling down

    def _check_deadlines(self):
        # If a cloudlet is about to miss its deadline, escalate priority or trigger more scaling
        now = time.time()
        for cloudlet in self.cloudlets:
            if cloudlet.status in [CloudletStatus.WAITING, CloudletStatus.PENDING]:
                if (cloudlet.deadline - now) < 10:  # 10 seconds to deadline
                    cloudlet.sla_priority = 3  # Escalate to high priority

    def complete_cloudlet(self, cloudlet_id):
        with self.lock:
            for cloudlet in self.cloudlets:
                if cloudlet.id == cloudlet_id and cloudlet.status == CloudletStatus.ACTIVE:
                    cloudlet.status = CloudletStatus.COMPLETED
                    cloudlet.completion_time = time.time()
                    for vm in self.vms:
                        if vm.id == cloudlet.vm_id:
                            vm.deallocate(cloudlet)
                            break
            
            # After completing a cloudlet, try to allocate any waiting cloudlets
            self._allocate_cloudlets()

    def delete_cloudlet(self, cloudlet_id):
        with self.lock:
            for cl in self.cloudlets:
                if cl.id == cloudlet_id:
                    # Deallocate if active
                    if cl.status == CloudletStatus.ACTIVE and cl.vm_id:
                        for vm in self.vms:
                            if vm.id == cl.vm_id:
                                vm.deallocate(cl)
                                break
                    # Remove from queues
                    if cl in self.pending_queue:
                        self.pending_queue.remove(cl)
                    self.cloudlets.remove(cl)
                    
                    # After deleting a cloudlet, try to allocate any waiting cloudlets
                    self._allocate_cloudlets()
                    return True
            return False

    def delete_vm(self, vm_id):
        with self.lock:
            for vm in self.vms:
                if vm.id == vm_id:
                    # Only allow deletion if no cloudlet is running on this VM
                    running = any(cl.vm_id == vm_id and cl.status == CloudletStatus.ACTIVE for cl in self.cloudlets)
                    if running:
                        return False  # Indicate error: VM has running cloudlets
                    self.vms.remove(vm)
                    return True
            return False

    def get_metrics(self):
        with self.lock:
            total_cpu = sum(vm.cpu_capacity for vm in self.vms)
            total_ram = sum(vm.ram_capacity for vm in self.vms)
            total_storage = sum(vm.storage_capacity for vm in self.vms)
            
            used_cpu = sum(vm.cpu_used for vm in self.vms)
            used_ram = sum(vm.ram_used for vm in self.vms)
            used_storage = sum(vm.storage_used for vm in self.vms)
            
            if total_cpu == 0 or total_ram == 0 or total_storage == 0:
                avg_utilization = 0
            else:
                cpu_utilization = used_cpu / total_cpu
                ram_utilization = used_ram / total_ram
                storage_utilization = used_storage / total_storage
                avg_utilization = (cpu_utilization + ram_utilization + storage_utilization) / 3

            scaling_status = "Disabled"
            if avg_utilization > self.SCALING_UP_THRESHOLD:
                scaling_status = "Scaling Up"
            elif avg_utilization < self.SCALING_DOWN_THRESHOLD:
                scaling_status = "Scaling Down"
            elif self.vms and self.pending_queue:
                scaling_status = "Pending Allocation"

            return {
                'vms': [
                    {
                        'id': vm.id,
                        'cpu_capacity': vm.cpu_capacity,
                        'ram_capacity': vm.ram_capacity,
                        'storage_capacity': vm.storage_capacity,
                        'bandwidth_capacity': vm.bandwidth_capacity,
                        'gpu_capacity': vm.gpu_capacity,
                        'cpu_used': vm.cpu_used,
                        'ram_used': vm.ram_used,
                        'storage_used': vm.storage_used,
                        'bandwidth_used': vm.bandwidth_used,
                        'gpu_used': vm.gpu_used,
                        'status': vm.status.name,
                        'last_activity': vm.last_activity
                    }
                    for vm in self.vms
                ],
                'cloudlets': [
                    {
                        'id': cl.id,
                        'name': cl.name,
                        'cpu': cl.cpu,
                        'ram': cl.ram,
                        'storage': cl.storage,
                        'bandwidth': cl.bandwidth,
                        'gpu': cl.gpu,
                        'sla_priority': cl.sla_priority,
                        'deadline': cl.deadline,
                        'status': cl.status.name,
                        'vm_id': cl.vm_id,
                        'creation_time': cl.creation_time,
                        'start_time': cl.start_time,
                        'completion_time': cl.completion_time
                    }
                    for cl in self.cloudlets
                ],
                'scaling_status': scaling_status,
                'utilization': {
                    'cpu': cpu_utilization * 100 if total_cpu > 0 else 0,
                    'ram': ram_utilization * 100 if total_ram > 0 else 0,
                    'storage': storage_utilization * 100 if total_storage > 0 else 0,
                    'average': avg_utilization * 100
                },
                'auto_scaling': True
            }
