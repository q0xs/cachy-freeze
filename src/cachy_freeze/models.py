"""Typed domain models shared by the backend, catalog, and tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from typing import Any

CHECKSUM_ALGORITHM = "sha256-metadata-v1"


@dataclass(frozen=True, slots=True)
class SnapshotMetadata:
    snapshot_id: str
    subvolume: str
    btrfs_uuid: str
    parent_uuid: str
    created_at: str
    kernel: str
    apparent_size_bytes: int
    exclusive_size_bytes: int
    description: str
    created_by: str
    frozen: bool
    bootable: bool
    checksum: str
    checksum_algorithm: str
    rollback_count: int
    creation_duration_ms: int
    health: str
    source_subvolume: str

    @classmethod
    def create(cls, **values: Any) -> SnapshotMetadata:
        unsigned = cls(
            checksum="",
            checksum_algorithm=CHECKSUM_ALGORITHM,
            rollback_count=0,
            health="healthy",
            **values,
        )
        return replace(unsigned, checksum=unsigned.expected_checksum())

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> SnapshotMetadata:
        return cls(**values)

    def checksum_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        for mutable_field in ("checksum", "health", "rollback_count"):
            payload.pop(mutable_field)
        return payload

    def expected_checksum(self) -> str:
        encoded = json.dumps(
            self.checksum_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def verifies(self) -> bool:
        return (
            self.checksum_algorithm == CHECKSUM_ALGORITHM
            and self.checksum == self.expected_checksum()
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
