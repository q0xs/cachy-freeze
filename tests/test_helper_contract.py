from __future__ import annotations

import re
import unittest
from pathlib import Path


class HelperContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (Path(__file__).parents[1] / "app/cachy-freeze-manager-helper").read_text(
            encoding="utf-8"
        )

    def _case(self, action: str) -> str:
        match = re.search(
            rf"^  {re.escape(action)}\)\n(?P<body>.*?)(?=^    ;;$)",
            self.source,
            flags=re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match, f"missing helper action: {action}")
        return match.group("body")  # type: ignore[union-attr]

    def test_every_fixed_arity_action_rejects_extra_parameters(self) -> None:
        expected_counts = {
            "status": 1,
            "thaw": 1,
            "thaw-once": 1,
            "freeze": 1,
            "freeze-prepare": 1,
            "reboot": 1,
            "snapshot-list": 1,
            "snapshot-create": 2,
            "snapshot-verify": 2,
            "snapshot-compare": 3,
            "snapshot-delete": 2,
            "snapshot-rollback": 2,
            "snapshot-export": 2,
            "snapshot-import": 2,
            "health": 1,
            "diagnostics": 1,
            "updates-check": 1,
            "updates-apply": 1,
            "applications-status": 1,
            "applications-install": 1,
            "settings-get": 1,
            "settings-set": 10,
            "logs": 1,
            "user-list": 1,
            "user-create": 3,
            "user-delete": 2,
            "user-restore": 2,
            "user-password": 2,
            "user-lock": 2,
            "user-unlock": 2,
        }
        for action, count in expected_counts.items():
            with self.subTest(action=action):
                self.assertIn(f'require_argument_count {count} "$@"', self._case(action))

    def test_optional_login_selection_username_allows_only_zero_or_one_value(self) -> None:
        self.assertIn("(( $# == 1 || $# == 2 ))", self._case("user-autologin"))

    def test_reboot_uses_the_json_backend_contract(self) -> None:
        reboot = self._case("reboot")
        self.assertIn('exec "$BACKEND" reboot', reboot)
        self.assertNotIn("systemctl reboot", reboot)

    def test_setup_splits_grub_password_from_frozen_finalization(self) -> None:
        password = self._case("setup-grub-password")
        freeze = self._case("setup-freeze")
        self.assertIn("read_grub_secret", password)
        self.assertIn("configure-grub-password.sh", password)
        self.assertNotIn("finalize request", password)
        self.assertIn("/etc/cachy-freeze-grub-auth.conf", freeze)
        self.assertIn('"$BACKEND" health', freeze)
        self.assertIn("finalize request", freeze)
        self.assertNotIn("read_grub_secret", freeze)


if __name__ == "__main__":
    unittest.main()
