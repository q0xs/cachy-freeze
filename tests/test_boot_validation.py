from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from cachy_freeze.catalog import AuditLogger
from cachy_freeze.errors import CachyFreezeError, IntegrityError
from cachy_freeze.validation import BootValidationManager

SNAPSHOT_ID = "snap-20260820T120000Z-deadbeef"
BOOT_ID = "12345678-1234-1234-1234-123456789abc"


class FakeRunner:
    def __init__(self, *, graphical: bool = True) -> None:
        self.graphical = graphical
        self.commands: list[list[str]] = []

    def run(self, command: list[str], *, check: bool = True, **_: object):
        self.commands.append(command)
        value = ""
        if command[:3] == ["loginctl", "show-user", "employee"]:
            value = "c2"
        elif command[:3] == ["loginctl", "show-session", "c2"]:
            property_name = command[3]
            values = {
                "--property=Name": "employee",
                "--property=Type": "wayland" if self.graphical else "tty",
                "--property=State": "active",
            }
            value = values.get(property_name, "")
        return subprocess.CompletedProcess(command, 0, stdout=f"{value}\n".encode(), stderr=b"")


class Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds


class BootValidationTests(unittest.TestCase):
    def manager(
        self,
        root: Path,
        *,
        runner: FakeRunner | None = None,
        clock: Clock | None = None,
    ) -> BootValidationManager:
        active_clock = clock or Clock()
        boot_id_path = root / "boot-id"
        boot_id_path.write_text(f"{BOOT_ID}\n", encoding="utf-8")
        return BootValidationManager(
            root,
            AuditLogger(root / "audit.jsonl"),
            runner=runner or FakeRunner(),
            sleeper=active_clock.sleep,
            monotonic=active_clock.monotonic,
            boot_id_path=boot_id_path,
        )

    def write_markers(self, root: Path) -> None:
        for name in (
            "active-reset-boot-id",
            "home-reset-boot-id",
            "admin-restrict-boot-id",
        ):
            (root / name).write_text(f"{BOOT_ID}\n", encoding="utf-8")

    def test_arm_writes_private_durable_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = self.manager(root)
            result = manager.arm(SNAPSHOT_ID, "employee")
            self.assertEqual(result["status"], "awaiting-frozen-boot")
            self.assertEqual(manager.path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(manager.status()["expected_user"], "employee")

    def test_real_frozen_graphical_boot_is_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = FakeRunner()
            manager = self.manager(root, runner=runner)
            manager.arm(SNAPSHOT_ID, "employee")
            self.write_markers(root)
            result = manager.validate(
                running_mode="frozen",
                current_subvolume="@active",
                golden_present=True,
                active_present=True,
            )
            self.assertEqual(result["status"], "verified")
            self.assertEqual(result["verified_boot_id"], BOOT_ID)
            self.assertTrue(
                any(command[:2] == ["loginctl", "show-user"] for command in runner.commands)
            )

    def test_missing_current_boot_marker_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = self.manager(root)
            manager.arm(SNAPSHOT_ID, None)
            (root / "active-reset-boot-id").write_text(f"{BOOT_ID}\n", encoding="utf-8")
            with self.assertRaisesRegex(CachyFreezeError, "reset evidence is missing"):
                manager.validate(
                    running_mode="frozen",
                    current_subvolume="@active",
                    golden_present=True,
                    active_present=True,
                )
            state = manager.status()
            self.assertEqual(state["status"], "failed")
            self.assertIn("home-reset-boot-id", state["error"])

    def test_graphical_login_timeout_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            clock = Clock()
            manager = self.manager(root, runner=FakeRunner(graphical=False), clock=clock)
            manager.arm(SNAPSHOT_ID, "employee")
            self.write_markers(root)
            with self.assertRaisesRegex(CachyFreezeError, "graphical session"):
                manager.validate(
                    running_mode="frozen",
                    current_subvolume="@active",
                    golden_present=True,
                    active_present=True,
                    timeout_seconds=1,
                )
            self.assertEqual(manager.status()["status"], "failed")

    def test_malformed_state_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = self.manager(root)
            manager.path.write_text(json.dumps({"schema": 1, "status": "verified"}))
            with self.assertRaisesRegex(IntegrityError, "snapshot id"):
                manager.status()


if __name__ == "__main__":
    unittest.main()
