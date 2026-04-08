"""initial control plane tables

Revision ID: 20260408_0001
Revises:
Create Date: 2026-04-08 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260408_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cp_tenants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cp_tenants_name", "cp_tenants", ["name"], unique=True)
    op.create_index("ix_cp_tenants_slug", "cp_tenants", ["slug"], unique=True)

    op.create_table(
        "cp_users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_platform_admin", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cp_users_email", "cp_users", ["email"], unique=True)

    op.create_table(
        "cp_roles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_cp_role_name"),
    )
    op.create_index("ix_cp_roles_name", "cp_roles", ["name"], unique=False)
    op.create_index("ix_cp_roles_tenant_id", "cp_roles", ["tenant_id"], unique=False)

    op.create_table(
        "cp_memberships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_cp_membership"),
    )
    op.create_index("ix_cp_memberships_role_id", "cp_memberships", ["role_id"], unique=False)
    op.create_index("ix_cp_memberships_tenant_id", "cp_memberships", ["tenant_id"], unique=False)
    op.create_index("ix_cp_memberships_user_id", "cp_memberships", ["user_id"], unique=False)

    op.create_table(
        "cp_nodes",
        sa.Column("node_uid", sa.String(length=120), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("environment", sa.String(length=32), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("node_group", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cp_nodes_environment", "cp_nodes", ["environment"], unique=False)
    op.create_index("ix_cp_nodes_hostname", "cp_nodes", ["hostname"], unique=False)
    op.create_index("ix_cp_nodes_node_group", "cp_nodes", ["node_group"], unique=False)
    op.create_index("ix_cp_nodes_node_uid", "cp_nodes", ["node_uid"], unique=True)
    op.create_index("ix_cp_nodes_region", "cp_nodes", ["region"], unique=False)
    op.create_index("ix_cp_nodes_status", "cp_nodes", ["status"], unique=False)
    op.create_index("ix_cp_nodes_tenant_id", "cp_nodes", ["tenant_id"], unique=False)

    op.create_table(
        "cp_agents",
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("agent_uid", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("capabilities_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cp_agents_agent_uid", "cp_agents", ["agent_uid"], unique=True)
    op.create_index("ix_cp_agents_node_id", "cp_agents", ["node_id"], unique=False)
    op.create_index("ix_cp_agents_status", "cp_agents", ["status"], unique=False)
    op.create_index("ix_cp_agents_tenant_id", "cp_agents", ["tenant_id"], unique=False)

    op.create_table(
        "cp_policies",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("policy_type", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("rules_json", sa.JSON(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cp_policies_name", "cp_policies", ["name"], unique=False)
    op.create_index("ix_cp_policies_policy_type", "cp_policies", ["policy_type"], unique=False)
    op.create_index("ix_cp_policies_tenant_id", "cp_policies", ["tenant_id"], unique=False)

    op.create_table(
        "cp_incidents",
        sa.Column("incident_key", sa.String(length=160), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("root_cause_json", sa.JSON(), nullable=False),
        sa.Column("affected_nodes_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cp_incidents_incident_key", "cp_incidents", ["incident_key"], unique=False)
    op.create_index("ix_cp_incidents_severity", "cp_incidents", ["severity"], unique=False)
    op.create_index("ix_cp_incidents_status", "cp_incidents", ["status"], unique=False)
    op.create_index("ix_cp_incidents_tenant_id", "cp_incidents", ["tenant_id"], unique=False)

    op.create_table(
        "cp_alerts",
        sa.Column("node_id", sa.String(), nullable=True),
        sa.Column("service_id", sa.String(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=160), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cp_alerts_dedupe_key", "cp_alerts", ["dedupe_key"], unique=False)
    op.create_index("ix_cp_alerts_node_id", "cp_alerts", ["node_id"], unique=False)
    op.create_index("ix_cp_alerts_service_id", "cp_alerts", ["service_id"], unique=False)
    op.create_index("ix_cp_alerts_severity", "cp_alerts", ["severity"], unique=False)
    op.create_index("ix_cp_alerts_status", "cp_alerts", ["status"], unique=False)
    op.create_index("ix_cp_alerts_tenant_id", "cp_alerts", ["tenant_id"], unique=False)

    op.create_table(
        "cp_remediation_actions",
        sa.Column("incident_id", sa.String(), nullable=True),
        sa.Column("target_node_id", sa.String(), nullable=True),
        sa.Column("policy_id", sa.String(), nullable=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("approval_status", sa.String(length=32), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cp_remediation_actions_action_type", "cp_remediation_actions", ["action_type"], unique=False)
    op.create_index("ix_cp_remediation_actions_approval_status", "cp_remediation_actions", ["approval_status"], unique=False)
    op.create_index("ix_cp_remediation_actions_incident_id", "cp_remediation_actions", ["incident_id"], unique=False)
    op.create_index("ix_cp_remediation_actions_policy_id", "cp_remediation_actions", ["policy_id"], unique=False)
    op.create_index("ix_cp_remediation_actions_status", "cp_remediation_actions", ["status"], unique=False)
    op.create_index("ix_cp_remediation_actions_target_node_id", "cp_remediation_actions", ["target_node_id"], unique=False)
    op.create_index("ix_cp_remediation_actions_tenant_id", "cp_remediation_actions", ["tenant_id"], unique=False)

    op.create_table(
        "cp_services",
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("service_key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cp_services_category", "cp_services", ["category"], unique=False)
    op.create_index("ix_cp_services_name", "cp_services", ["name"], unique=False)
    op.create_index("ix_cp_services_node_id", "cp_services", ["node_id"], unique=False)
    op.create_index("ix_cp_services_service_key", "cp_services", ["service_key"], unique=False)
    op.create_index("ix_cp_services_tenant_id", "cp_services", ["tenant_id"], unique=False)

    op.create_table(
        "cp_dependency_edges",
        sa.Column("source_service_id", sa.String(), nullable=False),
        sa.Column("target_service_id", sa.String(), nullable=False),
        sa.Column("edge_type", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "source_service_id", "target_service_id", name="uq_cp_dependency_edge"),
    )
    op.create_index("ix_cp_dependency_edges_edge_type", "cp_dependency_edges", ["edge_type"], unique=False)
    op.create_index("ix_cp_dependency_edges_source_service_id", "cp_dependency_edges", ["source_service_id"], unique=False)
    op.create_index("ix_cp_dependency_edges_target_service_id", "cp_dependency_edges", ["target_service_id"], unique=False)
    op.create_index("ix_cp_dependency_edges_tenant_id", "cp_dependency_edges", ["tenant_id"], unique=False)

    op.create_table(
        "cp_telemetry_batches",
        sa.Column("batch_id", sa.String(length=160), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cp_telemetry_batches_agent_id", "cp_telemetry_batches", ["agent_id"], unique=False)
    op.create_index("ix_cp_telemetry_batches_batch_id", "cp_telemetry_batches", ["batch_id"], unique=True)
    op.create_index("ix_cp_telemetry_batches_tenant_id", "cp_telemetry_batches", ["tenant_id"], unique=False)

    op.create_table(
        "cp_telemetry_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("telemetry_batch_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("occurred_at", sa.String(length=40), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cp_telemetry_events_event_type", "cp_telemetry_events", ["event_type"], unique=False)
    op.create_index("ix_cp_telemetry_events_occurred_at", "cp_telemetry_events", ["occurred_at"], unique=False)
    op.create_index("ix_cp_telemetry_events_tenant_id", "cp_telemetry_events", ["tenant_id"], unique=False)
    op.create_index("ix_cp_telemetry_events_telemetry_batch_id", "cp_telemetry_events", ["telemetry_batch_id"], unique=False)

    op.create_table(
        "cp_enrollment_tokens",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=120), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cp_enrollment_tokens_tenant_id", "cp_enrollment_tokens", ["tenant_id"], unique=False)
    op.create_index("ix_cp_enrollment_tokens_token_hash", "cp_enrollment_tokens", ["token_hash"], unique=True)

    op.create_table(
        "cp_audit_records",
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=120), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.String(length=120), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cp_audit_records_action", "cp_audit_records", ["action"], unique=False)
    op.create_index("ix_cp_audit_records_actor_id", "cp_audit_records", ["actor_id"], unique=False)
    op.create_index("ix_cp_audit_records_actor_type", "cp_audit_records", ["actor_type"], unique=False)
    op.create_index("ix_cp_audit_records_outcome", "cp_audit_records", ["outcome"], unique=False)
    op.create_index("ix_cp_audit_records_resource_id", "cp_audit_records", ["resource_id"], unique=False)
    op.create_index("ix_cp_audit_records_resource_type", "cp_audit_records", ["resource_type"], unique=False)
    op.create_index("ix_cp_audit_records_tenant_id", "cp_audit_records", ["tenant_id"], unique=False)

    op.create_table(
        "cp_agent_heartbeats",
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("health_status", sa.String(length=32), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cp_agent_heartbeats_agent_id", "cp_agent_heartbeats", ["agent_id"], unique=False)
    op.create_index("ix_cp_agent_heartbeats_health_status", "cp_agent_heartbeats", ["health_status"], unique=False)
    op.create_index("ix_cp_agent_heartbeats_node_id", "cp_agent_heartbeats", ["node_id"], unique=False)
    op.create_index("ix_cp_agent_heartbeats_received_at", "cp_agent_heartbeats", ["received_at"], unique=False)
    op.create_index("ix_cp_agent_heartbeats_tenant_id", "cp_agent_heartbeats", ["tenant_id"], unique=False)


def downgrade() -> None:
    for table in [
        "cp_agent_heartbeats",
        "cp_audit_records",
        "cp_enrollment_tokens",
        "cp_telemetry_events",
        "cp_telemetry_batches",
        "cp_dependency_edges",
        "cp_services",
        "cp_remediation_actions",
        "cp_alerts",
        "cp_incidents",
        "cp_policies",
        "cp_agents",
        "cp_nodes",
        "cp_memberships",
        "cp_roles",
        "cp_users",
        "cp_tenants",
    ]:
        op.drop_table(table)
