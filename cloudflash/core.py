import threading
import uuid
import time
from enum import Enum, auto
from collections import deque
from typing import List, Dict, Optional

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

# --- MEMORY MANAGER ---
class MemoryManager:
    def __init__(self, total_memory: int = 1024):  # Total memory in GB
        self.PAGE_SIZE = 1  # 1GB per page
        self.total_pages = total_memory // self.PAGE_SIZE
        self.pages = [False] * self.total_pages  # False = free, True = allocated
        self.page_to_vm: Dict[int, str] = {}  # Map page index to VM ID
        self.page_last_used = [time.time()] * self.total_pages  # Track last use
        self.lock = threading.Lock()

    def allocate_pages(self, ram_needed: int, vm_id: str) -> List[int]:
        """Allocate pages for the given RAM requirement."""
        with self.lock:
            pages_needed = (ram_needed + self.PAGE_SIZE - 1) // self.PAGE_SIZE
            free_pages = [i for i, allocated in enumerate(self.pages) if not allocated]
            
            # Try to find contiguous pages first
            for start in range(len(self.pages) - pages_needed + 1):
                if all(not self.pages[start + i] for i in range(pages_needed)):
                    for i in range(start, start + pages_needed):
                        self.pages[i] = True
                        self.page_to_vm[i] = vm_id
                        self.page_last_used[i] = time.time()
                    return list(range(start, start + pages_needed))
            
            # If no contiguous space, use any free pages
            if len(free_pages) >= pages_needed:
                allocated_pages = free_pages[:pages_needed]
                for i in allocated_pages:
                    self.pages[i] = True
                    self.page_to_vm[i] = vm_id
                    self.page_last_used[i] = time.time()
                return allocated_pages
            return []

    def deallocate_pages(self, page_indices: List[int]) -> None:
        """Deallocate pages and update last used time."""
        with self.lock:
            for i in page_indices:
                if i in self.page_to_vm:
                    self.pages[i] = False
                    del self.page_to_vm[i]
                    self.page_last_used[i] = time.time()

    def consolidate(self) -> None:
        """Consolidate fragmented memory to reduce gaps."""
        with self.lock:
            allocated_pages = [i for i, allocated in enumerate(self.pages) if allocated]
            if not allocated_pages:
                return
            new_allocation = 0
            for old_page in allocated_pages[:]:
                if old_page != new_allocation:
                    vm_id = self.page_to_vm[old_page]
                    self.pages[old_page] = False
                    del self.page_to_vm[old_page]
                    self.pages[new_allocation] = True
                    self.page_to_vm[new_allocation] = vm_id
                    self.page_last_used[new_allocation] = self.page_last_used[old_page]
                new_allocation += 1

    def get_memory_metrics(self, vms: List[dict]) -> dict:
        """Calculate memory metrics including fragmentation."""
        with self.lock:
            total_pages = self.total_pages
            free_pages = sum(1 for allocated in self.pages if not allocated)
            allocated_pages = [i for i, allocated in enumerate(self.pages) if allocated]
            
            # Calculate external fragmentation
            external_fragmentation = 0
            if allocated_pages:
                gaps = [allocated_pages[i+1] - allocated_pages[i] - 1 
                       for i in range(len(allocated_pages)-1)]
                external_fragmentation = sum(gaps) / total_pages if gaps else 0
            
            # Calculate internal fragmentation
            internal_fragmentation = 0
            for vm in vms:
                pages = sum(1 for p, v in self.page_to_vm.items() if v == vm['id'])
                allocated_ram = pages * self.PAGE_SIZE
                internal_fragmentation += (allocated_ram - vm['ram_used']) / total_pages
            
            fragmentation_percent = (external_fragmentation + internal_fragmentation) * 100
            
            return {
                'total_pages': total_pages,
                'free_pages': free_pages,
                'allocated_pages': len(allocated_pages),
                'fragmentation': fragmentation_percent
            }

