"""Durable transaction metadata and bounded structured audit logging."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import IntegrityError


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_json_write(path: Path, value: Any, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_text_write(path: Path, value: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


class OperationJournal:
    """Record only the in-flight baseline transaction; never user data."""

    SCHEMA = 2
    _PHASES = {
        "preparing",
        "prepared",
        "golden-committed",
        "active-committed",
        "boot-committed",
    }

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.path = state_dir / "transaction.json"

    def begin(self, *, baseline_id: str, source_subvolume: str) -> dict[str, Any]:
        if self.path.exists():
            raise IntegrityError("A CachyFreeze transaction is already pending")
        document = {
            "schema": self.SCHEMA,
            "kind": "publish",
            "phase": "preparing",
            "baseline_id": baseline_id,
            "source_subvolume": source_subvolume,
            "started_at": datetime.now(UTC).isoformat(),
        }
        atomic_json_write(self.path, document)
        return document

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise IntegrityError(f"Transaction journal cannot be read: {error}") from error
        if document.get("schema") != self.SCHEMA:
            raise IntegrityError("Unsupported transaction journal schema")
        if document.get("kind") != "publish":
            raise IntegrityError("Unsupported transaction kind")
        if document.get("phase") not in self._PHASES:
            raise IntegrityError("Unsupported transaction phase")
        baseline_id = document.get("baseline_id")
        if not isinstance(baseline_id, str) or len(baseline_id) != 32:
            raise IntegrityError("Transaction baseline identity is invalid")
        if document.get("source_subvolume") != "@":
            raise IntegrityError("Transaction source identity is invalid")
        return document

    def set_phase(self, phase: str) -> None:
        if phase not in self._PHASES:
            raise IntegrityError(f"Invalid transaction phase: {phase}")
        document = self.load()
        if document is None:
            raise IntegrityError("Transaction journal is missing")
        document["phase"] = phase
        atomic_json_write(self.path, document)

    def finish(self) -> None:
        self.path.unlink(missing_ok=True)
        if self.state_dir.exists():
            _fsync_directory(self.state_dir)


class AuditLogger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, level: str, action: str, message: str, **context: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level.upper(),
            "action": action,
            "message": message,
            "context": context,
        }
        descriptor = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o640)
        try:
            payload = (json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n").encode()
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
