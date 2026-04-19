import threading, time


def heartbeat_thread(phase, interval=45, sink=print, stop_event=None):
    start = time.time()
    while True:
        if stop_event and stop_event.is_set():
            return
        elapsed = int(time.time() - start)
        sink(f"[rail] HEARTBEAT phase={phase} step=-/- elapsed_s={elapsed}")
        for _ in range(interval):
            if stop_event and stop_event.is_set():
                return
            time.sleep(1)


class HeartbeatContext:
    def __init__(self, phase, interval=45, sink=print):
        self.phase = phase
        self.interval = interval
        self.sink = sink
        self._stop = threading.Event()
        self._t = None

    def __enter__(self):
        self._t = threading.Thread(target=heartbeat_thread, args=(self.phase, self.interval, self.sink, self._stop), daemon=True)
        self._t.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._stop.set()
        if self._t:
            self._t.join(timeout=2)
        return False
