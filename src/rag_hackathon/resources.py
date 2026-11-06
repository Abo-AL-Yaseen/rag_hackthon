"""Sample process RSS and available system memory, including native tensors."""
import threading
import time

import psutil


class MemoryMonitor:
    def __init__(self, interval=0.05):
        self.interval = interval
        self.process = psutil.Process()
        self.initial_rss = self.process.memory_info().rss
        self.peak_rss = self.initial_rss
        self.min_available = psutil.virtual_memory().available
        self.samples = 0
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self.stop_event.is_set():
            self.peak_rss = max(self.peak_rss, self.process.memory_info().rss)
            self.min_available = min(self.min_available, psutil.virtual_memory().available)
            self.samples += 1
            self.stop_event.wait(self.interval)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop_event.set()
        self.thread.join()

    def result(self):
        return {"initial_rss_bytes": self.initial_rss, "sampled_peak_rss_bytes": self.peak_rss,
                "minimum_system_available_bytes": self.min_available, "samples": self.samples,
                "sampling_interval_seconds": self.interval,
                "limitation": "Sampled RSS can miss peaks between samples; not GPU memory."}
