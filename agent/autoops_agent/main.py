import time

from .services.enrollment import EnrollmentService
from .services.heartbeat import HeartbeatService
from .services.policy_sync import PolicySyncService
from .services.remediation_runner import RemediationRunnerService
from .services.telemetry import TelemetryService


def main() -> None:
    enrollment_service = EnrollmentService()
    enrollment_service.ensure_registered()

    heartbeat_service = HeartbeatService()
    telemetry_service = TelemetryService()
    policy_service = PolicySyncService()
    remediation_service = RemediationRunnerService()

    while True:
        policy_service.maybe_refresh()
        heartbeat_service.send()
        telemetry_service.collect_and_flush()
        remediation_service.poll_and_execute()
        time.sleep(5)


if __name__ == "__main__":
    main()
