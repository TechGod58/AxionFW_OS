from allocator import decide


def test_allocate_ok():
    out = decide({'vm_class': 'small', 'workload_class': 'latency_sensitive'}, {'cpu_used': 0.2, 'mem_used': 0.4})
    assert out['decision'] == 'ALLOCATE'


def test_queue_under_pressure():
    out = decide({'vm_class': 'small', 'workload_class': 'throughput_heavy'}, {'cpu_used': 0.9, 'mem_used': 0.4})
    assert out['decision'] == 'QUEUE'
