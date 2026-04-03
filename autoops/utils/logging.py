"""Logging configuration helpers."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask


class JsonFormatter(logging.Formatter):
    """Simple structured JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(app: Flask) -> None:
    """Attach console and file handlers with optional JSON logging."""
    log_dir = Path(app.config["LOG_DIR"])
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = Path(app.config["LOG_FILE"])

    formatter: logging.Formatter
    if app.config["JSON_LOGS"]:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s %(message)s")

    root = logging.getLogger()
    root.setLevel(getattr(logging, app.config["LOG_LEVEL"], logging.INFO))
    root.handlers.clear()

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    app.logger.setLevel(root.level)
