from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from cachy_freeze.catalog import AuditLogger
from cachy_freeze.errors import IntegrityError
from cachy_freeze.power import IdlePowerManager


class Clock:
    def __init__(self) -> None:
        self.wall = 10_000.0
        self.monotonic = 5_000.0
        self.elapsed = 5_000.0


class FakeRunner:
    def __init__(self, clock: Clock, *, wake_after: int = 3600) -> None:
        self.clock = clock
        self.wake_after = wake_after
        self.idle = True
        self.commands: list[list[str]] = []

    def text(self, command: list[str], **_: object) -> str:
        self.commands.append(command)
        if "--property=IdleHint" in command:
            return "yes" if self.idle else "no"
        if "--property=IdleSinceHintMonotonic" in command:
            return "1000000000"
        return ""

    def run(self, command: list[str], **_: object):
        self.commands.append(command)
        if "--mode" in command and "mem" in command:
            self.clock.wall += self.wake_after
            self.clock.elapsed += self.wake_after
        return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")


class IdlePowerPolicyTests(unittest.TestCase):
    def manager(
        self,
        root: Path,
        *,
        wake_after: int = 3600,
        supported: bool = True,
    ) -> tuple[IdlePowerManager, FakeRunner]:
        clock = Clock()
        runner = FakeRunner(clock, wake_after=wake_after)
        rtcwake = root / "rtcwake"
        wakealarm = root / "wakealarm"
        if supported:
            rtcwake.touch(mode=0o755)
            wakealarm.touch(mode=0o600)
        boot_id = root / "boot-id"
        boot_id.write_text("12345678-1234-1234-1234-123456789abc\n", encoding="utf-8")
        manager = IdlePowerManager(
            root,
            AuditLogger(root / "audit.jsonl"),
            runner=runner,  # type: ignore[arg-type]
            monotonic=lambda: clock.monotonic,
            wall_clock=lambda: clock.wall,
            elapsed_clock=lambda: clock.elapsed,
            rtcwake_path=rtcwake,
            wakealarm_path=wakealarm,
            boot_id_path=boot_id,
        )
        return manager, runner

    def test_one_hour_idle_then_full_sleep_powers_off(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager, runner = self.manager(Path(directory))
            result = manager.run_cycle()
            self.assertEqual(result["status"], "shutting-down")
            self.assertIn(
                ["systemctl", "poweroff", "--no-block"],
                runner.commands,
            )
            self.assertEqual(manager.path.stat().st_mode & 0o777, 0o600)

    def test_manual_early_wake_cancels_shutdown_until_new_activity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager, runner = self.manager(Path(directory), wake_after=600)
            first = manager.run_cycle()
            second = manager.run_cycle()
            self.assertEqual(first["status"], "manual-wake")
            self.assertTrue(second["waiting_for_new_activity"])
            self.assertNotIn(["systemctl", "poweroff", "--no-block"], runner.commands)
            runner.idle = False
            self.assertEqual(manager.run_cycle()["status"], "active")
            self.assertFalse(manager.waiting_for_activity)

    def test_manual_wake_cancellation_survives_service_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager, _runner = self.manager(root, wake_after=600)
            self.assertEqual(manager.run_cycle()["status"], "manual-wake")

            restarted, restarted_runner = self.manager(root)
            result = restarted.run_cycle()
            self.assertEqual(result["status"], "manual-wake")
            self.assertTrue(result["waiting_for_new_activity"])
            self.assertNotIn(
                [str(root / "rtcwake"), "--mode", "mem", "--seconds", "3600"],
                restarted_runner.commands,
            )

    def test_missing_rtc_support_fails_visible_and_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager, runner = self.manager(Path(directory), supported=False)
            result = manager.run_cycle()
            self.assertEqual(result["status"], "unsupported")
            self.assertFalse(manager.status()["supported"])
            self.assertNotIn(["systemctl", "poweroff", "--no-block"], runner.commands)

    def test_malformed_state_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager, _runner = self.manager(Path(directory))
            manager.path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(IntegrityError, "schema"):
                manager.status()


if __name__ == "__main__":
    unittest.main()
