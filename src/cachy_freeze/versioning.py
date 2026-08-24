"""Application version and durable state-schema migration support."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import __version__ as APP_VERSION
from .catalog import AuditLogger, atomic_json_write
from .errors import IntegrityError

STATE_SCHEMA_VERSION = 2


def _now() -> str:
    return datetime.now(UTC).isoformat()


class StateMigrationManager:
    """Apply ordered, atomic and idempotent persistent-state migrations."""

    def __init__(self, state_dir: Path, logger: AuditLogger) -> None:
        self.state_dir = state_dir
        self.path = state_dir / "schema-version.json"
        self.logger = logger

    def status(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "schema": 1,
                "state_schema": 0,
                "target_state_schema": STATE_SCHEMA_VERSION,
                "application_version": APP_VERSION,
                "migration_required": True,
            }
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise IntegrityError(f"State schema record cannot be read: {error}") from error
        if document.get("schema") != 1:
            raise IntegrityError("Unsupported state schema record format")
        state_schema = document.get("state_schema")
        if not isinstance(state_schema, int) or state_schema < 0:
            raise IntegrityError("The installed state schema version is invalid")
        if state_schema > STATE_SCHEMA_VERSION:
            raise IntegrityError(
                "Persistent state was created by a newer CachyFreeze release; downgrade is blocked."
            )
        return {
            **document,
            "target_state_schema": STATE_SCHEMA_VERSION,
            "application_version": APP_VERSION,
            "migration_required": state_schema < STATE_SCHEMA_VERSION,
        }

    def migrate(self) -> dict[str, Any]:
        """Migrate through every missing schema, recording a version last."""

        self.state_dir.mkdir(parents=True, exist_ok=True)
        before = self.status()
        current = int(before["state_schema"])
        if current == STATE_SCHEMA_VERSION:
            return {**before, "changed": False}

        started_at = _now()
        while current < STATE_SCHEMA_VERSION:
            next_version = current + 1
            self._migrate_one(current, next_version)
            current = next_version

        document = {
            "schema": 1,
            "state_schema": current,
            "application_version": APP_VERSION,
            "migrated_at": _now(),
            "migration_started_at": started_at,
        }
        atomic_json_write(self.path, document, mode=0o600)
        self.logger.write(
            "INFO",
            "state.migrate",
            "Persistent state schema migrated",
            previous_schema=before["state_schema"],
            state_schema=current,
            application_version=APP_VERSION,
        )
        return {
            **document,
            "target_state_schema": STATE_SCHEMA_VERSION,
            "migration_required": False,
            "changed": True,
        }

    @staticmethod
    def _migrate_one(previous: int, target: int) -> None:
        if (previous, target) == (0, 1):
            # Schema 1 formalizes the existing durable files. They already use
            # independent atomic writers, so no legacy content rewrite is needed.
            return
        if (previous, target) == (1, 2):
            # Filesystem-owned snapshot history is validated and removed by
            # FreezeEngine before this version marker is advanced. Schema 2
            # records the minimal two-mode state contract.
            return
        raise IntegrityError(f"No state migration exists for schema {previous} -> {target}")
