from datetime import UTC, datetime

from control_plane.app.messaging.redis_streams import RedisStreamsBus
from control_plane.app.messaging.topics import AUDIT_STREAM, REMEDIATION_STREAM, TELEMETRY_STREAM


class EventPublisher:
    def __init__(self) -> None:
        self.bus = RedisStreamsBus()

    def publish_telemetry(
        self,
        tenant_id: str,
        agent_uid: str,
        event_type: str,
        payload: dict,
        event_id: str,
        occurred_at: str,
    ) -> str:
        return self.bus.publish(
            TELEMETRY_STREAM,
            event_id,
            {
                "event_id": event_id,
                "event_type": f"telemetry.{event_type}",
                "tenant_id": tenant_id,
                "source": {"kind": "agent", "agent_id": agent_uid},
                "occurred_at": occurred_at,
                "schema_version": 1,
                "payload": payload,
            },
        )

    def publish_remediation(self, tenant_id: str, action_id: str, payload: dict, action_type: str, target_node_id: str | None) -> str:
        return self.bus.publish(
            REMEDIATION_STREAM,
            action_id,
            {
                "event_id": action_id,
                "event_type": "remediation.requested",
                "tenant_id": tenant_id,
                "source": {"kind": "control_plane", "node_id": target_node_id},
                "occurred_at": datetime.now(UTC).isoformat(),
                "schema_version": 1,
                "payload": {"action_type": action_type, "request": payload},
            },
        )

    def publish_audit(
        self,
        tenant_id: str,
        action: str,
        actor_id: str | None,
        outcome: str,
        resource_type: str,
        resource_id: str | None,
    ) -> str:
        event_id = f"audit-{datetime.now(UTC).timestamp()}"
        return self.bus.publish(
            AUDIT_STREAM,
            event_id,
            {
                "event_id": event_id,
                "event_type": "audit.recorded",
                "tenant_id": tenant_id,
                "source": {"kind": "control_plane", "actor_id": actor_id},
                "occurred_at": datetime.now(UTC).isoformat(),
                "schema_version": 1,
                "payload": {
                    "action": action,
                    "outcome": outcome,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                },
            },
        )
