from sqlalchemy.orm import Session

from control_plane.app.models.agent import Agent
from control_plane.app.models.heartbeat import AgentHeartbeat
from control_plane.app.models.node import Node


class FleetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_node_by_uid(self, node_uid: str) -> Node | None:
        return self.db.query(Node).filter(Node.node_uid == node_uid).first()

    def create_node(self, node: Node) -> Node:
        self.db.add(node)
        self.db.flush()
        return node

    def create_agent(self, agent: Agent) -> Agent:
        self.db.add(agent)
        self.db.flush()
        return agent

    def get_agent_by_uid(self, tenant_id: str, agent_uid: str) -> Agent | None:
        return self.db.query(Agent).filter(Agent.agent_uid == agent_uid, Agent.tenant_id == tenant_id).first()

    def list_nodes(self, tenant_id: str) -> list[Node]:
        return list(self.db.query(Node).filter(Node.tenant_id == tenant_id).order_by(Node.hostname.asc()).all())

    def list_agents(self, tenant_id: str) -> list[Agent]:
        return list(self.db.query(Agent).filter(Agent.tenant_id == tenant_id).order_by(Agent.created_at.desc()).all())

    def record_heartbeat(self, heartbeat: AgentHeartbeat) -> AgentHeartbeat:
        self.db.add(heartbeat)
        self.db.flush()
        return heartbeat
