"""Asynchronous JSON bridge to the allow-listed PolicyKit helper."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

INSTALLED_HELPER = Path("/usr/lib/cachy-freeze/cachy-freeze-manager-helper")
STATUS_CACHE = Path("/var/lib/cachy-freeze/status.json")
MAX_ERROR_OUTPUT_BYTES = 64 * 1024
ALLOWED_ACTIONS = frozenset(
    {
        "status",
        "freeze",
        "thaw",
        "reboot",
        "setup-install",
        "setup-workstation-install",
        "setup-workstation-repair",
        "setup-workstation-check",
    }
)


class BackendClient(QObject):
    busy_changed = pyqtSignal(bool)
    status_changed = pyqtSignal(dict)
    result_ready = pyqtSignal(str, object)
    operation_finished = pyqtSignal(str, bool, str)
    operation_output = pyqtSignal(str, str)

    def __init__(self, setup_root: Path | None = None) -> None:
        super().__init__()
        self.setup_root = setup_root.resolve() if setup_root is not None else None
        self.process: QProcess | None = None
        self.pending_action = ""
        self.pending_secret: str | None = None
        self.stderr_buffer = bytearray()
        self.status: dict[str, Any] = {}

    @property
    def busy(self) -> bool:
        return self.process is not None

    @property
    def workstation_available(self) -> bool:
        if self.setup_root is not None:
            root = self.setup_root
        else:
            root = Path("/usr/lib/cachy-freeze/deployment")
        return os.access(root / "workstation" / "bin" / "workstation-setup", os.X_OK)

    def refresh_local(self) -> None:
        try:
            cached = json.loads(STATUS_CACHE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cached = None
        self.status = cached if isinstance(cached, dict) else self._fallback_status()
        self.status_changed.emit(self.status)

    @staticmethod
    def _fallback_status() -> dict[str, Any]:
        try:
            command_line = Path("/proc/cmdline").read_text(encoding="utf-8").split()
        except OSError:
            command_line = []
        mode = "unknown"
        if "cachy.freeze=1" in command_line:
            mode = "frozen"
        elif "cachy.freeze=0" in command_line:
            mode = "thawed"
        return {
            "schema": 3,
            "running_mode": mode,
            "scheduled_mode": "unknown",
            "reboot_required": False,
            "verified": False,
        }

    def run(self, action: str, *, secret: str | None = None) -> bool:
        if action not in ALLOWED_ACTIONS:
            self.operation_finished.emit(action, False, "Unsupported CachyFreeze action.")
            return False
        if self.busy:
            self.operation_finished.emit(
                action, False, "Another CachyFreeze operation is already running."
            )
            return False
        helper = self._helper_for(action)
        if not os.access(helper, os.X_OK):
            self.operation_finished.emit(action, False, "The privileged helper was not found.")
            return False
        self.pending_action = action
        self.pending_secret = secret
        self.stderr_buffer.clear()
        self.process = QProcess(self)
        self.process.setProgram("/usr/bin/pkexec")
        self.process.setArguments([str(helper), action])
        self.process.started.connect(self._send_secret)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self.busy_changed.emit(True)
        self.process.start()
        return True

    def _helper_for(self, action: str) -> Path:
        if action.startswith("setup-") and self.setup_root is not None:
            return self.setup_root / "app" / "cachy-freeze-manager-helper"
        return INSTALLED_HELPER

    def _send_secret(self) -> None:
        if self.process is None or self.pending_secret is None:
            return
        secret = self.pending_secret
        self.pending_secret = None
        self.process.write((secret + "\n").encode())
        self.process.closeWriteChannel()

    def _read_stderr(self) -> None:
        if self.process is None:
            return
        chunk = bytes(self.process.readAllStandardError())
        self.stderr_buffer.extend(chunk)
        if len(self.stderr_buffer) > MAX_ERROR_OUTPUT_BYTES:
            del self.stderr_buffer[:-MAX_ERROR_OUTPUT_BYTES]
        if chunk:
            self.operation_output.emit(self.pending_action, chunk.decode("utf-8", errors="replace"))

    def _finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        if self.process is None:
            return
        action = self.pending_action
        stdout = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self.stderr_buffer.extend(bytes(self.process.readAllStandardError()))
        stderr = self.stderr_buffer[-MAX_ERROR_OUTPUT_BYTES:].decode("utf-8", errors="replace")
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
                raise ValueError
            result = payload.get("result")
        except (json.JSONDecodeError, AttributeError, ValueError):
            self.operation_finished.emit(
                action, False, "The privileged helper returned an invalid response."
            )
            return
        if isinstance(result, dict) and action in {"status", "setup-install"}:
            result = {**result, "verified": True}
            self.status = result
            self.status_changed.emit(result)
        elif action in {"freeze", "thaw"}:
            self.refresh_local()
        self.result_ready.emit(action, result)
        messages = {
            "status": "System state verified.",
            "setup-install": "CachyFreeze was installed and FROZEN was prepared.",
            "setup-workstation-install": "CachyWorkstation provisioning finished.",
            "setup-workstation-repair": "CachyWorkstation repair finished.",
            "setup-workstation-check": "CachyWorkstation health check passed.",
            "freeze": "The new Golden baseline is ready; FROZEN is scheduled.",
            "thaw": "THAWED is scheduled without retaining the disposable runtime.",
            "reboot": "The explicit reboot request was accepted.",
        }
        self.operation_finished.emit(action, True, messages[action])

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
