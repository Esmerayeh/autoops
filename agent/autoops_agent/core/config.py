from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    control_plane_url: str = "http://localhost:8000/api/v1"
    tenant_slug: str = "demo"
    enrollment_token: str = "change-me-agent"
    node_uid: str = "node-local"
    hostname: str = "localhost"
    environment: str = "dev"
    region: str = "local"
    agent_version: str = "0.1.0"
    spool_path: str = str(Path(".agent-spool.db").absolute())
    policy_refresh_seconds: int = 30


settings = AgentSettings()
