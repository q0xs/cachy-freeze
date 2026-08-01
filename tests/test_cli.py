from __future__ import annotations

import unittest

from cachy_freeze.cli import parser


class CliParserTests(unittest.TestCase):
    def test_snapshot_create_contract(self) -> None:
        arguments = parser().parse_args(
            ["snapshot", "create", "--description", "Before kernel update"]
        )
        self.assertEqual(arguments.command, "snapshot")
        self.assertEqual(arguments.snapshot_command, "create")
        self.assertEqual(arguments.description, "Before kernel update")

    def test_verify_full_contract(self) -> None:
        arguments = parser().parse_args(
            ["snapshot", "verify", "snap-20260801T120000Z-1234abcd", "--full"]
        )
        self.assertTrue(arguments.full)

    def test_cleanup_keep_must_be_integer(self) -> None:
        with self.assertRaises(SystemExit):
            parser().parse_args(["snapshot", "cleanup", "--keep", "invalid"])

    def test_export_and_import_contracts(self) -> None:
        exported = parser().parse_args(["snapshot", "export", "snap-20260801T120000Z-1234abcd"])
        imported = parser().parse_args(
            ["snapshot", "import", "snap-20260801T120000Z-1234abcd.btrfs"]
        )
        self.assertEqual(exported.snapshot_command, "export")
        self.assertEqual(imported.archive_name, "snap-20260801T120000Z-1234abcd.btrfs")

    def test_platform_management_contracts(self) -> None:
        self.assertEqual(parser().parse_args(["thaw-once"]).command, "thaw-once")
        self.assertEqual(
            parser().parse_args(["applications", "status"]).operation,
            "status",
        )
        user = parser().parse_args(["user", "create", "person01", "--display-name", "Person One"])
        self.assertEqual(user.user_command, "create")
        settings = parser().parse_args(
            [
                "settings",
                "set",
                "--retention-count",
                "20",
                "--auto-snapshot-enabled",
                "true",
                "--auto-snapshot-interval",
                "60",
                "--update-checks-enabled",
                "true",
                "--network-online-checks",
                "true",
                "--boot-failure-limit",
                "3",
                "--log-retention-lines",
                "5000",
                "--language",
                "tr",
                "--theme",
                "dark",
            ]
        )
        self.assertEqual(settings.boot_failure_limit, 3)


if __name__ == "__main__":
    unittest.main()
