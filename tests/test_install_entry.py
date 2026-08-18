from __future__ import annotations

import unittest
from pathlib import Path


class InstallEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (Path(__file__).parents[1] / "install.sh").read_text(encoding="utf-8")

    def test_terminal_install_uses_sudo(self) -> None:
        self.assertIn("[[ -t 0 && -t 1 ]]", self.source)
        self.assertIn('exec sudo /usr/bin/bash "$SCRIPT_DIR/install.sh" "$@"', self.source)

    def test_graphical_install_uses_policykit(self) -> None:
        self.assertIn("command -v pkexec", self.source)
        self.assertIn('exec pkexec /usr/bin/bash "$SCRIPT_DIR/install.sh" "$@"', self.source)


if __name__ == "__main__":
    unittest.main()
