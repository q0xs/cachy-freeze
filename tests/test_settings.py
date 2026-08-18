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

    def test_every_numeric_boundary(self) -> None:
        ranges = {
            "retention_count": (1, 1000),
            "auto_snapshot_interval_minutes": (15, 10080),
            "boot_failure_limit": (2, 10),
            "log_retention_lines": (100, 100000),
        }
        for name, (minimum, maximum) in ranges.items():
            for value in (minimum, maximum):
                with (
                    self.subTest(name=name, value=value),
                    tempfile.TemporaryDirectory() as directory,
                ):
                    self.assertEqual(
                        SettingsStore(Path(directory)).update({name: value})[name], value
                    )
            for value in (minimum - 1, maximum + 1, True, "invalid"):
                with (
                    self.subTest(name=name, value=value),
                    tempfile.TemporaryDirectory() as directory,
                    self.assertRaises(ConfigurationError),
                ):
                    SettingsStore(Path(directory)).update({name: value})

    def test_boolean_locale_theme_and_unknown_parameters(self) -> None:
        for name in (
            "auto_snapshot_enabled",
            "update_checks_enabled",
            "network_online_checks",
        ):
            for value in (True, False):
                with (
                    self.subTest(name=name, value=value),
                    tempfile.TemporaryDirectory() as directory,
                ):
                    self.assertIs(SettingsStore(Path(directory)).update({name: value})[name], value)
            for value in (0, 1, "true", None):
                with (
                    self.subTest(name=name, value=value),
                    tempfile.TemporaryDirectory() as directory,
                    self.assertRaises(ConfigurationError),
                ):
                    SettingsStore(Path(directory)).update({name: value})

        for changes in (
            {"language": "de"},
            {"theme": "blue"},
            {"unknown": True},
            {"schema": 2},
        ):
            with tempfile.TemporaryDirectory() as directory, self.assertRaises(ConfigurationError):
                SettingsStore(Path(directory)).update(changes)

    def test_malformed_settings_are_not_silently_replaced(self) -> None:
        for content in ("not-json", "[]", '{"schema":2}'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "settings.json").write_text(content, encoding="utf-8")
                with self.subTest(content=content), self.assertRaises(ConfigurationError):
                    SettingsStore(root).load()


if __name__ == "__main__":
    unittest.main()
