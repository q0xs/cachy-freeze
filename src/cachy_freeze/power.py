"""Idle suspend followed by unattended RTC wake and shutdown."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .catalog import AuditLogger, atomic_json_write
from .errors import CachyFreezeError, IntegrityError
from .runner import CommandRunner

POWER_SCHEMA = 1
IDLE_BEFORE_SUSPEND_SECONDS = 3600
SLEEP_BEFORE_SHUTDOWN_SECONDS = 3600
RTC_WAKE_GRACE_SECONDS = 5
_VALID_STATES = {
    "active",
    "idle",
    "sleeping",
    "manual-wake",
    "shutting-down",
    "unsupported",
    "failed",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _boottime() -> float:
    return time.clock_gettime(time.CLOCK_BOOTTIME)


class IdlePowerManager:
    """Enforce one hour idle -> sleep -> one hour unattended -> shutdown."""

    def __init__(
        self,
        state_dir: Path,
        logger: AuditLogger,
        *,
        runner: CommandRunner | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
        elapsed_clock: Callable[[], float] = _boottime,
        rtcwake_path: Path = Path("/usr/bin/rtcwake"),
        wakealarm_path: Path = Path("/sys/class/rtc/rtc0/wakealarm"),
        boot_id_path: Path = Path("/proc/sys/kernel/random/boot_id"),
    ) -> None:
        self.state_dir = state_dir
        self.path = state_dir / "power-policy.json"
        self.logger = logger
        self.runner = runner or CommandRunner()
        self.sleeper = sleeper
        self.monotonic = monotonic
        self.wall_clock = wall_clock
        self.elapsed_clock = elapsed_clock
        self.rtcwake_path = rtcwake_path
        self.wakealarm_path = wakealarm_path
        self.boot_id_path = boot_id_path
        self.waiting_for_activity: bool | None = None

    def support(self) -> dict[str, Any]:
        rtcwake_available = self.rtcwake_path.is_file() and os.access(self.rtcwake_path, os.X_OK)
        wakealarm_available = self.wakealarm_path.exists() and os.access(
            self.wakealarm_path, os.W_OK
        )
        return {
            "supported": rtcwake_available and wakealarm_available,
            "rtcwake_available": rtcwake_available,
            "wakealarm_available": wakealarm_available,
            "idle_before_suspend_seconds": IDLE_BEFORE_SUSPEND_SECONDS,
            "sleep_before_shutdown_seconds": SLEEP_BEFORE_SHUTDOWN_SECONDS,
        }

    def status(self) -> dict[str, Any]:
        support = self.support()
        if not self.path.exists():
            return {"schema": POWER_SCHEMA, "status": "active", **support}
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise IntegrityError(f"Power-policy state cannot be read: {error}") from error
        if document.get("schema") != POWER_SCHEMA:
            raise IntegrityError("Unsupported power-policy state schema")
        if document.get("status") not in _VALID_STATES:
            raise IntegrityError("Power-policy state has an invalid status")
        return {**document, **support}

    def _write(self, status: str, **details: Any) -> dict[str, Any]:
        document = {
            "schema": POWER_SCHEMA,
            "status": status,
            "updated_at": _now(),
            **details,
        }
        atomic_json_write(self.path, document, mode=0o600)
        return document

    def _idle(self) -> tuple[bool, float]:
        hint = self.runner.text(
            ["loginctl", "show-seat", "seat0", "--property=IdleHint", "--value"],
            check=False,
        )
        raw_since = self.runner.text(
            [
                "loginctl",
                "show-seat",
                "seat0",
                "--property=IdleSinceHintMonotonic",
                "--value",
            ],
            check=False,
        )
        normalized_hint = hint.strip().casefold()
        if normalized_hint == "no":
            return False, 0.0
        if normalized_hint != "yes" or not raw_since.strip().isdigit():
            raise CachyFreezeError("The desktop idle state could not be read from logind.")
        since_seconds = int(raw_since.strip()) / 1_000_000
        if since_seconds <= 0:
            raise CachyFreezeError("The desktop idle timestamp reported by logind is invalid.")
        return True, max(0.0, self.monotonic() - since_seconds)

    def _boot_id(self) -> str:
        try:
            return self.boot_id_path.read_text(encoding="utf-8").strip()[:64]
        except OSError:
            return "unavailable"

    def run_cycle(self) -> dict[str, Any]:
        if self.waiting_for_activity is None:
            previous = self.status()
            self.waiting_for_activity = bool(previous.get("waiting_for_new_activity", False))
        support = self.support()
        if not support["supported"]:
            self.waiting_for_activity = True
            return self._write(
                "unsupported",
                error="RTC wake is unavailable; automatic shutdown after sleep is disabled.",
                waiting_for_new_activity=True,
            )

        idle, idle_seconds = self._idle()
        if not idle:
            self.waiting_for_activity = False
            return self._write("active")
        if self.waiting_for_activity:
            return self._write("manual-wake", waiting_for_new_activity=True)
        if idle_seconds < IDLE_BEFORE_SUSPEND_SECONDS:
            return self._write("idle", idle_seconds=int(idle_seconds))

        sleep_started = self.wall_clock()
        elapsed_started = self.elapsed_clock()
        deadline = sleep_started + SLEEP_BEFORE_SHUTDOWN_SECONDS
        boot_id = self._boot_id()
        self._write(
            "sleeping",
            sleep_started_at_epoch=int(sleep_started),
            shutdown_deadline_epoch=int(deadline),
            boot_id=boot_id,
        )
        self.logger.write(
            "INFO",
            "power.suspend",
            "Idle workstation entering timed sleep",
            idle_seconds=int(idle_seconds),
            shutdown_after_seconds=SLEEP_BEFORE_SHUTDOWN_SECONDS,
        )
        completed = self.runner.run(
            [
                str(self.rtcwake_path),
                "--mode",
                "mem",
                "--seconds",
                str(SLEEP_BEFORE_SHUTDOWN_SECONDS),
            ],
            check=False,
        )
        if completed.returncode != 0:
            self.waiting_for_activity = True
            error = (completed.stderr or b"").decode("utf-8", errors="replace")[-512:].strip()
            self.logger.write(
                "ERROR",
                "power.suspend.failed",
                "Timed RTC sleep failed",
                error=error or "rtcwake failed",
            )
            return self._write(
                "failed",
                error=error or "rtcwake failed",
                waiting_for_new_activity=True,
            )

        slept_seconds = max(0.0, self.elapsed_clock() - elapsed_started)
        if slept_seconds >= SLEEP_BEFORE_SHUTDOWN_SECONDS - RTC_WAKE_GRACE_SECONDS:
            self._write(
                "shutting-down",
                slept_seconds=int(slept_seconds),
                boot_id=boot_id,
            )
            self.logger.write(
                "WARNING",
                "power.shutdown",
                "RTC sleep deadline reached; unattended workstation is shutting down",
                slept_seconds=int(slept_seconds),
            )
            shutdown = self.runner.run(["systemctl", "poweroff", "--no-block"], check=False)
            if shutdown.returncode != 0:
                self.waiting_for_activity = True
                error = (shutdown.stderr or b"").decode("utf-8", errors="replace")[-512:].strip()
                return self._write(
                    "failed",
                    error=error or "systemctl poweroff failed",
                    waiting_for_new_activity=True,
                )
            return self.status()

        self.runner.run([str(self.rtcwake_path), "--mode", "disable"], check=False)
        self.waiting_for_activity = True
        self.logger.write(
            "INFO",
            "power.manual-wake",
            "Timed sleep ended early; automatic shutdown cancelled",
            slept_seconds=int(slept_seconds),
        )
        return self._write(
            "manual-wake",
            slept_seconds=int(slept_seconds),
            waiting_for_new_activity=True,
        )

    def run_forever(self, poll_seconds: int = 15) -> None:
        if not 5 <= poll_seconds <= 300:
            raise CachyFreezeError("Power-policy polling must be between 5 and 300 seconds.")
        while True:
            try:
                self.run_cycle()
            except Exception as error:
                self.waiting_for_activity = True
                self._write(
                    "failed",
                    error=str(error)[:512],
                    waiting_for_new_activity=True,
                )
                self.logger.write(
                    "ERROR",
                    "power.policy.failed",
                    "Idle power-policy cycle failed",
                    error=str(error)[:512],
                )
            self.sleeper(poll_seconds)
