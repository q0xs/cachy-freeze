"""Asynchronous, JSON-only bridge to the PolicyKit helper."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

INSTALLED_HELPER = Path("/usr/lib/cachy-freeze/cachy-freeze-manager-helper")
STATUS_CACHE = Path("/var/lib/cachy-freeze/status.json")
SNAPSHOT_CATALOG = Path("/var/lib/cachy-freeze/snapshots.json")
MAX_ERROR_OUTPUT_BYTES = 64 * 1024


class BackendClient(QObject):
    busy_changed = pyqtSignal(bool)
    status_changed = pyqtSignal(dict)
    snapshots_changed = pyqtSignal(list)
    logs_changed = pyqtSignal(list)
    users_changed = pyqtSignal(list)
    result_ready = pyqtSignal(str, object)
    operation_finished = pyqtSignal(str, bool, str)
    operation_output = pyqtSignal(str, str)

    def __init__(self, setup_root: Path | None = None) -> None:
        super().__init__()
        self.setup_root = setup_root.resolve() if setup_root is not None else None
        self.process: QProcess | None = None
        self.pending_action = ""
        self.status: dict[str, Any] = {}
        self.snapshots: list[dict[str, Any]] = []
        self.logs: list[dict[str, Any]] = []
        self.users: list[dict[str, Any]] = []
        self.pending_secret: str | None = None
        self.stderr_buffer = bytearray()

    @property
    def busy(self) -> bool:
        return self.process is not None

    @staticmethod
    def _read_json(path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def refresh_local(self) -> None:
        cached_status = self._read_json(STATUS_CACHE)
        if isinstance(cached_status, dict):
            self.status = cached_status
        else:
            self.status = self._fallback_status()
        self.status_changed.emit(self.status)

        catalog = self._read_json(SNAPSHOT_CATALOG)
        items = catalog.get("snapshots", []) if isinstance(catalog, dict) else []
        self.snapshots = sorted(
            [item for item in items if isinstance(item, dict)],
            key=lambda item: str(item.get("created_at", "")),
            reverse=True,
        )
        self.snapshots_changed.emit(self.snapshots)

    @staticmethod
    def _fallback_status() -> dict[str, Any]:
        try:
            command_line = Path("/proc/cmdline").read_text(encoding="utf-8").split()
        except OSError:
            command_line = []
        if "cachy.freeze=1" in command_line:
            mode = "frozen"
        elif "cachy.freeze=0" in command_line:
            mode = "thawed"
        else:
            mode = "unknown"
        return {
            "schema": 1,
            "running_mode": mode,
            "scheduled_mode": "unknown",
            "snapshot_count": 0,
            "last_snapshot": None,
            "golden_present": False,
            "active_present": False,
            "transaction_pending": False,
        }

    def run(self, action: str, *arguments: str, secret: str | None = None) -> bool:
        if self.busy:
            self.operation_finished.emit(
                action, False, "Another CachyFreeze operation is already running."
            )
            return False
        helper = self._helper_for(action)
        if not os.access(helper, os.X_OK):
            self.operation_finished.emit(
                action,
                False,
                "The privileged CachyFreeze helper was not found. Open setup from "
                "the desktop launcher in the repository.",
            )
            return False
        self.pending_action = action
        self.pending_secret = secret
        self.stderr_buffer.clear()
        self.process = QProcess(self)
        self.process.setProgram("/usr/bin/pkexec")
        self.process.setArguments([str(helper), action, *arguments])
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self.process.started.connect(self._send_secret)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.busy_changed.emit(True)
        self.process.start()
        return True

    def _helper_for(self, action: str) -> Path:
        if action.startswith("setup-") and self.setup_root is not None:
            return self.setup_root / "app" / "cachy-freeze-manager-helper"
        return INSTALLED_HELPER

    def _read_stderr(self) -> None:
        if self.process is None:
            return
        chunk = bytes(self.process.readAllStandardError())
        if not chunk:
            return
        self.stderr_buffer.extend(chunk)
        if len(self.stderr_buffer) > MAX_ERROR_OUTPUT_BYTES:
            del self.stderr_buffer[:-MAX_ERROR_OUTPUT_BYTES]
        self.operation_output.emit(
            self.pending_action,
            chunk.decode("utf-8", errors="replace"),
        )

    def _send_secret(self) -> None:
        if self.process is None or self.pending_secret is None:
            return
        self.process.write((self.pending_secret + "\n").encode("utf-8"))
        self.process.closeWriteChannel()
        self.pending_secret = None

    def _finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        if self.process is None:
            return
        action = self.pending_action
        stdout = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self.stderr_buffer.extend(bytes(self.process.readAllStandardError()))
        if len(self.stderr_buffer) > MAX_ERROR_OUTPUT_BYTES:
            del self.stderr_buffer[:-MAX_ERROR_OUTPUT_BYTES]
        stderr = self.stderr_buffer.decode("utf-8", errors="replace")
        self.process.deleteLater()
        self.process = None
        self.pending_action = ""
        self.pending_secret = None
        self.stderr_buffer.clear()
        self.busy_changed.emit(False)
        if exit_code in (126, 127):
            self.operation_finished.emit(action, False, "Authentication was cancelled.")
            return
        if exit_code != 0:
            self.operation_finished.emit(action, False, stderr.strip() or "Operation failed.")
            return
        try:
            payload = json.loads(stdout)
            if payload.get("ok") is not True:
                raise ValueError("invalid backend response")
            result = payload.get("result")
        except (json.JSONDecodeError, AttributeError, ValueError):
            self.operation_finished.emit(
                action, False, "The privileged service returned an invalid response."
            )
            return

        if action == "status" and isinstance(result, dict):
            self.status = result
            self.status_changed.emit(self.status)
        elif action == "snapshot-list" and isinstance(result, list):
            self.snapshots = result
            self.snapshots_changed.emit(self.snapshots)
        elif action == "logs" and isinstance(result, list):
            self.logs = result
            self.logs_changed.emit(self.logs)
        elif action == "user-list" and isinstance(result, list):
            self.users = result
            self.users_changed.emit(self.users)
        else:
            self.refresh_local()
        self.result_ready.emit(action, result)
        self.operation_finished.emit(action, True, self._success_message(action))

    def _process_error(self, _error: QProcess.ProcessError) -> None:
        if self.process is None or self.process.state() != QProcess.ProcessState.NotRunning:
            return
        action = self.pending_action
        self.process.deleteLater()
        self.process = None
        self.pending_action = ""
        self.pending_secret = None
        self.stderr_buffer.clear()
        self.busy_changed.emit(False)
        self.operation_finished.emit(action, False, "The privileged operation could not start.")

    @staticmethod
    def _success_message(action: str) -> str:
        messages = {
            "status": "System status refreshed.",
            "thaw": "The next boot was set to THAWED maintenance mode.",
            "thaw-once": "Only the next boot was set to THAWED.",
            "freeze": "Golden was published and the next boot was set to FROZEN.",
            "freeze-prepare": "Safe finalization was queued; log out to continue.",
            "snapshot-list": "Snapshot list refreshed.",
            "snapshot-create": "Snapshot created.",
            "snapshot-verify": "Snapshot verification completed.",
            "snapshot-delete": "Snapshot deleted.",
            "snapshot-rollback": "Rollback prepared; the next boot will be FROZEN.",
            "snapshot-export": "Snapshot written to the export directory.",
            "snapshot-import": "Snapshot imported after checksum verification.",
            "health": "System health check completed.",
            "diagnostics": "Redacted diagnostic bundle created.",
            "logs": "Audit log refreshed.",
            "user-list": "User list refreshed.",
            "user-create": "Standard user created.",
            "user-delete": "User backed up and deleted.",
            "user-restore": "User restored from backup.",
            "user-password": "User password changed.",
            "user-lock": "User account locked.",
            "user-unlock": "User account unlocked.",
            "user-autologin": "Automatic login updated.",
            "updates-check": "Update check completed.",
            "updates-apply": "Updates applied and a new Golden published.",
            "settings-get": "Settings loaded.",
            "settings-set": "Settings validated and saved.",
            "applications-status": "Applications verified.",
            "applications-install": "Applications installed and a new Golden published.",
            "setup-status": "Setup status refreshed.",
            "setup-preflight": "CachyOS, UEFI, Btrfs, and GRUB preflight passed.",
            "setup-install": "CachyFreeze was installed in THAWED mode.",
            "setup-freeze": "GRUB protection is ready; log out to publish Golden safely.",
            "reboot": "System is rebooting.",
        }
        return messages.get(action, "Operation completed successfully.")
