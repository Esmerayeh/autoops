"""Runtime coordination for sampler and request timing."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

from flask import Flask, g

from autoops.distributed import DistributedControlPlaneService
from autoops.monitoring.service import MonitoringService


@dataclass
class RuntimeManager:
    monitoring_service: MonitoringService | None = None
    control_plane_service: DistributedControlPlaneService | None = None
    started: bool = False
    startup_lock: threading.Lock = field(default_factory=threading.Lock)

    def start(self, app: Flask) -> None:
        """Start background services once."""
        with self.startup_lock:
            if self.started:
                return
            self.monitoring_service = MonitoringService(app)
            self.control_plane_service = DistributedControlPlaneService(app)
            self.monitoring_service.control_plane = self.control_plane_service
            self.control_plane_service.ensure_local_node()
            if app.config.get("START_BACKGROUND_SAMPLER", True):
                self.monitoring_service.start()
            self.started = True
            logging.getLogger(__name__).info("AutoOps runtime services started.")

    def mark_request_start(self) -> None:
        g.request_started_at = time.perf_counter()

    def record_request(self, status_code: int) -> None:
        started_at = getattr(g, "request_started_at", None)
        if started_at is None or not self.monitoring_service:
            return
        latency_ms = (time.perf_counter() - started_at) * 1000
        self.monitoring_service.record_request_latency(latency_ms, status_code)


runtime_manager = RuntimeManager()