# --- VM CLASS ---

class VM:
    def __init__(self, cpu, ram, storage, bandwidth=1000, gpu=0, 
                 firewall_enabled=True, isolation_level='STANDARD'):
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
        self.memory_pages: List[int] = []  # Track allocated memory pages

    def can_allocate(self, cpu, ram, storage, bandwidth=0, gpu=0, memory_manager=None):
        if memory_manager:
            pages_needed = (ram + memory_manager.PAGE_SIZE - 1) // memory_manager.PAGE_SIZE
            free_pages = sum(1 for allocated in memory_manager.pages if not allocated)
            if free_pages < pages_needed:
                return False
        return (
            self.cpu_capacity - self.cpu_used >= cpu and
            self.ram_capacity - self.ram_used >= ram and
            self.storage_capacity - self.storage_used >= storage and
            self.bandwidth_capacity - self.bandwidth_used >= bandwidth and
            self.gpu_capacity - self.gpu_used >= gpu
        )

    def allocate(self, cloudlet, memory_manager=None):
        with self.lock:
            if self.can_allocate(cloudlet.cpu, cloudlet.ram, cloudlet.storage, 
                              cloudlet.bandwidth, cloudlet.gpu, memory_manager):
                if memory_manager:
                    pages = memory_manager.allocate_pages(cloudlet.ram, self.id)
                    if not pages:
                        return False
                    self.memory_pages.extend(pages)
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

    def deallocate(self, cloudlet, memory_manager=None):
        with self.lock:
            if cloudlet.id in self.cloudlets:
                if memory_manager:
                    pages_needed = (cloudlet.ram + memory_manager.PAGE_SIZE - 1) // memory_manager.PAGE_SIZE
                    pages_to_free = self.memory_pages[-pages_needed:] if self.memory_pages else []
                    memory_manager.deallocate_pages(pages_to_free)
                    self.memory_pages = self.memory_pages[:-pages_needed] if self.memory_pages else []
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
    def __init__(self, cpu, ram, storage, sla_priority, deadline, name=None, bandwidth=100, gpu=0, execution_time=5.0):
        self.id = str(uuid.uuid4())
        self.name = name or f"Cloudlet-{self.id[:8]}"
        self.cpu = cpu
        self.ram = ram
        self.storage = storage
        self.bandwidth = bandwidth  # Mbps
        self.gpu = gpu
        self.sla_priority = int(sla_priority)
        self.deadline = time.time() + deadline
        self.execution_time = float(execution_time)  # in seconds
        self.status = CloudletStatus.WAITING
        self.vm_id = None
        self.creation_time = time.time()
        self.start_time = None
        self.completion_time = None
        self._completion_timer = None

# --- RESOURCE MANAGER & SCHEDULER ---

