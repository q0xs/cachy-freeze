"""Strict parser for root-owned CachyFreeze configuration."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, fields
from pathlib import Path

from .errors import ConfigurationError

_SUBVOLUME_RE = re.compile(r"^@[A-Za-z0-9._-]*$")
_UUID_RE = re.compile(
    r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-"
    r"[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$"
)


@dataclass(frozen=True, slots=True)
class Config:
    STATE_DIR: str = "/var/lib/cachy-freeze"
    STATE_SUBVOL: str = "@cachy-state"
    TOP_MOUNT: str = "/run/cachy-freeze/btrfs"
    MAINTENANCE_SUBVOL: str = "@"
    GOLDEN_SUBVOL: str = "@golden"
    GOLDEN_NEXT_SUBVOL: str = "@golden.next"
    GOLDEN_PENDING_SUBVOL: str = "@golden.pending"
    ACTIVE_SUBVOL: str = "@active"
    ACTIVE_NEXT_SUBVOL: str = "@active.next"
    ACTIVE_PENDING_SUBVOL: str = "@active.pending"
    CAPTURE_SUBVOL: str = "@cachy-capture"
    LEGACY_SNAPSHOT_SUBVOL: str = "@cachy-snapshots"
    LOG_FILE: str = "/var/log/cachy-freeze/operations.jsonl"
    LOCK_FILE: str = "/run/lock/cachy-freeze.lock"
    ROOT_UUID: str = ""
    ROOT_DEVICE: str = ""

    @classmethod
    def load(cls, path: Path) -> Config:
        if not path.is_file():
            raise ConfigurationError(f"Configuration file not found: {path}")
        allowed = {field.name for field in fields(cls)}
        values: dict[str, str] = {}
        for line_number, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ConfigurationError(f"Invalid configuration at {path}:{line_number}")
            key, value = (part.strip() for part in line.split("=", 1))
            if key not in allowed:
                raise ConfigurationError(f"Unknown configuration key: {key}")
            if key in values:
                raise ConfigurationError(f"Duplicate configuration key: {key}")
            if any(character in value for character in ("\x00", "\n", "\r")):
                raise ConfigurationError(f"Invalid value for {key}")
            values[key] = value
        config = cls(**values)
        config.validate()
        return config

    def validate(self) -> None:
        required_contract = {
            "MAINTENANCE_SUBVOL": "@",
            "STATE_SUBVOL": "@cachy-state",
            "GOLDEN_SUBVOL": "@golden",
            "GOLDEN_NEXT_SUBVOL": "@golden.next",
            "GOLDEN_PENDING_SUBVOL": "@golden.pending",
            "ACTIVE_SUBVOL": "@active",
            "ACTIVE_NEXT_SUBVOL": "@active.next",
            "ACTIVE_PENDING_SUBVOL": "@active.pending",
            "CAPTURE_SUBVOL": "@cachy-capture",
            "LEGACY_SNAPSHOT_SUBVOL": "@cachy-snapshots",
        }
        for name, expected in required_contract.items():
            if getattr(self, name) != expected:
                raise ConfigurationError(f"Unsupported {name}; expected {expected}")
        subvolume_fields = [field.name for field in fields(self) if "SUBVOL" in field.name]
        subvolumes: list[str] = []
        for name in subvolume_fields:
            value = str(getattr(self, name))
            if not _SUBVOLUME_RE.fullmatch(value):
                raise ConfigurationError(f"Invalid subvolume name in {name}: {value}")
            subvolumes.append(value)
        if len(set(subvolumes)) != len(subvolumes):
            raise ConfigurationError("Configured subvolume names must be unique")

        for name in ("STATE_DIR", "TOP_MOUNT", "LOG_FILE", "LOCK_FILE"):
            if not os.path.isabs(str(getattr(self, name))):
                raise ConfigurationError(f"{name} must be an absolute path")
        if self.ROOT_DEVICE and not os.path.isabs(self.ROOT_DEVICE):
            raise ConfigurationError("ROOT_DEVICE must be empty or an absolute path")
        if self.ROOT_UUID and not _UUID_RE.fullmatch(self.ROOT_UUID):
            raise ConfigurationError("ROOT_UUID must be empty or a canonical filesystem UUID")

    @property
    def managed_subvolumes(self) -> frozenset[str]:
        return frozenset(
            {
                self.MAINTENANCE_SUBVOL,
                self.STATE_SUBVOL,
                self.GOLDEN_SUBVOL,
                self.GOLDEN_NEXT_SUBVOL,
                self.GOLDEN_PENDING_SUBVOL,
                self.ACTIVE_SUBVOL,
                self.ACTIVE_NEXT_SUBVOL,
                self.ACTIVE_PENDING_SUBVOL,
                self.CAPTURE_SUBVOL,
                self.LEGACY_SNAPSHOT_SUBVOL,
            }
        )
