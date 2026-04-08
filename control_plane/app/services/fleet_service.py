import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from control_plane.app.core.security import create_token
from control_plane.app.models.agent import Agent
from control_plane.app.models.heartbeat import AgentHeartbeat
from control_plane.app.models.node import Node
from control_plane.app.repositories.fleet_repo import FleetRepository
from control_plane.app.repositories.tenant_repo import TenantRepository


class FleetService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.fleet_repo = FleetRepository(db)
        self.tenant_repo = TenantRepository(db)

    def register_agent(self, tenant_slug: str, payload: dict) -> dict:
        tenant = self.tenant_repo.get_by_slug(tenant_slug)
        if not tenant:
            raise ValueError("Unknown tenant")
        tenant_id = tenant.id
        node = self.fleet_repo.get_node_by_uid(payload["node_uid"])
        if not node:
            node = Node(
                tenant_id=tenant_id,
                node_uid=payload["node_uid"],
                hostname=payload["hostname"],
                display_name=payload["hostname"],
                environment=payload["environment"],
                region=payload["region"],
                status="online",
                metadata_json={},
            )
            self.fleet_repo.create_node(node)

        agent = Agent(
            tenant_id=tenant_id,
            node_id=node.id,
            agent_uid=str(uuid.uuid4()),
            version=payload["agent_version"],
            status="online",
            capabilities_json=payload.get("capabilities", {}),
        )
        self.fleet_repo.create_agent(agent)
        self.db.commit()

        return {
            "agent_id": agent.agent_uid,
            "node_id": node.id,
            "agent_token": create_token(agent.agent_uid, tenant_id, ["agent:write"], token_type="agent"),
            "policy_version": 1,
        }

    def record_heartbeat(self, tenant_id: str, agent_uid: str, payload: dict) -> dict:
        agent = self.fleet_repo.get_agent_by_uid(tenant_id, agent_uid)
        if not agent:
            raise ValueError("Unknown agent")

        heartbeat = AgentHeartbeat(
            tenant_id=tenant_id,
            agent_id=agent.id,
            node_id=agent.node_id,
            received_at=datetime.now(UTC),
            health_status=payload["status"],
            metrics_json=payload.get("metrics", {}),
        )
        agent.status = payload["status"]
        self.fleet_repo.record_heartbeat(heartbeat)
        self.db.commit()
        return {"accepted": True, "next_policy_version": 1}

    def get_fleet_overview(self, tenant_id: str) -> dict:
        nodes = self.fleet_repo.list_nodes(tenant_id)
        agents = self.fleet_repo.list_agents(tenant_id)
        unhealthy_agents = [agent for agent in agents if agent.status != "healthy" and agent.status != "online"]
        return {
            "node_count": len(nodes),
            "agent_count": len(agents),
            "unhealthy_agent_count": len(unhealthy_agents),
            "nodes": nodes,
            "agents": agents,
        }