class ResourceManager:
    def __init__(self):
        # Auto-scaling configuration
        self.SCALING_UP_THRESHOLD = 0.8  # Scale up when utilization exceeds 80%
        self.SCALING_DOWN_THRESHOLD = 0.2  # Scale down when utilization is below 20%
        self.IDLE_TIME_THRESHOLD = 60  # 1 minutes in seconds
        self.SCALING_COOLDOWN = 10  # 10 seconds cooldown between scaling operations
        
        # Base cooldown in seconds
        self.BASE_COOLDOWN = 10
        self.last_scaling_time = 0

        # Load balancing algorithm (default: round_robin)
        self.load_balancing_algorithm = 'round_robin'
        self.available_algorithms = [
            'round_robin',
            'least_loaded',
            'weighted_round_robin',
            'best_fit'
        ]

        # Per-resource scale-up/down thresholds (%)
        self.THRESHOLDS = {
            'cpu': {'up': 0.80, 'down': 0.20},
            'ram': {'up': 0.75, 'down': 0.25},
            'storage': {'up': 0.85, 'down': 0.30},
            'bandwidth': {'up': 0.80, 'down': 0.30},
            'gpu': {'up': 0.70, 'down': 0.25}
        }

        self.vms = []
        self.cloudlets = []
        self.pending_queue = deque()
        self.lock = threading.RLock()
        self.memory_manager = MemoryManager(total_memory=1024)
        self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self.metrics_callback = None  # Will be set by Flask app if present
        self.last_scaling_time = 0  # Track last scaling operation
        self.last_consolidation_time = 0
        self.monitor_thread.start()
        self.system_logs = deque(maxlen=100)

    def set_metrics_callback(self, cb):
        self.metrics_callback = cb
        
    def get_vms(self):
        """Return a list of all VMs with their current state."""
        with self.lock:
            return [{
                "id": vm.id,
                "cpu_cores": vm.cpu_capacity,
                "cpu_used": vm.cpu_used,
                "ram_gb": vm.ram_capacity,
                "ram_used": vm.ram_used,
                "storage_gb": vm.storage_capacity,
                "storage_used": vm.storage_used,
                "bandwidth": vm.bandwidth_capacity,
                "bandwidth_used": vm.bandwidth_used,
                "gpu": vm.gpu_capacity,
                "gpu_used": vm.gpu_used,
                "status": vm.status.name,
                "cloudlet_count": len(vm.cloudlets),
                "last_activity": time.time() - vm.last_activity,
                "is_idle": vm.status == VMStatus.IDLE
            } for vm in self.vms]

    def _log_scaling_event(self, event_type, message, utilization=None, cooldown=None):
        timestamp = time.strftime('%X')
        log = f"[{timestamp}] [{event_type}] {message}"
        if utilization:
            log += f" | Utilization: CPU {utilization['cpu']:.1%}, RAM {utilization['ram']:.1%}, Storage {utilization['storage']:.1%}"
        if cooldown is not None:
            log += f" | Cooldown: {cooldown:.1f}s"
        self.system_logs.append(log)
        self.log(log)  # Sends to dashboard if callback is set

    def get_cloudlets(self):
        """Return a list of all cloudlets with their current state."""
        with self.lock:
            cloudlets = []
            for cl in self.cloudlets + list(self.pending_queue):
                cloudlets.append({
                    "id": cl.id,
                    "name": cl.name,
                    "cpu": cl.cpu,
                    "ram": cl.ram,
                    "storage": cl.storage,
                    "bandwidth": cl.bandwidth,
                    "gpu": cl.gpu,
                    "sla_priority": cl.sla_priority,
                    "status": cl.status.name,
                    "vm_id": cl.vm_id,
                    "deadline": cl.deadline,
                    "time_remaining": max(0, cl.deadline - time.time()),
                    "age": time.time() - cl.creation_time,
                    "is_active": cl.status == CloudletStatus.ACTIVE,
                    "is_completed": cl.status == CloudletStatus.COMPLETED,
                    "is_failed": cl.status == CloudletStatus.FAILED,
                    "is_pending": cl.status in [CloudletStatus.WAITING, CloudletStatus.PENDING],
                    "time_critical": ((cl.deadline - time.time()) < 10) if cl.status in [CloudletStatus.WAITING, CloudletStatus.PENDING, CloudletStatus.ACTIVE] else False,
                })
            return cloudlets

    def add_vm(self, vm):
        with self.lock:
            pages = self.memory_manager.allocate_pages(vm.ram_capacity, vm.id)
            if not pages:
                print(f"Failed to add VM {vm.id}: Insufficient memory pages")
                return False
            vm.memory_pages = pages
            self.vms.append(vm)
            self._allocate_cloudlets()
            print(f"Added VM {vm.id} with {len(pages)} memory pages")
            return True

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
            if time.time() - self.last_consolidation_time > 30:  # Consolidate every 30 seconds
                self.memory_manager.consolidate()
                self.last_consolidation_time = time.time()
            if self.metrics_callback:
                self.metrics_callback()
            time.sleep(1)

    def _allocate_cloudlets(self):
        with self.lock:
            # Process pending queue first
            while self.pending_queue:
                cloudlet = self.pending_queue[0]
                vm = self._find_vm_for_cloudlet(cloudlet)
                if not vm:
                    break  # No suitable VM found
                
                if vm.allocate(cloudlet, self.memory_manager):
                    cloudlet.status = CloudletStatus.ACTIVE
                    cloudlet.vm_id = vm.id
                    cloudlet.start_time = time.time()
                    self.pending_queue.popleft()
                    
                    # Start a timer for automatic completion
                    if cloudlet.execution_time > 0:
                        cloudlet._completion_timer = threading.Timer(
                            cloudlet.execution_time,
                            self.complete_cloudlet,
                            args=(cloudlet.id,)
                        )
                        cloudlet._completion_timer.daemon = True
                        cloudlet._completion_timer.start()
                        self.log(f" [STARTED] {cloudlet.name} on VM {vm.id} (will complete in {cloudlet.execution_time:.1f}s)")
                    else:
                        self.log(f" [ALLOCATED] {cloudlet.name} to VM {vm.id}")
                else:
                    break  # Couldn't allocate, will try again later

    def _find_vm_for_cloudlet(self, cloudlet):
        """
        Find a suitable VM for the cloudlet using the current load balancing algorithm.
        
        Args:
            cloudlet: The cloudlet to be allocated
            
        Returns:
            VM object if a suitable VM is found, None otherwise
        """
        algorithm = self.load_balancing_algorithm
        candidates = [
            vm for vm in self.vms 
            if vm.can_allocate(cloudlet.cpu, cloudlet.ram, cloudlet.storage, 
                            cloudlet.bandwidth, cloudlet.gpu, self.memory_manager) 
            and vm.status != VMStatus.TERMINATED
        ]
        
        if not candidates:
            return None
            
        if algorithm == 'round_robin':
            # Simple round-robin distribution
            if not hasattr(self, '_last_vm_index'):
                self._last_vm_index = -1
            self._last_vm_index = (self._last_vm_index + 1) % len(candidates)
            return candidates[self._last_vm_index]
            
        elif algorithm == 'least_loaded':
            # Select VM with the least resource utilization
            def get_utilization(vm):
                cpu_util = vm.cpu_used / vm.cpu_capacity if vm.cpu_capacity > 0 else 0
                ram_util = vm.ram_used / vm.ram_capacity if vm.ram_capacity > 0 else 0
                # Weighted sum of utilizations (can be adjusted based on priority)
                return 0.6 * cpu_util + 0.3 * ram_util + 0.1 * (vm.storage_used / vm.storage_capacity if vm.storage_capacity > 0 else 0)
                
            return min(candidates, key=get_utilization)
            
        elif algorithm == 'weighted_round_robin':
            # Round-robin but weighted by VM capacity
            if not hasattr(self, '_weighted_index'):
                self._weighted_index = 0
                self._weights = [vm.cpu_capacity + vm.ram_capacity for vm in candidates]
                self._total_weight = sum(self._weights)
                
            selected = None
            while not selected:
                self._weighted_index = (self._weighted_index + 1) % len(candidates)
                if random.random() < (self._weights[self._weighted_index] / self._total_weight):
                    selected = candidates[self._weighted_index]
            return selected
            
        else:  # best_fit (default)
            # Original best-fit implementation
            return min(candidates, key=lambda vm: (vm.cpu_used + vm.ram_used + vm.storage_used))

    def _calculate_adaptive_cooldown(self, deltas):
        """
        Dynamic cooldown: higher spikes = faster scaling (min 3s, max BASE_COOLDOWN)
        """
        max_delta = max(deltas.values(), default=0)
        severity = min(max_delta, 1.0)  # Cap at 1.0 (100%)
        cooldown = self.BASE_COOLDOWN * (1 - severity)
        return max(cooldown, 3)

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

            # Total and used resources
            total = {
                'cpu': sum(vm.cpu_capacity for vm in self.vms),
                'ram': sum(vm.ram_capacity for vm in self.vms),
                'storage': sum(vm.storage_capacity for vm in self.vms),
                'bandwidth': sum(vm.bandwidth_capacity for vm in self.vms),
                'gpu': sum(vm.gpu_capacity for vm in self.vms)
            }
            used = {
                'cpu': sum(vm.cpu_used for vm in self.vms),
                'ram': sum(vm.ram_used for vm in self.vms),
                'storage': sum(vm.storage_used for vm in self.vms),
                'bandwidth': sum(vm.bandwidth_used for vm in self.vms),
                'gpu': sum(vm.gpu_used for vm in self.vms)
            }
            utilization = {
                key: (used[key] / total[key]) if total[key] > 0 else 0
                for key in total
            }

            now = time.time()

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
            
            # Calculate how far each resource is from its threshold
            spike_deltas = {
                key: max(0, utilization[key] - self.THRESHOLDS[key]['up'])
                for key in self.THRESHOLDS
            }
            dip_deltas = {
                key: max(0, self.THRESHOLDS[key]['down'] - utilization[key])
                for key in self.THRESHOLDS
            }

            # Determine if any resource needs scaling up/down
            should_scale_up = any(spike_deltas.values())
            should_scale_down = any(dip_deltas.values())

            # Apply adaptive cooldown
            adaptive_cooldown = self._calculate_adaptive_cooldown(spike_deltas if should_scale_up else dip_deltas)
            self.last_adaptive_cooldown = adaptive_cooldown  # <- for dashboard visibility
            
            if should_scale_up:
                self._scale_up()
                self.last_scaling_time = now
                self._log_scaling_event(
                    event_type="SCALE_UP",
                    message="Scaled up VM due to high resource usage",
                    utilization=utilization,
                    cooldown=adaptive_cooldown
                )
            elif should_scale_down:
                self._scale_down()
                self.last_scaling_time = now
                self._log_scaling_event(
                    event_type="SCALE_DOWN",
                    message="Scaled down VM due to under-utilization",
                    utilization=utilization,
                    cooldown=adaptive_cooldown
                )

            # Log current utilization
            self._log_scaling_event(
                'utilization',
                utilization=utilization,
                spike_deltas={
                    key: max(0, utilization[key] - self.THRESHOLDS[key]['up'])
                    for key in self.THRESHOLDS
                },
                dip_deltas={
                    key: max(0, self.THRESHOLDS[key]['down'] - utilization[key])
                    for key in self.THRESHOLDS
                },
                cooldown=getattr(self, 'last_adaptive_cooldown', self.BASE_COOLDOWN)
            )

            print("Utilization:", {k: f"{v:.2%}" for k, v in utilization.items()})
            print("Spike Deltas:", spike_deltas)
            print("Cooldown:", adaptive_cooldown, "seconds")

            if now - self.last_scaling_time < adaptive_cooldown:
                return  # Still in cooldown

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
                        self.memory_manager.deallocate_pages(vm.memory_pages)
                        self._log_scaling_event(
                            'scale_down', 
                            vm_id=vm.id,
                            cooldown=self.last_adaptive_cooldown,
                            timestamp=current_time
                        )
                        print(f"Auto-scaling: Removed idle VM {vm.id}")
                        self.last_scaling_time = time.time()
                        break  # Remove one VM at a time to prevent aggressive scaling down

    def _log_scaling_event(self, event_type, vm_id=None, **kwargs):
        """Log scaling events to be sent to the dashboard"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        event = {
            'timestamp': timestamp,
            'type': event_type,
            'vm_id': vm_id,
            'message': '',
            'details': kwargs
        }
        
        if event_type == 'scale_up':
            event['message'] = f"[SCALE UP] Created new VM {vm_id}"
        elif event_type == 'scale_down':
            event['message'] = f"[SCALE DOWN] Removed idle VM {vm_id}"
        elif event_type == 'utilization':
            event['message'] = "[UTILIZATION] " + ", ".join(
                f"{k.upper()}: {v:.1%}" for k, v in kwargs.get('utilization', {}).items()
            )
        
        # Add to system logs
        self.system_logs.append(event)
        # Keep only the last 1000 log entries
        if len(self.system_logs) > 1000:
            self.system_logs = self.system_logs[-1000:]
        return event

    def _scale_up(self):
        """Create a new VM for scaling up"""
        new_vm = VM(
            cpu=4,
            ram=8,
            storage=100,
            bandwidth=1000,
            gpu=1
        )
        self.add_vm(new_vm)
        self._log_scaling_event(
            'scale_up', 
            vm_id=new_vm.id,
            cooldown=self.last_adaptive_cooldown,
            timestamp=time.time()
        )
        self.log(f"Scaled up: Created new VM {new_vm.id}")
        self.log(f"[AUTO-SCALER] Scaling Up at {time.strftime('%X')} | Cooldown: {self.last_adaptive_cooldown:.1f}s")

    def _scale_down(self):
        """Remove idle VMs"""
        current_time = time.time()
        for vm in self.vms[:]:  # Create a copy to safely remove items
            if vm.status == VMStatus.IDLE and \
               (current_time - vm.last_activity) > self.IDLE_TIME_THRESHOLD:
                vm_id = vm.id
                
                # Find and deallocate all pages associated with this VM
                pages_to_deallocate = []
                for page, vm_id_in_page in self.memory_manager.page_to_vm.items():
                    if vm_id_in_page == vm_id:
                        pages_to_deallocate.append(page)
                
                self.memory_manager.deallocate_pages(pages_to_deallocate)
                
                # Remove VM from list
                self.vms.remove(vm)
                
                self._log_scaling_event(
                    'scale_down', 
                    vm_id=vm_id,
                    cooldown=self.last_adaptive_cooldown,
                    timestamp=current_time
                )
                self.log(f"Scaled down: Removed idle VM {vm_id}")
                self.log(f"[AUTO-SCALER] Scaling Down at {time.strftime('%X')} | Cooldown: {self.last_adaptive_cooldown:.1f}s")
                break  # Remove one VM at a time to prevent aggressive scaling down

    def _check_deadlines(self):
        now = time.time()
        for cloudlet in self.cloudlets:
            if cloudlet.status in [CloudletStatus.WAITING, CloudletStatus.PENDING]:
                time_left = cloudlet.deadline - now

                # Check if deadline is missed
                if time_left <= 0:
                    cloudlet.status = CloudletStatus.FAILED
                    cloudlet.completion_time = now
                    self.log(f"❌ [DEADLINE MISSED] {cloudlet.name} failed - missed deadline")
                    continue

                # Escalate based on urgency
                if time_left < 5:
                    cloudlet.sla_priority = 3  # Critical
                    self.log(f"⚠️ [SLA ESCALATED] {cloudlet.name} escalated to Priority 3 (deadline in {time_left:.1f}s)")
                elif time_left < 15:
                    cloudlet.sla_priority = max(cloudlet.sla_priority, 2)
                    self.log(f"⏳ [SLA WARNING] {cloudlet.name} elevated to Priority 2 (deadline in {time_left:.1f}s)")

    def complete_cloudlet(self, cloudlet_id):
        with self.lock:
            for cloudlet in self.cloudlets:
                if cloudlet.id == cloudlet_id and cloudlet.status == CloudletStatus.ACTIVE:
                    # Cancel any pending timer if it exists
                    if hasattr(cloudlet, '_completion_timer') and cloudlet._completion_timer:
                        cloudlet._completion_timer.cancel()
                    
                    cloudlet.status = CloudletStatus.COMPLETED
                    cloudlet.completion_time = time.time()
                    
                    # Log completion
                    if cloudlet.start_time:
                        actual_duration = cloudlet.completion_time - cloudlet.start_time
                        self.log(f"✅ [COMPLETED] {cloudlet.name} in {actual_duration:.2f}s on VM {cloudlet.vm_id}")
                    
                    # Deallocate resources
                    for vm in self.vms:
                        if vm.id == cloudlet.vm_id:
                            vm.deallocate(cloudlet, self.memory_manager)
                            break
                    
                    # Trigger allocation of pending cloudlets
                    self._allocate_cloudlets()
                    return True
            return False

    def delete_cloudlet(self, cloudlet_id):
        with self.lock:
            for cl in self.cloudlets:
                if cl.id == cloudlet_id:
                    # Deallocate if active
                    if cl.status == CloudletStatus.ACTIVE and cl.vm_id:
                        for vm in self.vms:
                            if vm.id == cl.vm_id:
                                vm.deallocate(cl, self.memory_manager)
                                break
                    # Remove from queues
                    if cl in self.pending_queue:
                        self.pending_queue.remove(cl)
                    self.cloudlets.remove(cl)
                    self._allocate_cloudlets()
                    return True
            return False

    def delete_vm(self, vm_id):
        with self.lock:
            for vm in self.vms:
                if vm.id == vm_id:
                    # Only allow deletion if no cloudlet is running on this VM
                    running = any(cl.vm_id == vm_id and cl.status == CloudletStatus.ACTIVE 
                               for cl in self.cloudlets)
                    if running:
                        return False  # Indicate error: VM has running cloudlets
                    
                    # Find all pages associated with this VM
                    pages_to_deallocate = []
                    for page, vm_id_in_page in self.memory_manager.page_to_vm.items():
                        if vm_id_in_page == vm_id:
                            pages_to_deallocate.append(page)
                    
                    # Deallocate all pages associated with this VM
                    self.memory_manager.deallocate_pages(pages_to_deallocate)
                    
                    # Remove VM from list
                    self.vms.remove(vm)
                    return True
            return False

    def log(self, message: str):
        print(message)  # for console
        if self.metrics_callback:
            try:
                self.metrics_callback(log=message)  # send to dashboard via Flask
            except Exception as e:
                print(f"Failed to emit log: {e}")

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
                cpu_utilization = 0
                ram_utilization = 0
                storage_utilization = 0
            else:
                cpu_utilization = used_cpu / total_cpu
                ram_utilization = used_ram / total_ram
                storage_utilization = used_storage / total_storage
                avg_utilization = (cpu_utilization + ram_utilization + storage_utilization) / 3

            scaling_status = "Stable"
            if avg_utilization > self.SCALING_UP_THRESHOLD or self.pending_queue:
                scaling_status = "Scaling Up"
            elif avg_utilization < self.SCALING_DOWN_THRESHOLD:
                scaling_status = "Scaling Down"

            vms_data = [
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
                    'last_activity': vm.last_activity,
                    'memory_pages': vm.memory_pages
                }
                for vm in self.vms
            ]
            
            # Get memory metrics including fragmentation
            memory_metrics = self.memory_manager.get_memory_metrics(vms_data)

            return {
                'vms': vms_data,
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
                        'completion_time': cl.completion_time,
                        'execution_time': cl.execution_time,
                        'time_critical': ((cl.deadline - time.time()) < 10) if cl.status in [CloudletStatus.WAITING, CloudletStatus.PENDING, CloudletStatus.ACTIVE] else False,
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
                'memory': memory_metrics,
                'auto_scaling': True,
                'scaling': {
                    'status': scaling_status,
                    'last_scaled_at': self.last_scaling_time,
                    'adaptive_cooldown': getattr(self, 'last_adaptive_cooldown', self.BASE_COOLDOWN),
                    'next_possible_scale': self.last_scaling_time + getattr(self, 'last_adaptive_cooldown', self.BASE_COOLDOWN)
                }
            }