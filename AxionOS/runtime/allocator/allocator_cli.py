import argparse
import json
from allocator import decide
from audit import append_allocation


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vm-class', default='small')
    ap.add_argument('--workload-class', default='throughput_heavy')
    ap.add_argument('--cpu-used', type=float, default=0.30)
    ap.add_argument('--mem-used', type=float, default=0.40)
    ap.add_argument('--corr', default='corr_alloc_demo')
    args = ap.parse_args()

    req = {'vm_class': args.vm_class, 'workload_class': args.workload_class, 'corr': args.corr}
    host = {'cpu_used': args.cpu_used, 'mem_used': args.mem_used}

    out = decide(req, host)
    out['corr'] = args.corr
    append_allocation(out)
    print(json.dumps(out))


if __name__ == '__main__':
    main()
