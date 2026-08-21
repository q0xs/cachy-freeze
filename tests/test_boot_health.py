from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cachy_freeze.catalog import AuditLogger
from cachy_freeze.config import Config
from cachy_freeze.engine import FreezeEngine


class RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command: list[str]) -> None:
        self.commands.append(command)


class BootHealthTests(unittest.TestCase):
    def test_success_resets_attempts_and_consumes_recovery_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "boot-attempts").write_text("3\n", encoding="utf-8")
            (root / "recovery-event").write_text("automatic-rollback\n", encoding="utf-8")
            config = Config(STATE_DIR=str(root), LOG_FILE=str(root / "audit.jsonl"))
            engine = FreezeEngine(config, logger=AuditLogger(root / "audit.jsonl"))
            with patch.object(engine, "require_root"):
                result = engine.mark_boot_successful()
            self.assertTrue(result["automatic_recovery"])
            self.assertEqual((root / "boot-attempts").read_text(), "0\n")
            self.assertFalse((root / "recovery-event").exists())
            self.assertIn("last_automatic_recovery", (root / "boot-health.json").read_text())

    def test_reboot_is_queued_without_blocking_the_gui_response(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit_path = root / "audit.jsonl"
            runner = RecordingRunner()
            engine = FreezeEngine(
                Config(STATE_DIR=str(root), LOG_FILE=str(audit_path)),
                runner=runner,  # type: ignore[arg-type]
                logger=AuditLogger(audit_path),
            )

            with patch.object(engine, "require_root"):
                result = engine.request_reboot()

            self.assertEqual(result, {"reboot_queued": True})
            self.assertEqual(runner.commands, [["systemctl", "reboot", "--no-block"]])
            self.assertIn('"action": "system.reboot"', audit_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
