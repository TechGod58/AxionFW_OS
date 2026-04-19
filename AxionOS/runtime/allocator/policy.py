POLICY_VERSION = 1
HOST_CPU_CEILING = 0.80
HOST_MEM_CEILING = 0.85

VM_CLASSES = {
    'small': {'vcpu': 1, 'mem_mb': 2048},
    'medium': {'vcpu': 2, 'mem_mb': 4096},
    'large': {'vcpu': 4, 'mem_mb': 8192},
}

WORKLOAD_PRIORITY = {
    'latency_sensitive': 90,
    'stability_critical': 80,
    'throughput_heavy': 60,
}
