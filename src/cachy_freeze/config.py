"""Strict parser for the root-owned CachyFreeze configuration."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, fields
from pathlib import Path

from .errors import ConfigurationError

_SUBVOLUME_RE = re.compile(r"^@[A-Za-z0-9._-]*$")
_INTEGER_RE = re.compile(r"^[0-9]+$")


@dataclass(frozen=True, slots=True)
class Config:
    STATE_DIR: str = "/var/lib/cachy-freeze"
    STATE_SUBVOL: str = "@cachy-state"
    TOP_MOUNT: str = "/run/cachy-freeze/btrfs"
    MAINTENANCE_SUBVOL: str = "@"
    GOLDEN_SUBVOL: str = "@golden"
    GOLDEN_PREVIOUS_SUBVOL: str = "@golden.previous"
    GOLDEN_NEXT_SUBVOL: str = "@golden.next"
    GOLDEN_PENDING_SUBVOL: str = "@golden.previous.pending"
    FAILED_GOLDEN_SUBVOL: str = "@golden.failed"
    ACTIVE_SUBVOL: str = "@active"
    PREVIOUS_SUBVOL: str = "@active.previous"
    NEXT_SUBVOL: str = "@active.next"
    ACTIVE_PENDING_SUBVOL: str = "@active.previous.pending"
    SNAPSHOT_SUBVOL: str = "@cachy-snapshots"
    EXPORT_DIR: str = "/var/lib/cachy-freeze/exports"
    LOG_FILE: str = "/var/log/cachy-freeze/operations.jsonl"
    LOCK_FILE: str = "/run/lock/cachy-freeze.lock"
    RETENTION_COUNT: int = 20
    BOOT_FAILURE_LIMIT: int = 3
    ROOT_UUID: str = ""
    ROOT_DEVICE: str = ""

    @classmethod
    def load(cls, path: Path) -> Config:
        if not path.is_file():
            raise ConfigurationError(f"Configuration file not found: {path}")
        allowed = {field.name for field in fields(cls)}
        values: dict[str, str | int] = {}
        for line_number, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ConfigurationError(f"Invalid configuration at {path}:{line_number}")
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key not in allowed:
                raise ConfigurationError(f"Unknown configuration key: {key}")
            if key in values:
                raise ConfigurationError(f"Duplicate configuration key: {key}")
            if "\x00" in value or "\n" in value or "\r" in value:
                raise ConfigurationError(f"Invalid value for {key}")
            values[key] = value

        for integer_name in ("RETENTION_COUNT", "BOOT_FAILURE_LIMIT"):
            if integer_name not in values:
                continue
            raw_integer = str(values[integer_name])
            if not _INTEGER_RE.fullmatch(raw_integer):
                raise ConfigurationError(f"{integer_name} must be an integer")
            values[integer_name] = int(raw_integer)

        config = cls(**values)
        config.validate()
        return config

    def validate(self) -> None:
        for name in (
            "MAINTENANCE_SUBVOL",
            "STATE_SUBVOL",
            "GOLDEN_SUBVOL",
            "GOLDEN_PREVIOUS_SUBVOL",
            "GOLDEN_NEXT_SUBVOL",
            "GOLDEN_PENDING_SUBVOL",
            "FAILED_GOLDEN_SUBVOL",
            "ACTIVE_SUBVOL",
            "PREVIOUS_SUBVOL",
            "NEXT_SUBVOL",
            "ACTIVE_PENDING_SUBVOL",
            "SNAPSHOT_SUBVOL",
        ):
            value = str(getattr(self, name))
            if not _SUBVOLUME_RE.fullmatch(value):
                raise ConfigurationError(f"Invalid subvolume name in {name}: {value}")

        subvolumes = [
            str(getattr(self, field.name)) for field in fields(self) if "SUBVOL" in field.name
        ]
        if len(set(subvolumes)) != len(subvolumes):
            raise ConfigurationError("Configured subvolume names must be unique")

        for name in ("STATE_DIR", "TOP_MOUNT", "EXPORT_DIR", "LOG_FILE", "LOCK_FILE"):
            value = str(getattr(self, name))
            if not os.path.isabs(value):
                raise ConfigurationError(f"{name} must be an absolute path")
        if self.ROOT_DEVICE and not os.path.isabs(self.ROOT_DEVICE):
            raise ConfigurationError("ROOT_DEVICE must be empty or an absolute path")
        if not 1 <= self.RETENTION_COUNT <= 1000:
            raise ConfigurationError("RETENTION_COUNT must be between 1 and 1000")
        if not 2 <= self.BOOT_FAILURE_LIMIT <= 10:
            raise ConfigurationError("BOOT_FAILURE_LIMIT must be between 2 and 10")
