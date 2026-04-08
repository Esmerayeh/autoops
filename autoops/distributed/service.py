"""Cluster-ready control plane services for a distributed AutoOps MVP."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from flask import Flask

from autoops.extensions import db
from autoops.models import ClusterNode, OrchestrationTask, ServiceDependency


class DistributedControlPlaneService:
    """Provides a small, local-first control plane for future multi-node expansion."""

    def __init__(self, app: Flask) -> None:
        self.app = app
        self.cluster_name = app.config["CLUSTER_NAME"]
        self.tenant_id = app.config["DEFAULT_TENANT"]

    def ensure_local_node(self) -> None:
        node = ClusterNode.query.filter_by(node_id=self.app.config["NODE_ID"]).first()
        if node is None:
            node = ClusterNode(
                node_id=self.app.config["NODE_ID"],
                tenant_id=self.tenant_id,
                cluster_name=self.cluster_name,
                node_name=self.app.config["NODE_NAME"],
                role=self.app.config["NODE_ROLE"],
                environment=self.app.config["NODE_ENVIRONMENT"],
                region=self.app.config["NODE_REGION"],
                status="online",
                capabilities=self._default_capabilities(),
                metadata_payload={
                    "stream_backend": self.app.config["STREAM_BACKEND"],
                    "distributed_mode": self.app.config["DISTRIBUTED_MODE"],
                },
            )
            db.session.add(node)
            db.session.commit()
        self._ensure_default_dependency_map()

    def _default_capabilities(self) -> dict[str, Any]:
        return {
            "monitoring": True,
            "analytics": True,
            "healing": True,
            "incidents": True,
            "control_plane": self.app.config["NODE_ROLE"] == "control-plane",
        }

    def _ensure_default_dependency_map(self) -> None:
        default_edges = [
            ("dashboard-ui", "api-gateway", "http"),
            ("api-gateway", "monitoring-service", "internal"),
            ("monitoring-service", "analytics-engine", "internal"),
            ("monitoring-service", "decision-engine", "internal"),
            ("decision-engine", "healing-engine", "internal"),
            ("monitoring-service", "sqlite-store", "storage"),
        ]
        for source, target, dependency_type in default_edges:
            edge = ServiceDependency.query.filter_by(
                tenant_id=self.tenant_id,
                cluster_name=self.cluster_name,
                source=source,
                target=target,
            ).first()
            if edge is None:
                db.session.add(
                    ServiceDependency(
                        tenant_id=self.tenant_id,
                        cluster_name=self.cluster_name,
                        source=source,
                        target=target,
                        dependency_type=dependency_type,
                        confidence=0.86,
                        metadata_payload={"seeded": True},
                    )
                )
        db.session.commit()

    def heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        node_id = str(payload.get("node_id") or "").strip()
        if not node_id:
            raise ValueError("node_id is required")
        node = ClusterNode.query.filter_by(node_id=node_id).first()
        if node is None:
            if not self.app.config["CLUSTER_ALLOW_REMOTE_AGENTS"]:
                raise PermissionError("remote agent registration is disabled")
            node = ClusterNode(
                node_id=node_id,
                tenant_id=str(payload.get("tenant_id") or self.tenant_id),
                cluster_name=str(payload.get("cluster_name") or self.cluster_name),
                node_name=str(payload.get("node_name") or node_id),
                role=str(payload.get("role") or "agent"),
                environment=str(payload.get("environment") or self.app.config["NODE_ENVIRONMENT"]),
                region=str(payload.get("region") or "unknown"),
                status="online",
            )
            db.session.add(node)

        node.node_name = str(payload.get("node_name") or node.node_name)
        node.role = str(payload.get("role") or node.role)
        node.environment = str(payload.get("environment") or node.environment)
        node.region = str(payload.get("region") or node.region)
        node.status = str(payload.get("status") or "online")
        node.capabilities = payload.get("capabilities") or node.capabilities
        node.latest_metrics = payload.get("latest_metrics") or node.latest_metrics
        node.metadata_payload = payload.get("metadata") or node.metadata_payload
        node.last_seen_at = datetime.now(timezone.utc)
        db.session.commit()
        return self.serialize_node(node)

    def update_local_node_snapshot(self, metrics: dict[str, Any]) -> None:
        node = ClusterNode.query.filter_by(node_id=self.app.config["NODE_ID"]).first()
        if node is None:
            self.ensure_local_node()
            node = ClusterNode.query.filter_by(node_id=self.app.config["NODE_ID"]).first()
        if node is None:
            return
        node.status = "online"
        node.last_seen_at = datetime.now(timezone.utc)
        node.latest_metrics = {
            "cpu": metrics.get("cpu"),
            "memory": metrics.get("memory"),
            "disk": metrics.get("disk"),
            "swap": metrics.get("swap"),
            "process_count": metrics.get("process_count"),
        }
        db.session.commit()

    def get_nodes(self, limit: int = 50) -> list[dict[str, Any]]:
        self._mark_stale_nodes()
        nodes = (
            ClusterNode.query.filter_by(cluster_name=self.cluster_name)
            .order_by(ClusterNode.last_seen_at.desc())
            .limit(limit)
            .all()
        )
        return [self.serialize_node(node) for node in nodes]

    def get_dependency_map(self) -> list[dict[str, Any]]:
        edges = (
            ServiceDependency.query.filter_by(cluster_name=self.cluster_name)
            .order_by(ServiceDependency.source.asc(), ServiceDependency.target.asc())
            .all()
        )
        return [
            {
                "id": edge.id,
                "source": edge.source,
                "target": edge.target,
                "dependency_type": edge.dependency_type,
                "confidence": round(edge.confidence, 3),
                "last_seen_at": edge.last_seen_at.isoformat().replace("+00:00", "Z"),
                "metadata": edge.metadata_payload or {},
            }
            for edge in edges
        ]

    def create_task(self, task_type: str, target_node_id: str | None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        task = OrchestrationTask(
            tenant_id=self.tenant_id,
            cluster_name=self.cluster_name,
            task_type=task_type,
            target_node_id=target_node_id,
            execution_mode="simulated",
            payload=payload or {},
            status="queued",
            result_payload={"message": "Task recorded for distributed MVP orchestration simulation."},
        )
        db.session.add(task)
        db.session.commit()
        return self.serialize_task(task)

    def get_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        tasks = (
            OrchestrationTask.query.filter_by(cluster_name=self.cluster_name)
            .order_by(OrchestrationTask.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self.serialize_task(task) for task in tasks]

    def get_cluster_overview(self) -> dict[str, Any]:
        self._mark_stale_nodes()
        nodes = self.get_nodes(limit=200)
        online = [node for node in nodes if node["status"] == "online"]
        return {
            "cluster_name": self.cluster_name,
            "tenant_id": self.tenant_id,
            "distributed_mode": self.app.config["DISTRIBUTED_MODE"],
            "stream_backend": self.app.config["STREAM_BACKEND"],
            "tenancy_enabled": self.app.config["TENANCY_ENABLED"],
            "control_plane_node_id": self.app.config["NODE_ID"],
            "node_count": len(nodes),
            "online_nodes": len(online),
            "offline_nodes": len(nodes) - len(online),
            "dependency_edges": len(self.get_dependency_map()),
            "queued_tasks": len([task for task in self.get_tasks(limit=100) if task["status"] == "queued"]),
            "capabilities": {
                "agent_collection": True,
                "cluster_orchestration": True,
                "dependency_mapping": True,
                "streaming_backend": self.app.config["STREAM_BACKEND"],
                "distributed_storage_ready": True,
                "rbac_ready": True,
            },
        }

    def serialize_node(self, node: ClusterNode) -> dict[str, Any]:
        return {
            "id": node.id,
            "node_id": node.node_id,
            "tenant_id": node.tenant_id,
            "cluster_name": node.cluster_name,
            "node_name": node.node_name,
            "role": node.role,
            "environment": node.environment,
            "region": node.region,
            "status": node.status,
            "last_seen_at": node.last_seen_at.isoformat().replace("+00:00", "Z"),
            "capabilities": node.capabilities or {},
            "latest_metrics": node.latest_metrics or {},
            "metadata": node.metadata_payload or {},
        }

    def serialize_task(self, task: OrchestrationTask) -> dict[str, Any]:
        return {
            "id": task.id,
            "task_type": task.task_type,
            "target_node_id": task.target_node_id,
            "status": task.status,
            "execution_mode": task.execution_mode,
            "payload": task.payload or {},
            "result": task.result_payload or {},
            "created_at": task.created_at.isoformat().replace("+00:00", "Z"),
            "updated_at": task.updated_at.isoformat().replace("+00:00", "Z"),
        }

    def _mark_stale_nodes(self) -> None:
        stale_before = datetime.now(timezone.utc) - timedelta(seconds=self.app.config["NODE_HEARTBEAT_TTL_SECONDS"])
        stale_nodes = ClusterNode.query.filter(
            ClusterNode.cluster_name == self.cluster_name,
            ClusterNode.last_seen_at < stale_before,
            ClusterNode.status != "offline",
        ).all()
        if not stale_nodes:
            return
        for node in stale_nodes:
            node.status = "offline"
        db.session.commit()
