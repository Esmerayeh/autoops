"""Durable runtime settings backed by the database."""

from __future__ import annotations

from flask import Flask

from autoops.extensions import db
from autoops.models import AppSetting


class SettingsService:
    """Persist small mutable runtime settings that must survive worker boundaries."""

    AUTONOMY_MODE_KEY = "autonomy_mode"

    def __init__(self, app: Flask) -> None:
        self.app = app

    def initialize_defaults(self) -> None:
        self._ensure(self.AUTONOMY_MODE_KEY, self.app.config["AUTONOMY_MODE"])

    def get_autonomy_mode(self) -> str:
        value = self.get(self.AUTONOMY_MODE_KEY, self.app.config["AUTONOMY_MODE"])
        return str(value or self.app.config["AUTONOMY_MODE"]).lower()

    def set_autonomy_mode(self, mode: str) -> str:
        normalized = str(mode).lower()
        self.set(self.AUTONOMY_MODE_KEY, normalized)
        self.app.config["AUTONOMY_MODE"] = normalized
        return normalized

    def get(self, key: str, default=None):
        setting = AppSetting.query.filter_by(key=key).first()
        return default if setting is None else setting.value

    def set(self, key: str, value) -> None:
        setting = AppSetting.query.filter_by(key=key).first()
        if setting is None:
            setting = AppSetting(key=key, value=value)
            db.session.add(setting)
        else:
            setting.value = value
        db.session.commit()

    def _ensure(self, key: str, default) -> None:
        if AppSetting.query.filter_by(key=key).first() is None:
            db.session.add(AppSetting(key=key, value=default))
            db.session.commit()
