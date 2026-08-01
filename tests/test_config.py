from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cachy_freeze.config import Config
from cachy_freeze.errors import ConfigurationError


class ConfigTests(unittest.TestCase):
    def write_config(self, content: str) -> Path:
        temporary = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", delete=False
        )
        self.addCleanup(Path(temporary.name).unlink, missing_ok=True)
        with temporary:
            temporary.write(content)
        return Path(temporary.name)

    def test_loads_complete_repository_configuration(self) -> None:
        repository_config = Path(__file__).parents[1] / "deepfreeze" / "etc" / "cachy-freeze.conf"
        config = Config.load(repository_config)
        self.assertEqual(config.MAINTENANCE_SUBVOL, "@")
        self.assertEqual(config.STATE_SUBVOL, "@cachy-state")
        self.assertEqual(config.RETENTION_COUNT, 20)

    def test_rejects_unknown_key(self) -> None:
        path = self.write_config("UNSAFE_OPTION=yes\n")
        with self.assertRaisesRegex(ConfigurationError, "Unknown configuration key"):
            Config.load(path)

    def test_rejects_duplicate_subvolume_names(self) -> None:
        path = self.write_config("GOLDEN_SUBVOL=@active\n")
        with self.assertRaisesRegex(ConfigurationError, "must be unique"):
            Config.load(path)

    def test_rejects_relative_privileged_path(self) -> None:
        path = self.write_config("STATE_DIR=relative/path\n")
        with self.assertRaisesRegex(ConfigurationError, "must be an absolute path"):
            Config.load(path)


if __name__ == "__main__":
    unittest.main()
