from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cachy_freeze.catalog import AuditLogger
from cachy_freeze.errors import CachyFreezeError, IntegrityError
from cachy_freeze.finalization import FinalizationManager


class FakeRunner:
    def __init__(self, sessions: list[str] | None = None) -> None:
        self.sessions = list(sessions or [])
        self.commands: list[list[str]] = []

    def run(self, command: list[str], *, check: bool = True, **_kwargs: object):
        self.commands.append(command)
        if command[:2] == ["loginctl", "show-user"]:
            output = self.sessions.pop(0) if self.sessions else ""
            return subprocess.CompletedProcess(command, 0, output.encode(), b"")
        if command[0] == "pgrep":
            return subprocess.CompletedProcess(command, 1, b"", b"")
        if command[:2] == ["systemctl", "show"]:
            return subprocess.CompletedProcess(command, 0, b"activating\n", b"")
        return subprocess.CompletedProcess(command, 0, b"", b"")


class FinalizationTests(unittest.TestCase):
    def test_service_reboots_only_after_successful_finalization(self) -> None:
        unit = (
            Path(__file__).parents[1] / "deepfreeze/systemd/cachy-freeze-finalize.service"
        ).read_text(encoding="utf-8")
        start = unit.index("ExecStart=/usr/local/sbin/cachy-freeze finalize run --timeout 180")
        reboot = unit.index("ExecStartPost=/usr/local/sbin/cachy-freeze reboot")

        self.assertLess(start, reboot)
        self.assertNotIn("ExecStopPost=/usr/local/sbin/cachy-freeze reboot", unit)

    def test_frozen_publication_restores_clean_homes_instead_of_capturing_session_data(
        self,
    ) -> None:
        engine = (Path(__file__).parents[1] / "src/cachy_freeze/engine.py").read_text(
            encoding="utf-8"
        )
        publish_and_freeze = engine.split("def publish_and_freeze", 1)[1].split(
            "def request_finalization", 1
        )[0]
        self.assertIn("restore_managed_homes=True", publish_and_freeze)

    def _manager(
        self,
        root: Path,
        *,
        runner: FakeRunner | None = None,
        **kwargs: object,
    ) -> FinalizationManager:
        return FinalizationManager(
            root,
            AuditLogger(root / "audit.jsonl"),
            runner=runner or FakeRunner(),
            template_root=root / "templates",
            **kwargs,
        )

    def test_request_is_durable_and_starts_detached_service(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = FakeRunner()
            manager = self._manager(root, runner=runner)
            account = SimpleNamespace(pw_uid=1001)
            with patch("cachy_freeze.finalization.pwd.getpwnam", return_value=account):
                result = manager.request("person_01", 1001)

            self.assertEqual(result["status"], "pending")
            self.assertEqual(manager.status()["request_id"], result["request_id"])
            self.assertEqual(
                runner.commands[-1],
                ["systemctl", "start", "--no-block", "cachy-freeze-finalize.service"],
            )
            self.assertEqual((root / "finalization.json").stat().st_mode & 0o777, 0o600)

    def test_duplicate_active_request_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = self._manager(root)
            account = SimpleNamespace(pw_uid=1001)
            with patch("cachy_freeze.finalization.pwd.getpwnam", return_value=account):
                manager.request("person_01", 1001)
                with self.assertRaises(CachyFreezeError):
                    manager.request("person_01", 1001)

    def test_interrupted_request_can_be_retried_when_service_is_inactive(self) -> None:
        class InactiveServiceRunner(FakeRunner):
            def run(self, command: list[str], *, check: bool = True, **kwargs: object):
                if command[:2] == ["systemctl", "show"]:
                    self.commands.append(command)
                    return subprocess.CompletedProcess(command, 0, b"inactive\n", b"")
                return super().run(command, check=check, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = InactiveServiceRunner()
            manager = self._manager(root, runner=runner)
            account = SimpleNamespace(pw_uid=1001)
            with patch("cachy_freeze.finalization.pwd.getpwnam", return_value=account):
                first = manager.request("person_01", 1001)
                second = manager.request("person_01", 1001)

            self.assertNotEqual(first["request_id"], second["request_id"])
            self.assertEqual(second["status"], "pending")

    def test_run_waits_for_logout_then_publishes_and_freezes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = FakeRunner(sessions=["c2", ""])
            manager = self._manager(root, runner=runner, sleeper=lambda _seconds: None)
            account = SimpleNamespace(pw_uid=1001)
            with patch("cachy_freeze.finalization.pwd.getpwnam", return_value=account):
                manager.request("person_01", 1001)
            publish = Mock(return_value=SimpleNamespace(snapshot_id="snap-final"))

            result = manager.run(publish, timeout_seconds=10)

            publish.assert_called_once_with("Golden publication after verified logout")
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["snapshot_id"], "snap-final")
            self.assertIn(["loginctl", "terminate-user", "person_01"], runner.commands)

    def test_timeout_fails_closed_without_publishing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = FakeRunner(sessions=["c2"])
            monotonic = Mock(side_effect=[0.0, 2.0])
            manager = self._manager(
                root,
                runner=runner,
                sleeper=lambda _seconds: None,
                monotonic=monotonic,
            )
            account = SimpleNamespace(pw_uid=1001)
            with patch("cachy_freeze.finalization.pwd.getpwnam", return_value=account):
                manager.request("person_01", 1001)
            publish = Mock()

            with self.assertRaisesRegex(CachyFreezeError, "did not close"):
                manager.run(publish, timeout_seconds=1)

            publish.assert_not_called()
            self.assertEqual(manager.status()["status"], "failed")

    def test_malformed_state_is_not_silently_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "finalization.json").write_text(
                json.dumps({"schema": 1, "status": "unknown"}),
                encoding="utf-8",
            )
            with self.assertRaises(IntegrityError):
                self._manager(root).status()


if __name__ == "__main__":
    unittest.main()
