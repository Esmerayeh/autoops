from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings for the distributed control plane."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AutoOps AI Control Plane"
    app_version: str = "0.1.0"
    app_env: str = "development"

    database_url: str = "postgresql+psycopg://autoops:autoops@localhost:5432/autoops"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = 60

    bootstrap_token: str = "change-me-bootstrap"
    bootstrap_admin_email: str = "admin@local.autoops"
    bootstrap_admin_password: str = "admin123!"
    enable_bootstrap_admin: bool = True
    agent_enrollment_secret: str = "change-me-agent"

    telemetry_stream: str = "autoops.telemetry"
    heartbeat_stream: str = "autoops.heartbeats"
    incident_stream: str = "autoops.incidents"
    topology_stream: str = "autoops.topology"
    remediation_stream: str = "autoops.remediation"
    audit_stream: str = "autoops.audit"


settings = Settings()
