import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from control_plane.app.core.db import SessionLocal
from control_plane.app.core.logging import configure_logging
from control_plane.app.messaging.publishers import EventPublisher
from control_plane.app.messaging.redis_streams import RedisStreamsBus
from control_plane.app.messaging.topics import TELEMETRY_STREAM
from control_plane.app.models.alert import Alert
from control_plane.app.models.incident import Incident
from control_plane.app.models.topology import DependencyEdge, Service


LOGGER = logging.getLogger(__name__)
GROUP_NAME = "telemetry-workers"
CONSUMER_NAME = "telemetry-ingest-1"


def _upsert_service(db: Session, tenant_id: str, node_id: str, service_data: dict[str, Any]) -> Service:
    service_key = service_data.get("service_key") or service_data.get("name", "unknown")
    service = (
        db.query(Service)
        .filter(Service.tenant_id == tenant_id, Service.node_id == node_id, Service.service_key == service_key)
        .first()
    )
    if not service:
        service = Service(
            tenant_id=tenant_id,
            node_id=node_id,
            service_key=service_key,
            name=service_data.get("name", service_key),
            category=service_data.get("category", "process"),
            status=service_data.get("status", "unknown"),
            metadata_json=service_data,
        )
        db.add(service)
        db.flush()
    else:
        service.status = service_data.get("status", service.status)
        service.metadata_json = service_data
    return service


def _record_cpu_incident(db: Session, tenant_id: str, payload: dict[str, Any]) -> Incident | None:
    cpu_percent = payload.get("cpu_percent", 0)
    if cpu_percent < 90:
        return None

    dedupe_key = f"{tenant_id}:cpu:critical"
    alert = db.query(Alert).filter(Alert.tenant_id == tenant_id, Alert.dedupe_key == dedupe_key, Alert.status == "open").first()
    if not alert:
        alert = Alert(
            tenant_id=tenant_id,
            node_id=None,
            service_id=None,
            dedupe_key=dedupe_key,
            severity="critical",
            status="open",
            details_json={"cpu_percent": cpu_percent},
        )
        db.add(alert)

    incident = (
        db.query(Incident)
        .filter(Incident.tenant_id == tenant_id, Incident.incident_key == dedupe_key, Incident.status.in_(["open", "acknowledged"]))
        .first()
    )
    if not incident:
        incident = Incident(
            tenant_id=tenant_id,
            incident_key=dedupe_key,
            severity="critical",
            status="open",
            title="CPU saturation detected",
            summary=f"Fleet telemetry reported CPU at {cpu_percent:.1f}%.",
            root_cause_json={"reason": "high host cpu", "confidence": 0.72},
            affected_nodes_json=[],
        )
        db.add(incident)
    return incident


def _record_topology(db: Session, tenant_id: str, payload: dict[str, Any]) -> bool:
    node_id = payload.get("node_id", "unknown-node")
    service_map: dict[str, Service] = {}
    changed = False
    for service_data in payload.get("services", []):
        service = _upsert_service(db, tenant_id, node_id, service_data)
        service_map[service.service_key] = service
        changed = True

    for connection in payload.get("connections", []):
        source_key = connection.get("source")
        target_key = connection.get("target")
        if not source_key or not target_key or source_key not in service_map or target_key not in service_map:
            continue
        edge = (
            db.query(DependencyEdge)
            .filter(
                DependencyEdge.tenant_id == tenant_id,
                DependencyEdge.source_service_id == service_map[source_key].id,
                DependencyEdge.target_service_id == service_map[target_key].id,
            )
            .first()
        )
        if not edge:
            edge = DependencyEdge(
                tenant_id=tenant_id,
                source_service_id=service_map[source_key].id,
                target_service_id=service_map[target_key].id,
                edge_type=connection.get("edge_type", "network"),
                confidence=float(connection.get("confidence", 0.5)),
                evidence_json=connection,
            )
            db.add(edge)
            changed = True
        else:
            edge.confidence = float(connection.get("confidence", edge.confidence))
            edge.evidence_json = connection
            changed = True
    return changed


def _process_payload(db: Session, publisher: EventPublisher, envelope: dict[str, Any]) -> None:
    tenant_id = envelope["tenant_id"]
    event_type = envelope["event_type"]
    payload = envelope.get("payload", {})
    if event_type == "telemetry.host_metrics":
        incident = _record_cpu_incident(db, tenant_id, payload)
        if incident:
            publisher.bus.publish(
                "autoops.incidents",
                incident.id,
                {
                    "event_id": incident.id,
                    "event_type": "incident.opened",
                    "tenant_id": tenant_id,
                    "source": {"kind": "worker"},
                    "occurred_at": envelope["occurred_at"],
                    "schema_version": 1,
                    "payload": {"incident_id": incident.id, "severity": incident.severity, "title": incident.title},
                },
            )
    elif event_type == "telemetry.discovery":
        if _record_topology(db, tenant_id, payload):
            publisher.bus.publish(
                "autoops.topology",
                envelope["event_id"],
                {
                    "event_id": envelope["event_id"],
                    "event_type": "topology.updated",
                    "tenant_id": tenant_id,
                    "source": {"kind": "worker"},
                    "occurred_at": envelope["occurred_at"],
                    "schema_version": 1,
                    "payload": {"node_id": payload.get("node_id"), "service_count": len(payload.get("services", []))},
                },
            )


def main() -> None:
    configure_logging()
    LOGGER.info("Starting telemetry ingest worker")
    bus = RedisStreamsBus()
    publisher = EventPublisher()
    db = SessionLocal()
    try:
        while True:
            batches = bus.consume(TELEMETRY_STREAM, GROUP_NAME, CONSUMER_NAME, count=20, block_ms=3000)
            if not batches:
                continue
            for stream_name, messages in batches:
                for message_id, fields in messages:
                    try:
                        envelope = json.loads(fields["payload"])
                        _process_payload(db, publisher, envelope)
                        db.commit()
                        bus.ack(stream_name, GROUP_NAME, message_id)
                    except Exception:
                        db.rollback()
                        LOGGER.exception("Failed to process telemetry message %s", message_id)
    finally:
        db.close()


if __name__ == "__main__":
    main()
