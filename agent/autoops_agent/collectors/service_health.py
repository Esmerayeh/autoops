class ServiceHealthCollector:
    name = "service_health"

    def collect(self) -> dict:
        return {"services": []}
