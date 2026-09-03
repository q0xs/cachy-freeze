from __future__ import annotations

import unittest
from pathlib import Path


class HelperContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).parents[1]
        cls.source = (root / "app/cachy-freeze-manager-helper").read_text()
        cls.backend = (root / "app/cachy_freeze_gui/backend.py").read_text()

    def test_helper_allow_list_contains_only_product_actions(self) -> None:
        for action in (
            "setup-install",
            "setup-workstation-install",
            "setup-workstation-check",
            "status",
            "freeze",
            "thaw",
            "reboot",
        ):
            self.assertIn(action, self.source)
        self.assertNotIn("setup-status", self.source)
        for removed in ("snapshot-list", "user-create", "applications-install", "diagnostics"):
            self.assertNotIn(removed, self.source)

    def test_secret_uses_stdin_not_arguments_or_environment(self) -> None:
        self.assertIn("IFS= read -r BOOT_SECRET", self.source)
        self.assertIn("printf '%s\\n' \"$BOOT_SECRET\" |", self.source)
        self.assertNotIn("export BOOT_SECRET", self.source)
        self.assertIn("self.process.write", self.backend)

    def test_workstation_user_uses_stdin_and_embedded_payload(self) -> None:
        workstation_common = (Path(__file__).parents[1] / "workstation/lib/common.sh").read_text()
        self.assertIn("read_target_user", self.source)
        self.assertIn("^[a-zA-Z_][a-zA-Z0-9_-]{0,30}$", self.source)
        self.assertIn("^[a-zA-Z_][a-zA-Z0-9_-]{0,30}$", workstation_common)
        self.assertIn('"$PROJECT_ROOT/workstation/bin/workstation-setup"', self.source)
        self.assertIn('"setup-workstation-install"', self.backend)
        self.assertIn('"setup-workstation-check"', self.backend)

    def test_reboot_uses_backend_json_contract(self) -> None:
        self.assertIn('exec "$BACKEND" "$1"', self.source)
        self.assertNotIn("systemctl reboot", self.source)


if __name__ == "__main__":
    unittest.main()
