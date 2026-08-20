"""Durable proof that a published Golden completed a real FROZEN boot."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .catalog import AuditLogger, atomic_json_write
from .errors import CachyFreezeError, IntegrityError
from .runner import CommandRunner

VALIDATION_SCHEMA = 1
_SNAPSHOT_RE = re.compile(r"^snap-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
_USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,30}$")
_BOOT_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_VALID_STATES = {"awaiting-frozen-boot", "verifying", "verified", "failed"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


class BootValidationManager:
    """Arm a Golden and verify its first real FROZEN graphical boot."""

    def __init__(
        self,
        state_dir: Path,
        logger: AuditLogger,
        *,
        runner: CommandRunner | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        boot_id_path: Path = Path("/proc/sys/kernel/random/boot_id"),
    ) -> None:
        self.state_dir = state_dir
        self.path = state_dir / "boot-validation.json"
        self.logger = logger
        self.runner = runner or CommandRunner()
        self.sleeper = sleeper
        self.monotonic = monotonic
        self.boot_id_path = boot_id_path

    def status(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema": VALIDATION_SCHEMA, "status": "idle"}
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise IntegrityError(f"Boot validation state cannot be read: {error}") from error
        if document.get("schema") != VALIDATION_SCHEMA:
            raise IntegrityError("Unsupported boot validation state schema")
        if document.get("status") not in _VALID_STATES:
            raise IntegrityError("Boot validation state has an invalid status")
        if not _SNAPSHOT_RE.fullmatch(str(document.get("snapshot_id", ""))):
            raise IntegrityError("Boot validation state has an invalid snapshot id")
        expected_user = document.get("expected_user")
        if expected_user is not None and (
            not isinstance(expected_user, str) or not _USERNAME_RE.fullmatch(expected_user)
        ):
            raise IntegrityError("Boot validation state has an invalid expected user")
        return document

    def _write(self, document: dict[str, Any]) -> dict[str, Any]:
        document["updated_at"] = _now()
        atomic_json_write(self.path, document, mode=0o600)
        return document

    def arm(self, snapshot_id: str, expected_user: str | None) -> dict[str, Any]:
        if not _SNAPSHOT_RE.fullmatch(snapshot_id):
            raise CachyFreezeError("The Golden snapshot id cannot be armed for validation.")
        if expected_user is not None and not _USERNAME_RE.fullmatch(expected_user):
            raise CachyFreezeError("The expected automatic-login user is invalid.")
        now = _now()
        document = {
            "schema": VALIDATION_SCHEMA,
            "status": "awaiting-frozen-boot",
            "snapshot_id": snapshot_id,
            "expected_user": expected_user,
            "armed_at": now,
            "updated_at": now,
        }
        self._write(document)
        self.logger.write(
            "INFO",
            "boot.validation.arm",
            "Golden armed for real FROZEN boot validation",
            snapshot_id=snapshot_id,
            expected_user=expected_user,
        )
        return document

    def _boot_id(self) -> str:
        try:
            boot_id = self.boot_id_path.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise CachyFreezeError("The current boot id could not be read.") from error
        if not _BOOT_ID_RE.fullmatch(boot_id):
            raise IntegrityError("The current boot id is invalid")
        return boot_id

    def _marker_matches(self, name: str, boot_id: str) -> bool:
        try:
            value = (self.state_dir / name).read_text(encoding="utf-8").strip()
        except OSError:
            return False
        return value == boot_id

    def _command_value(self, command: list[str]) -> str:
        completed = self.runner.run(command, check=False)
        if completed.returncode != 0:
            return ""
        return (completed.stdout or b"").decode("utf-8", errors="replace").strip()

    def _has_graphical_session(self, username: str) -> bool:
        sessions = self._command_value(
            ["loginctl", "show-user", username, "--property=Sessions", "--value"]
        ).split()
        for session in sessions:
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", session):
                continue
            name = self._command_value(
                ["loginctl", "show-session", session, "--property=Name", "--value"]
            )
            session_type = self._command_value(
                ["loginctl", "show-session", session, "--property=Type", "--value"]
            )
            state = self._command_value(
                ["loginctl", "show-session", session, "--property=State", "--value"]
            )
            if name == username and session_type in {"wayland", "x11"} and state == "active":
                return True
        return False

    def _wait_for_graphical_session(self, username: str, timeout_seconds: int) -> None:
        deadline = self.monotonic() + timeout_seconds
        while not self._has_graphical_session(username):
            if self.monotonic() >= deadline:
                raise CachyFreezeError(
                    "The expected automatic-login graphical session did not become active."
                )
            self.sleeper(2)

    def validate(
        self,
        *,
        running_mode: str,
        current_subvolume: str,
        golden_present: bool,
        active_present: bool,
        timeout_seconds: int = 120,
    ) -> dict[str, Any]:
        if not 1 <= timeout_seconds <= 300:
            raise CachyFreezeError("Boot validation timeout must be between 1 and 300 seconds.")
        document = self.status()
        if document.get("status") == "idle":
            return document
        if document.get("status") == "verified":
            return document
        document.update({"status": "verifying"})
        document.pop("error", None)
        self._write(document)
        try:
            if running_mode != "frozen" or current_subvolume != "@active":
                raise CachyFreezeError("The validation boot is not a FROZEN Active boot.")
            if not golden_present or not active_present:
                raise CachyFreezeError("Golden or Active is missing during boot validation.")
            boot_id = self._boot_id()
            required_markers = (
                "active-reset-boot-id",
                "home-reset-boot-id",
                "admin-restrict-boot-id",
            )
            missing = [
                marker for marker in required_markers if not self._marker_matches(marker, boot_id)
            ]
            if missing:
                raise CachyFreezeError(
                    "Current-boot reset evidence is missing: " + ", ".join(missing)
                )
            if expected_user := document.get("expected_user"):
                self._wait_for_graphical_session(str(expected_user), timeout_seconds)
        except Exception as error:
            document.update({"status": "failed", "error": str(error)[:512]})
            self._write(document)
            self.logger.write(
                "ERROR",
                "boot.validation.failed",
                "Real FROZEN boot validation failed",
                snapshot_id=document["snapshot_id"],
                error=document["error"],
            )
            raise
        document.update(
            {
                "status": "verified",
                "verified_at": _now(),
                "verified_boot_id": boot_id,
            }
        )
        self._write(document)
        self.logger.write(
            "INFO",
            "boot.validation.verified",
            "Golden passed real FROZEN graphical boot validation",
            snapshot_id=document["snapshot_id"],
            boot_id=boot_id,
        )
        return document
