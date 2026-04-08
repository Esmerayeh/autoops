import psutil


class ProcessMetricsCollector:
    name = "process_metrics"

    def collect(self) -> dict:
        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                info = proc.info
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            processes.append(info)
        return {"processes": processes[:20]}
