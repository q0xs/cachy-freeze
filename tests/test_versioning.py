from __future__ import annotations

import json
import tempfile
import tomllib
import unittest
from pathlib import Path

from cachy_freeze import __version__
from cachy_freeze.catalog import AuditLogger
from cachy_freeze.errors import IntegrityError
from cachy_freeze.versioning import APP_VERSION, STATE_SCHEMA_VERSION, StateMigrationManager


class StateMigrationTests(unittest.TestCase):
    def manager(self, root: Path) -> StateMigrationManager:
        return StateMigrationManager(root, AuditLogger(root / "audit.jsonl"))

    def test_legacy_state_migrates_once_and_is_private(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = self.manager(root)
            self.assertTrue(manager.status()["migration_required"])
            first = manager.migrate()
            second = manager.migrate()
            self.assertTrue(first["changed"])
            self.assertFalse(second["changed"])
            self.assertEqual(first["state_schema"], STATE_SCHEMA_VERSION)
            self.assertEqual(first["application_version"], APP_VERSION)
            self.assertEqual(manager.path.stat().st_mode & 0o777, 0o600)

    def test_newer_state_blocks_downgrade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = self.manager(root)
            manager.path.write_text(
                json.dumps({"schema": 1, "state_schema": STATE_SCHEMA_VERSION + 1}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(IntegrityError, "downgrade is blocked"):
                manager.status()

    def test_malformed_state_record_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = self.manager(root)
            manager.path.write_text("not-json", encoding="utf-8")
            with self.assertRaisesRegex(IntegrityError, "cannot be read"):
                manager.migrate()

    def test_release_version_is_consistent(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        release = (project_root / "VERSION").read_text(encoding="utf-8").strip()
        pyproject = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(release, APP_VERSION)
        self.assertEqual(__version__, APP_VERSION)
        self.assertEqual(pyproject["project"]["version"], APP_VERSION)


if __name__ == "__main__":
    unittest.main()
