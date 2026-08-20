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

    def test_optional_autologin_username_allows_only_zero_or_one_value(self) -> None:
        self.assertIn("(( $# == 1 || $# == 2 ))", self._case("user-autologin"))


if __name__ == "__main__":
    unittest.main()
