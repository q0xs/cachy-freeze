"""Validated, atomic workstation settings shared by services and the GUI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .catalog import atomic_json_write, atomic_text_write
from .errors import ConfigurationError

DEFAULTS: dict[str, Any] = {
    "schema": 1,
    "retention_count": 20,
    "auto_snapshot_enabled": False,
    "auto_snapshot_interval_minutes": 1440,
    "update_checks_enabled": True,
    "network_online_checks": True,
    "boot_failure_limit": 3,
    "log_retention_lines": 5000,
    "language": "tr",
    "theme": "dark",
}


class SettingsStore:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.path = state_dir / "settings.json"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return dict(DEFAULTS)
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ConfigurationError(f"Settings cannot be read: {error}") from error
        if not isinstance(document, dict):
            raise ConfigurationError("Settings document must be an object")
        merged = {**DEFAULTS, **document}
        self.validate(merged)
        return merged

    def update(self, changes: dict[str, Any]) -> dict[str, Any]:
        unknown = set(changes) - set(DEFAULTS)
        if unknown or "schema" in changes:
            raise ConfigurationError(f"Unknown or immutable settings: {sorted(unknown)}")
        document = {**self.load(), **changes, "schema": 1}
        self.validate(document)
        atomic_json_write(self.path, document, mode=0o644)
        atomic_text_write(
            self.state_dir / "boot-failure-limit",
            f"{document['boot_failure_limit']}\n",
        )
        return document

    @staticmethod
    def validate(document: dict[str, Any]) -> None:
        if document.get("schema") != 1:
            raise ConfigurationError("Unsupported settings schema")
        for name in (
            "auto_snapshot_enabled",
            "update_checks_enabled",
            "network_online_checks",
        ):
            if not isinstance(document.get(name), bool):
                raise ConfigurationError(f"{name} must be true or false")
        ranges = {
            "retention_count": (1, 1000),
            "auto_snapshot_interval_minutes": (15, 10080),
            "boot_failure_limit": (2, 10),
            "log_retention_lines": (100, 100000),
        }
        for name, (minimum, maximum) in ranges.items():
            value = document.get(name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not minimum <= value <= maximum
            ):
                raise ConfigurationError(f"{name} must be between {minimum} and {maximum}")
        if document.get("language") != "tr":
            raise ConfigurationError("This workstation profile supports the tr locale")
        if document.get("theme") not in {"dark", "light"}:
            raise ConfigurationError("theme must be dark or light")
