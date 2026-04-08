class DiscoveryCollector:
    name = "discovery"

    def collect(self) -> dict:
        return {"services": [], "connections": []}
