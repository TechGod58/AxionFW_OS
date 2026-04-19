from policy import VM_CLASSES, WORKLOAD_PRIORITY, HOST_CPU_CEILING, HOST_MEM_CEILING


def decide(request, host):
    # request: {vm_class, workload_class, corr}
    # host: {cpu_used, mem_used}
    if host.get('cpu_used', 0) >= HOST_CPU_CEILING or host.get('mem_used', 0) >= HOST_MEM_CEILING:
        return {'decision': 'QUEUE', 'code': 'ALLOC_HOST_PRESSURE', 'retry_sec': 15}

    vm_class = request.get('vm_class', 'small')
    if vm_class not in VM_CLASSES:
        return {'decision': 'DENY', 'code': 'ALLOC_BAD_CLASS'}

    wl = request.get('workload_class', 'throughput_heavy')
    prio = WORKLOAD_PRIORITY.get(wl, 50)
    alloc = VM_CLASSES[vm_class]

    return {
        'decision': 'ALLOCATE',
        'vcpu': alloc['vcpu'],
        'mem_mb': alloc['mem_mb'],
        'priority': prio,
        'code': 'ALLOC_OK'
    }
