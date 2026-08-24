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
        self.assertEqual(config.GOLDEN_PENDING_SUBVOL, "@golden.pending")
        active_contract = config.managed_subvolumes - {config.LEGACY_SNAPSHOT_SUBVOL}
        self.assertNotIn("@cachy-snapshots", active_contract)

    def test_rejects_unknown_key(self) -> None:
        path = self.write_config("UNSAFE_OPTION=yes\n")
        with self.assertRaisesRegex(ConfigurationError, "Unknown configuration key"):
            Config.load(path)

    def test_rejects_changed_subvolume_contract(self) -> None:
        path = self.write_config("GOLDEN_SUBVOL=@active\n")
        with self.assertRaisesRegex(ConfigurationError, "Unsupported GOLDEN_SUBVOL"):
            Config.load(path)

    def test_rejects_relative_privileged_path(self) -> None:
        path = self.write_config("STATE_DIR=relative/path\n")
        with self.assertRaisesRegex(ConfigurationError, "must be an absolute path"):
            Config.load(path)

    def test_rejects_noncanonical_root_uuid(self) -> None:
        path = self.write_config("ROOT_UUID=not-a-uuid\n")
        with self.assertRaisesRegex(ConfigurationError, "ROOT_UUID"):
            Config.load(path)


if __name__ == "__main__":
    unittest.main()
