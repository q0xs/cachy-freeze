"""Atomic snapshot metadata catalog and structured audit log."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import IntegrityError
from .models import SnapshotMetadata

CATALOG_SCHEMA = 1


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


class SnapshotCatalog:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.path = state_dir / "snapshots.json"
        self.transaction_path = state_dir / "transaction.json"

    def _document(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema": CATALOG_SCHEMA, "snapshots": []}
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise IntegrityError(f"Snapshot catalog cannot be read: {error}") from error
        if document.get("schema") != CATALOG_SCHEMA:
            raise IntegrityError("Unsupported snapshot catalog schema")
        if not isinstance(document.get("snapshots"), list):
            raise IntegrityError("Snapshot catalog has an invalid snapshots list")
        return document

    def list(self) -> list[SnapshotMetadata]:
        snapshots = [SnapshotMetadata.from_dict(item) for item in self._document()["snapshots"]]
        return sorted(snapshots, key=lambda item: item.created_at, reverse=True)

    def get(self, snapshot_id: str) -> SnapshotMetadata:
        for snapshot in self.list():
            if snapshot.snapshot_id == snapshot_id:
                return snapshot
        raise IntegrityError(f"Snapshot is not present in the catalog: {snapshot_id}")

    def add(self, snapshot: SnapshotMetadata) -> None:
        document = self._document()
        if any(item.get("snapshot_id") == snapshot.snapshot_id for item in document["snapshots"]):
            raise IntegrityError(f"Duplicate snapshot id: {snapshot.snapshot_id}")
        document["snapshots"].append(snapshot.to_dict())
        atomic_json_write(self.path, document, mode=0o644)

    def remove(self, snapshot_id: str) -> SnapshotMetadata:
        document = self._document()
        removed: SnapshotMetadata | None = None
        kept: list[dict[str, Any]] = []
        for item in document["snapshots"]:
            if item.get("snapshot_id") == snapshot_id:
                removed = SnapshotMetadata.from_dict(item)
            else:
                kept.append(item)
        if removed is None:
            raise IntegrityError(f"Snapshot is not present in the catalog: {snapshot_id}")
        document["snapshots"] = kept
        atomic_json_write(self.path, document, mode=0o644)
        return removed

    def increment_rollback(self, snapshot_id: str) -> SnapshotMetadata:
        document = self._document()
        updated: SnapshotMetadata | None = None
        for index, item in enumerate(document["snapshots"]):
            snapshot = SnapshotMetadata.from_dict(item)
            if snapshot.snapshot_id == snapshot_id:
                updated = replace(snapshot, rollback_count=snapshot.rollback_count + 1)
                document["snapshots"][index] = updated.to_dict()
                break
        if updated is None:
            raise IntegrityError(f"Snapshot is not present in the catalog: {snapshot_id}")
        atomic_json_write(self.path, document, mode=0o644)
        return updated

    def set_health(self, snapshot_id: str, health: str) -> SnapshotMetadata:
        if health not in {"healthy", "warning", "error"}:
            raise IntegrityError(f"Invalid snapshot health: {health}")
        document = self._document()
        updated: SnapshotMetadata | None = None
        for index, item in enumerate(document["snapshots"]):
            snapshot = SnapshotMetadata.from_dict(item)
            if snapshot.snapshot_id == snapshot_id:
                updated = replace(snapshot, health=health)
                document["snapshots"][index] = updated.to_dict()
                break
        if updated is None:
            raise IntegrityError(f"Snapshot is not present in the catalog: {snapshot_id}")
        atomic_json_write(self.path, document, mode=0o644)
        return updated

    def begin_transaction(self, kind: str, phase: str, details: dict[str, Any]) -> None:
        atomic_json_write(
            self.transaction_path,
            {
                "schema": 1,
                "kind": kind,
                "phase": phase,
                "started_at": datetime.now(UTC).isoformat(),
                "details": details,
            },
        )

    def set_transaction_phase(self, phase: str) -> None:
        if not self.transaction_path.exists():
            raise IntegrityError("Transaction journal is missing")
        document = json.loads(self.transaction_path.read_text(encoding="utf-8"))
        document["phase"] = phase
        atomic_json_write(self.transaction_path, document)

    def transaction(self) -> dict[str, Any] | None:
        if not self.transaction_path.exists():
            return None
        try:
            document = json.loads(self.transaction_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise IntegrityError(f"Transaction journal cannot be read: {error}") from error
        if document.get("schema") != 1 or not isinstance(document.get("kind"), str):
            raise IntegrityError("Transaction journal is invalid")
        return document

    def finish_transaction(self) -> None:
        self.transaction_path.unlink(missing_ok=True)
        if self.state_dir.exists():
            _fsync_directory(self.state_dir)


class AuditLogger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write(
        self,
        level: str,
        action: str,
        message: str,
        **context: Any,
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level.upper(),
            "action": action,
            "message": message,
            "context": context,
        }
        descriptor = os.open(
            self.path,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT,
            0o640,
        )
        try:
            payload = (json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
