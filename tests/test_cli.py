from __future__ import annotations

import unittest

from cachy_freeze.cli import parser


class CliParserTests(unittest.TestCase):
    def test_only_two_mode_and_lifecycle_commands_exist(self) -> None:
        for command in (
            "preflight",
            "version",
            "migrate",
            "status",
            "freeze",
            "thaw",
            "boot-success",
            "reboot",
        ):
            self.assertEqual(parser().parse_args([command]).command, command)

    def test_removed_management_commands_are_rejected(self) -> None:
        for command in ("snapshot", "user", "applications", "settings", "diagnostics"):
            with self.subTest(command=command), self.assertRaises(SystemExit):
                parser().parse_args([command])


if __name__ == "__main__":
    unittest.main()
