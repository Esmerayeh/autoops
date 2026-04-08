"""Configuration classes for AutoOps AI."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


class BaseConfig:
    SECRET_KEY = os.getenv("AUTOOPS_SECRET_KEY", "dev-only-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("AUTOOPS_DATABASE_URL", f"sqlite:///{BASE_DIR / 'autoops.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    APP_NAME = "AutoOps AI"
    ENV_NAME = os.getenv("AUTOOPS_ENV", "development")
    JSON_SORT_KEYS = False

    LOG_DIR = BASE_DIR / "logs"
    LOG_FILE = LOG_DIR / "system.log"
    LOG_LEVEL = os.getenv("AUTOOPS_LOG_LEVEL", "INFO").upper()
    JSON_LOGS = _bool("AUTOOPS_JSON_LOGS", False)

    WARNING_THRESHOLD = float(os.getenv("AUTOOPS_WARNING_THRESHOLD", "70"))
    CRITICAL_THRESHOLD = float(os.getenv("AUTOOPS_CRITICAL_THRESHOLD", "85"))
    SAMPLE_INTERVAL_SECONDS = float(os.getenv("AUTOOPS_SAMPLE_INTERVAL_SECONDS", "2"))
    MAX_HISTORY_POINTS = max(60, min(720, int(os.getenv("AUTOOPS_MAX_HISTORY_POINTS", "180"))))
    SNAPSHOT_PERSIST_EVERY = max(1, int(os.getenv("AUTOOPS_SNAPSHOT_PERSIST_EVERY", "3")))
    API_CACHE_TTL_SECONDS = float(os.getenv("AUTOOPS_API_CACHE_TTL_SECONDS", "2"))
    DATA_RETENTION_HOURS = max(24, int(os.getenv("AUTOOPS_DATA_RETENTION_HOURS", "168")))
    LOG_TAIL_LINES = max(50, min(1000, int(os.getenv("AUTOOPS_LOG_TAIL_LINES", "300"))))
    PROCESS_LIST_LIMIT = max(5, min(50, int(os.getenv("AUTOOPS_PROCESS_LIST_LIMIT", "12"))))
    SUSTAINED_BREACH_WINDOW = max(3, int(os.getenv("AUTOOPS_SUSTAINED_BREACH_WINDOW", "5")))

    ENABLE_SELF_HEALING = _bool("AUTOOPS_ENABLE_SELF_HEALING", True)
    HEALING_DRY_RUN = _bool("AUTOOPS_HEALING_DRY_RUN", True)
    HEALING_COOLDOWN_SECONDS = max(10, int(os.getenv("AUTOOPS_HEALING_COOLDOWN_SECONDS", "60")))
    OPERATOR_CONFIRMATION_REQUIRED = _bool("AUTOOPS_OPERATOR_CONFIRMATION_REQUIRED", True)
    AUTONOMY_MODE = os.getenv("AUTOOPS_AUTONOMY_MODE", "assisted")
    MAX_AUTONOMOUS_ACTIONS_PER_HOUR = max(1, int(os.getenv("AUTOOPS_MAX_AUTONOMOUS_ACTIONS_PER_HOUR", "4")))
    DECISION_CONFIDENCE_THRESHOLD = float(os.getenv("AUTOOPS_DECISION_CONFIDENCE_THRESHOLD", "0.72"))
    DECISION_SAFETY_THRESHOLD = float(os.getenv("AUTOOPS_DECISION_SAFETY_THRESHOLD", "0.8"))
    FEEDBACK_LOOKBACK_DAYS = max(1, int(os.getenv("AUTOOPS_FEEDBACK_LOOKBACK_DAYS", "14")))
    ALLOW_WEBHOOKS = _bool("AUTOOPS_ALLOW_WEBHOOKS", False)
    EXTERNAL_WEBHOOK_URL = os.getenv("AUTOOPS_EXTERNAL_WEBHOOK_URL", "")
    SAFE_TEMP_PATH = os.getenv("AUTOOPS_SAFE_TEMP_PATH", str(BASE_DIR / "tmp"))
    DISTRIBUTED_MODE = _bool("AUTOOPS_DISTRIBUTED_MODE", False)
    CLUSTER_NAME = os.getenv("AUTOOPS_CLUSTER_NAME", "autoops-local-cluster")
    NODE_ID = os.getenv("AUTOOPS_NODE_ID", os.getenv("HOSTNAME") or os.getenv("COMPUTERNAME") or "autoops-node-1")
    NODE_NAME = os.getenv("AUTOOPS_NODE_NAME", NODE_ID)
    NODE_ROLE = os.getenv("AUTOOPS_NODE_ROLE", "control-plane")
    NODE_REGION = os.getenv("AUTOOPS_NODE_REGION", "local")
    NODE_ENVIRONMENT = os.getenv("AUTOOPS_NODE_ENVIRONMENT", ENV_NAME)
    NODE_HEARTBEAT_TTL_SECONDS = max(10, int(os.getenv("AUTOOPS_NODE_HEARTBEAT_TTL_SECONDS", "30")))
    CLUSTER_ALLOW_REMOTE_AGENTS = _bool("AUTOOPS_CLUSTER_ALLOW_REMOTE_AGENTS", False)
    STREAM_BACKEND = os.getenv("AUTOOPS_STREAM_BACKEND", "inmemory")
    TENANCY_ENABLED = _bool("AUTOOPS_TENANCY_ENABLED", False)
    DEFAULT_TENANT = os.getenv("AUTOOPS_DEFAULT_TENANT", "default")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("AUTOOPS_COOKIE_SECURE", False)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = _bool("AUTOOPS_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8

    LOGIN_RATE_LIMIT = os.getenv("AUTOOPS_LOGIN_RATE_LIMIT", "5 per minute")
    API_RATE_LIMIT = os.getenv("AUTOOPS_API_RATE_LIMIT", "120 per minute")
    ACCOUNT_LOCKOUT_MINUTES = max(1, int(os.getenv("AUTOOPS_ACCOUNT_LOCKOUT_MINUTES", "15")))
    MAX_FAILED_LOGINS = max(3, int(os.getenv("AUTOOPS_MAX_FAILED_LOGINS", "5")))

    DEFAULT_ADMIN_USERNAME = os.getenv("AUTOOPS_DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.getenv("AUTOOPS_DEFAULT_ADMIN_PASSWORD", "admin123!")
    DEFAULT_ADMIN_ROLE = "admin"
    ENABLE_SIGNUP = _bool("AUTOOPS_ENABLE_SIGNUP", True)
    START_BACKGROUND_SAMPLER = True

    WTF_CSRF_TIME_LIMIT = None

    HEALING_ALLOWLIST = [item.strip().lower() for item in os.getenv("AUTOOPS_HEALING_ALLOWLIST", "").split(",") if item.strip()]
    HEALING_BLOCKLIST = [
        item.strip().lower()
        for item in os.getenv(
            "AUTOOPS_HEALING_BLOCKLIST",
            "system,system idle process,idle,registry,csrss.exe,wininit.exe,winlogon.exe,services.exe,lsass.exe,smss.exe,svchost.exe,explorer.exe,init,systemd",
        ).split(",")
        if item.strip()
    ]
    HEALING_PROTECTED_PIDS = {
        int(item.strip())
        for item in os.getenv("AUTOOPS_HEALING_PROTECTED_PIDS", "0,1").split(",")
        if item.strip().isdigit()
    }
    HEALING_POLICY_FILE = os.getenv("AUTOOPS_HEALING_POLICY_FILE", str(BASE_DIR / "autoops" / "healing" / "policies.json"))

    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self';"
        ),
    }


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    ENV_NAME = "development"


class ProductionConfig(BaseConfig):
    DEBUG = False
    ENV_NAME = "production"
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = False
    ENV_NAME = "testing"
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    ENABLE_SELF_HEALING = False
    HEALING_DRY_RUN = True
    LOGIN_RATE_LIMIT = "1000 per minute"
    API_RATE_LIMIT = "1000 per minute"
    MAX_HISTORY_POINTS = 60
    START_BACKGROUND_SAMPLER = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
