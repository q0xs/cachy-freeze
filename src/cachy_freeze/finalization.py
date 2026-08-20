"""Durable, logout-aware Golden publication orchestration."""

from __future__ import annotations

import json
import re
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .catalog import AuditLogger, atomic_json_write
from .errors import CachyFreezeError, IntegrityError
from .models import SnapshotMetadata
from .runner import CommandRunner

try:
    import pwd
except ImportError:  # pragma: no cover - Windows-only test compatibility
    pwd = None  # type: ignore[assignment]


FINALIZATION_SCHEMA = 1
_USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,30}$")
_ACTIVE_STATES = {"pending", "waiting-for-logout", "publishing"}
_VALID_STATES = _ACTIVE_STATES | {"complete", "failed", "cancelled"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


class FinalizationManager:
    """Own the durable hand-off between the desktop session and systemd."""

    def __init__(
        self,
        state_dir: Path,
        logger: AuditLogger,
        *,
        runner: CommandRunner | None = None,
        template_root: Path = Path("/var/lib/cachy-user-template"),
        sleeper: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.path = state_dir / "finalization.json"
        self.logger = logger
        self.runner = runner or CommandRunner()
        self.template_root = template_root
        self.sleeper = sleeper
        self.monotonic = monotonic

    def status(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema": FINALIZATION_SCHEMA, "status": "idle"}
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise IntegrityError(f"Finalization state cannot be read: {error}") from error
        if document.get("schema") != FINALIZATION_SCHEMA:
            raise IntegrityError("Unsupported finalization state schema")
        if document.get("status") not in _VALID_STATES:
            raise IntegrityError("Finalization state has an invalid status")
        username = document.get("requested_by")
        uid = document.get("requested_uid")
        if not isinstance(username, str) or not _USERNAME_RE.fullmatch(username):
            raise IntegrityError("Finalization state has an invalid username")
        if not isinstance(uid, int) or uid < 0:
            raise IntegrityError("Finalization state has an invalid user id")
        return document

    def _write(self, document: dict[str, Any]) -> dict[str, Any]:
        document["updated_at"] = _now()
        atomic_json_write(self.path, document, mode=0o600)
        return document

    def request(self, username: str, uid: int) -> dict[str, Any]:
        if not _USERNAME_RE.fullmatch(username) or uid < 0:
            raise CachyFreezeError("The finalization requester is invalid.")
        if pwd is None:
            raise CachyFreezeError("User account lookup is unavailable.")
        try:
            account = pwd.getpwnam(username)
        except KeyError as error:
            raise CachyFreezeError("The finalization requester does not exist.") from error
        if account.pw_uid != uid:
            raise CachyFreezeError("The finalization requester does not match its user id.")
        current = self.status()
        if current.get("status") in _ACTIVE_STATES:
            raise CachyFreezeError("A logout finalization is already pending.")
        now = _now()
        document = {
            "schema": FINALIZATION_SCHEMA,
            "request_id": uuid.uuid4().hex,
            "status": "pending",
            "requested_by": username,
            "requested_uid": uid,
            "requested_at": now,
            "updated_at": now,
        }
        self._write(document)
        try:
            self.runner.run(["systemctl", "start", "--no-block", "cachy-freeze-finalize.service"])
        except CachyFreezeError as error:
            document.update({"status": "failed", "error": "finalization-service-start"})
            self._write(document)
            raise CachyFreezeError(
                "The logout finalization service could not be started."
            ) from error
        self.logger.write(
            "WARNING",
            "finalization.request",
            "Logout-aware Golden publication requested",
            request_id=document["request_id"],
            username=username,
        )
        return document

    def _managed_accounts(self, requested_by: str, requested_uid: int) -> list[tuple[str, int]]:
        accounts = {requested_by: requested_uid}
        if pwd is None or not self.template_root.is_dir():
            return sorted(accounts.items())
        for template in self.template_root.iterdir():
            if not template.is_dir() or not _USERNAME_RE.fullmatch(template.name):
                continue
            try:
                account = pwd.getpwnam(template.name)
            except KeyError:
                continue
            accounts[template.name] = account.pw_uid
        return sorted(accounts.items())

    def _sessions(self, username: str) -> list[str]:
        completed = self.runner.run(
            ["loginctl", "show-user", username, "--property=Sessions", "--value"],
            check=False,
        )
        if completed.returncode != 0:
            return []
        output = (completed.stdout or b"").decode("utf-8", errors="replace").strip()
        return output.split() if output else []

    def _has_processes(self, uid: int) -> bool:
        completed = self.runner.run(["pgrep", "-u", str(uid)], check=False)
        if completed.returncode not in {0, 1}:
            raise CachyFreezeError("User process state could not be verified.")
        return completed.returncode == 0

    def _wait_until_quiescent(
        self,
        accounts: list[tuple[str, int]],
        *,
        timeout_seconds: int,
    ) -> None:
        deadline = self.monotonic() + timeout_seconds
        while True:
            active = [username for username, _uid in accounts if self._sessions(username)]
            if not active:
                break
            if self.monotonic() >= deadline:
                raise CachyFreezeError(
                    "Managed user sessions did not close; Golden was not published."
                )
            self.sleeper(2)

        # Once graphical sessions have exited, stop lingering per-user managers
        # and background jobs so no home file can change during template capture.
        for username, _uid in accounts:
            self.runner.run(["loginctl", "terminate-user", username], check=False)
        process_deadline = self.monotonic() + 30
        while any(self._has_processes(uid) for _username, uid in accounts):
            if self.monotonic() >= process_deadline:
                raise CachyFreezeError(
                    "Managed user processes did not stop; Golden was not published."
                )
            self.sleeper(1)

    def run(
        self,
        publish_and_freeze: Callable[[str], SnapshotMetadata],
        *,
        timeout_seconds: int = 180,
    ) -> dict[str, Any]:
        if not 1 <= timeout_seconds <= 900:
            raise CachyFreezeError("Finalization timeout must be between 1 and 900 seconds.")
        document = self.status()
        if document.get("status") not in {"pending", "waiting-for-logout"}:
            raise CachyFreezeError("No logout finalization is pending.")
        document.update({"status": "waiting-for-logout"})
        document.pop("error", None)
        self._write(document)
        accounts = self._managed_accounts(
            str(document["requested_by"]), int(document["requested_uid"])
        )
        try:
            self._wait_until_quiescent(accounts, timeout_seconds=timeout_seconds)
            document.update({"status": "publishing"})
            self._write(document)
            snapshot = publish_and_freeze("Golden publication after verified logout")
        except Exception as error:
            document.update(
                {
                    "status": "failed",
                    "error": str(error)[:512] or error.__class__.__name__,
                }
            )
            self._write(document)
            self.logger.write(
                "ERROR",
                "finalization.failed",
                "Logout-aware Golden publication failed safely",
                request_id=document["request_id"],
                error=document["error"],
            )
            raise
        document.update(
            {
                "status": "complete",
                "snapshot_id": snapshot.snapshot_id,
                "completed_at": _now(),
            }
        )
        self._write(document)
        self.logger.write(
            "INFO",
            "finalization.complete",
            "Golden published and FROZEN scheduled after verified logout",
            request_id=document["request_id"],
            snapshot_id=snapshot.snapshot_id,
        )
        return document
