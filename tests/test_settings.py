from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cachy_freeze.errors import ConfigurationError
from cachy_freeze.settings import SettingsStore


class SettingsStoreTests(unittest.TestCase):
    def test_defaults_are_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = SettingsStore(Path(directory)).load()
        self.assertEqual(settings["boot_failure_limit"], 3)
        self.assertFalse(settings["auto_snapshot_enabled"])

    def test_update_is_atomic_and_feeds_initramfs_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            updated = SettingsStore(root).update(
                {"boot_failure_limit": 4, "auto_snapshot_enabled": True}
            )
            self.assertEqual(updated["boot_failure_limit"], 4)
            self.assertEqual((root / "boot-failure-limit").read_text(), "4\n")

    def test_invalid_range_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ConfigurationError):
                SettingsStore(Path(directory)).update({"boot_failure_limit": 1})


if __name__ == "__main__":
    unittest.main()
