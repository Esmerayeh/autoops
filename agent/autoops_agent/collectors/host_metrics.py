import psutil


class HostMetricsCollector:
    name = "host_metrics"

    def collect(self) -> dict:
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }
