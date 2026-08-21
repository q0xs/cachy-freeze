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
        self.assertEqual(parser().parse_args(["reboot"]).command, "reboot")
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
                "en",
                "--theme",
                "dark",
            ]
        )
        self.assertEqual(settings.boot_failure_limit, 3)

    def test_every_command_and_parameter_shape_parses(self) -> None:
        snapshot_id = "snap-20260801T120000Z-1234abcd"
        backup_id = "20260801T120000Z-person01"
        commands = (
            ["preflight"],
            ["version"],
            ["migrate"],
            ["status"],
            ["freeze"],
            ["thaw"],
            ["thaw-once"],
            ["reboot"],
            ["health"],
            ["diagnostics"],
            ["boot-success"],
            ["auto-snapshot"],
            ["finalize", "request", "person01", "--uid", "1001"],
            ["finalize", "run", "--timeout", "180"],
            ["finalize", "status"],
            ["idle-power", "status"],
            ["idle-power", "run", "--poll", "15"],
            ["updates", "check"],
            ["updates", "apply"],
            ["applications", "status"],
            ["applications", "install"],
            ["settings", "get"],
            ["publish", "--description", "Golden"],
            ["snapshot", "create", "--description", "Before update"],
            ["snapshot", "list"],
            ["snapshot", "verify", snapshot_id, "--full"],
            ["snapshot", "delete", snapshot_id],
            ["snapshot", "compare", snapshot_id, snapshot_id],
            ["snapshot", "rollback", snapshot_id],
            ["snapshot", "export", snapshot_id],
            ["snapshot", "import", f"{snapshot_id}.btrfs"],
            ["snapshot", "cleanup", "--keep", "20"],
            ["logs", "--limit", "200"],
            ["user", "list"],
            ["user", "create", "person01", "--display-name", "Person One"],
            ["user", "delete", "person01"],
            ["user", "restore", backup_id],
            ["user", "password", "person01"],
            ["user", "lock", "person01"],
            ["user", "unlock", "person01"],
            ["user", "autologin"],
            ["user", "autologin", "person01"],
        )
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(parser().parse_args(command).command, command[0])

    def test_invalid_enum_parameters_are_rejected(self) -> None:
        for command in (
            ["updates", "invalid"],
            ["applications", "invalid"],
            ["settings", "set", "--language", "invalid"],
            ["snapshot", "invalid"],
            ["user", "invalid"],
        ):
            with self.subTest(command=command), self.assertRaises(SystemExit):
                parser().parse_args(command)


if __name__ == "__main__":
    unittest.main()
