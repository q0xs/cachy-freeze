from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cachy_freeze.catalog import AuditLogger, OperationJournal
from cachy_freeze.config import Config
from cachy_freeze.engine import FreezeEngine
from cachy_freeze.errors import CachyFreezeError, IntegrityError


class FakeBtrfsRunner:
    def __init__(self, top: Path) -> None:
        self.top = top
        self.commands: list[list[str]] = []
        self.mode = "thawed"
        self.recovery = "0"
        self.fail_snapshot_destination: str | None = None
        self.mounted_sources: dict[str, str] = {}
        self.nested_sources: list[str] = []
        self.disposable_root_id = 300
        self.subvolume_records: list[str] = []

    @staticmethod
    def _completed(command: list[str], returncode: int = 0, output: str = ""):
        return subprocess.CompletedProcess(command, returncode, output.encode(), b"")

    def run(self, command: list[str], *, check: bool = True, **_kwargs: object):
        command = [str(part) for part in command]
        self.commands.append(command)
        if command[:2] == ["mountpoint", "-q"]:
            return self._completed(command)
        if command[:3] == ["btrfs", "subvolume", "show"]:
            return self._completed(command, 0 if Path(command[-1]).is_dir() else 1)
        if command[:3] == ["btrfs", "property", "get"]:
            readonly = (Path(command[-2]) / ".fake-read-only").exists()
            return self._completed(command, output=f"ro={'true' if readonly else 'false'}\n")
        if command[:3] == ["btrfs", "property", "set"]:
            marker = Path(command[-3]) / ".fake-read-only"
            if command[-1] == "true":
                marker.touch()
            else:
                marker.unlink(missing_ok=True)
            return self._completed(command)
        if command[:3] == ["btrfs", "subvolume", "create"]:
            Path(command[-1]).mkdir()
            return self._completed(command)
        if command[:3] == ["btrfs", "subvolume", "snapshot"]:
            source = Path(command[-2])
            destination = Path(command[-1])
            if self.fail_snapshot_destination == destination.name:
                raise IntegrityError("injected snapshot failure")
            shutil.copytree(source, destination)
            marker = destination / ".fake-read-only"
            if "-r" in command:
                marker.touch()
            else:
                marker.unlink(missing_ok=True)
            if source == self.top / "@":
                for nested in self.nested_sources:
                    relative = Path(nested).relative_to("@")
                    nested_destination = destination / relative
                    if nested_destination.exists():
                        shutil.rmtree(nested_destination)
                    nested_destination.mkdir(parents=True)
            return self._completed(command)
        if command[:3] == ["btrfs", "subvolume", "delete"]:
            if "-i" in command:
                return self._completed(command)
            shutil.rmtree(command[-1])
            return self._completed(command)
        if command and command[0] == "find":
            directory = Path(command[1])
            for child in directory.iterdir():
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            return self._completed(command)
        if command and command[0] == "cp":
            source = Path(command[-2])
            destination = Path(command[-1])
            shutil.copytree(source, destination, dirs_exist_ok=True)
            (destination / ".fake-read-only").unlink(missing_ok=True)
            return self._completed(command)
        if command and command[0] == "grub-editenv" and "set" in command:
            for assignment in command[3:]:
                if assignment.startswith("cachy_mode="):
                    self.mode = assignment.split("=", 1)[1]
                if assignment.startswith("cachy_recovery="):
                    self.recovery = assignment.split("=", 1)[1]
            return self._completed(command)
        if command == ["systemctl", "reboot", "--no-block"] or command == ["sync"]:
            return self._completed(command)
        raise AssertionError(f"Unexpected command: {command}")

    def text(self, command: list[str], *, check: bool = True) -> str:
        command = [str(part) for part in command]
        if command[:3] == ["btrfs", "inspect-internal", "rootid"]:
            return str(self.disposable_root_id)
        if command[:2] == ["findmnt", "--json"]:
            children = [
                {
                    "target": target,
                    "source": f"/dev/loop0[/{subvolume}]",
                    "fstype": "btrfs",
                    "fsroot": f"/{subvolume}",
                    "uuid": "11111111-2222-3333-4444-555555555555",
                }
                for target, subvolume in sorted(self.mounted_sources.items())
            ]
            return json.dumps(
                {
                    "filesystems": [
                        {
                            "target": "/",
                            "source": "/dev/loop0[/@]",
                            "fstype": "btrfs",
                            "fsroot": "/@",
                            "uuid": "11111111-2222-3333-4444-555555555555",
                            "children": children,
                        }
                    ]
                }
            )
        if command[:4] == ["btrfs", "subvolume", "list", "-o"]:
            if Path(command[-1]) == self.top / "@":
                return "\n".join(
                    f"ID {300 + index} gen 1 top level 256 path {path}"
                    for index, path in enumerate(self.nested_sources)
                )
            return ""
        if command[:3] == ["btrfs", "subvolume", "list"]:
            return "\n".join(self.subvolume_records)
        if command[:4] == ["findmnt", "-n", "-o", "FSTYPE"]:
            return "btrfs"
        if command[:4] == ["findmnt", "-n", "-o", "FSROOT"]:
            return "/"
        if command[:4] == ["findmnt", "-n", "-o", "SOURCE"]:
            root = os.environ.get("CACHY_FREEZE_ROOT_SUBVOLUME", "@")
            return f"/dev/loop0[/{root}]"
        if command[:4] == ["findmnt", "-n", "-o", "UUID"]:
            return "11111111-2222-3333-4444-555555555555"
        if command and command[0] == "grub-editenv":
            return (
                f"cachy_mode={self.mode}\n"
                "saved_entry=cachyos-current\n"
                f"cachy_recovery={self.recovery}"
            )
        completed = self.run(command, check=check)
        return (completed.stdout or b"").decode().strip()


class LifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.top = self.root / "top"
        self.state = self.root / "state"
        self.top.mkdir()
        self.state.mkdir()
        self.config = Config(
            TOP_MOUNT=str(self.top),
            STATE_DIR=str(self.state),
            LOG_FILE=str(self.root / "audit.jsonl"),
            LOCK_FILE=str(self.root / "operation.lock"),
        )
        self.runner = FakeBtrfsRunner(self.top)
        self.engine = FreezeEngine(self.config, runner=self.runner)
        root_patch = patch.object(self.engine, "require_root")
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self._root("@", "maintained")
        self._root("@golden", "old", readonly=True)
        self._root("@active", "runtime")
        os.environ["CACHY_FREEZE_ROOT_SUBVOLUME"] = "@"
        self.addCleanup(os.environ.pop, "CACHY_FREEZE_ROOT_SUBVOLUME", None)

    def _root(self, name: str, marker: str, *, readonly: bool = False) -> Path:
        root = self.top / name
        root.mkdir()
        (root / "boot").mkdir()
        (root / "boot/vmlinuz-linux-cachyos").write_text("kernel")
        (root / "boot/initramfs-linux-cachyos.img").write_text("initramfs")
        (root / "boot/grub").mkdir()
        (root / "boot/grub/grub.cfg").write_text("menuentry test --id 'cachyos-current' {}\n")
        (root / "boot/grub/grubenv").write_text("")
        (root / "etc").mkdir()
        (root / "etc/os-release").write_text("ID=cachyos\n")
        (root / "sbin").mkdir()
        (root / "usr/lib/systemd").mkdir(parents=True)
        systemd = root / "usr/lib/systemd/systemd"
        systemd.write_text("#!/bin/sh\n")
        systemd.chmod(0o755)
        (root / "sbin/init").symlink_to("../usr/lib/systemd/systemd")
        (root / marker).write_text(marker)
        if readonly:
            (root / ".fake-read-only").touch()
        return root

    def test_freeze_replaces_baseline_from_thawed_without_history(self) -> None:
        result = self.engine.freeze()
        self.assertEqual(result["mode"], "frozen")
        self.assertTrue((self.top / "@golden/maintained").exists())
        self.assertFalse((self.top / "@golden/runtime").exists())
        self.assertTrue((self.top / "@active/maintained").exists())
        self.assertFalse((self.top / "@active/runtime").exists())
        for forbidden in (
            "@golden.next",
            "@golden.pending",
            "@active.next",
            "@active.pending",
            "@cachy-capture",
            "@cachy-snapshots",
        ):
            self.assertFalse((self.top / forbidden).exists())
        self.assertFalse((self.state / "transaction.json").exists())

    def test_freeze_flattens_standard_cachyos_mounts_into_disposable_root(self) -> None:
        (self.top / "@/home").mkdir()
        home = self.top / "@home"
        home.mkdir()
        (home / "approved-home-marker").write_text("baseline")
        self.runner.mounted_sources["/home"] = "@home"

        self.engine.freeze()

        self.assertTrue((self.top / "@golden/home/approved-home-marker").exists())
        self.assertTrue((self.top / "@active/home/approved-home-marker").exists())
        self.assertFalse((self.top / "@cachy-capture").exists())
        copy_commands = [command for command in self.runner.commands if command[0] == "cp"]
        self.assertTrue(copy_commands)
        self.assertTrue(all("--reflink=auto" in command for command in copy_commands))
        self.assertTrue(all("--reflink=always" not in command for command in copy_commands))
        (self.top / "@active/home/runtime-only-marker").write_text("discard")
        self.assertFalse((home / "runtime-only-marker").exists())

    def test_freeze_rejects_an_unmounted_standard_data_subvolume(self) -> None:
        (self.top / "@/home").mkdir()
        (self.top / "@home").mkdir()

        with self.assertRaisesRegex(
            CachyFreezeError, "Standard CachyOS subvolume @home is not mounted at /home"
        ):
            self.engine.freeze()

        self.assertTrue((self.top / "@golden/old").exists())
        self.assertTrue((self.top / "@active/runtime").exists())
        self.assertFalse((self.top / "@golden.next").exists())

    def test_freeze_excludes_snapper_history_and_flattens_systemd_subvolumes(self) -> None:
        snapshots = self.top / "@/.snapshots"
        machines = self.top / "@/var/lib/machines"
        portables = self.top / "@/var/lib/portables"
        snapshots.mkdir(parents=True)
        machines.mkdir(parents=True)
        portables.mkdir(parents=True)
        (snapshots / "historical-user-data").write_text("must-not-copy")
        (machines / "approved-machine-data").write_text("baseline")
        self.runner.nested_sources = [
            "@/.snapshots",
            "@/var/lib/machines",
            "@/var/lib/portables",
        ]

        self.engine.freeze()

        self.assertFalse((self.top / "@golden/.snapshots/historical-user-data").exists())
        self.assertTrue((self.top / "@golden/var/lib/machines/approved-machine-data").exists())
        self.assertTrue((snapshots / "historical-user-data").exists())
        self.assertFalse((self.top / "@cachy-capture").exists())

    def test_repeated_freeze_does_not_accumulate_history(self) -> None:
        for marker in ("first", "second", "third"):
            (self.top / f"@/{marker}").write_text(marker)
            self.runner.mode = "thawed"
            self.engine.freeze()
        self.assertEqual(
            sorted(path.name for path in self.top.iterdir()),
            ["@", "@active", "@golden"],
        )

    def test_disposable_cleanup_deletes_nested_subvolumes_deepest_first(self) -> None:
        self.runner.subvolume_records = [
            "ID 302 gen 1 top level 301 path @active/runtime nested/child",
            "ID 301 gen 1 top level 300 path @active/runtime nested",
            "ID 400 gen 1 top level 5 path @unrelated",
        ]

        self.engine._delete_subvolume("@active")

        id_deletions = [
            command
            for command in self.runner.commands
            if command[:4] == ["btrfs", "subvolume", "delete", "-i"]
        ]
        self.assertEqual(
            id_deletions,
            [
                ["btrfs", "subvolume", "delete", "-i", "302", str(self.top)],
                ["btrfs", "subvolume", "delete", "-i", "301", str(self.top)],
            ],
        )
        self.assertFalse((self.top / "@active").exists())

    def test_disposable_cleanup_rejects_malformed_subvolume_records(self) -> None:
        self.runner.subvolume_records = ["malformed"]

        with self.assertRaisesRegex(IntegrityError, "malformed nested-subvolume record"):
            self.engine._delete_subvolume("@active")

        self.assertTrue((self.top / "@active").exists())

    def test_thaw_never_promotes_runtime_and_discards_it_after_boot(self) -> None:
        (self.top / "@active/unique-frozen-marker").write_text("secret")
        os.environ["CACHY_FREEZE_ROOT_SUBVOLUME"] = "@active"
        self.runner.mode = "frozen"
        self.engine.thaw()
        self.assertFalse((self.top / "@/unique-frozen-marker").exists())
        self.assertFalse((self.top / "@golden/unique-frozen-marker").exists())
        os.environ["CACHY_FREEZE_ROOT_SUBVOLUME"] = "@"
        self.engine.mark_boot_successful()
        self.assertFalse((self.top / "@active").exists())

    def test_interrupted_freeze_recovers_old_pair(self) -> None:
        self.runner.fail_snapshot_destination = "@active.next"
        with self.assertRaisesRegex(IntegrityError, "injected"):
            self.engine.freeze()
        self.assertTrue((self.state / "transaction.json").exists())
        self.runner.fail_snapshot_destination = None
        status = self.engine.status()
        self.assertEqual(status["running_mode"], "thawed")
        self.assertTrue((self.top / "@golden/old").exists())
        self.assertTrue((self.top / "@active/runtime").exists())
        self.assertFalse((self.state / "transaction.json").exists())
        self.assertFalse((self.top / "@golden.next").exists())

    def test_freeze_rejects_baseline_without_usable_init(self) -> None:
        (self.top / "@/sbin/init").unlink()

        with self.assertRaisesRegex(IntegrityError, "required root file"):
            self.engine.freeze()

        self.assertTrue((self.top / "@golden/old").exists())
        self.assertTrue((self.top / "@active/runtime").exists())
        self.assertTrue((self.state / "transaction.json").exists())

    def test_frozen_boot_success_requires_current_reset_proof(self) -> None:
        boot_id = "11111111-2222-3333-4444-555555555555"
        (self.state / "active-reset-boot-id").write_text(f"{boot_id}\n")
        os.environ["CACHY_FREEZE_ROOT_SUBVOLUME"] = "@active"
        self.runner.mode = "frozen"

        with patch.object(self.engine, "_current_boot_id", return_value=boot_id):
            result = self.engine.mark_boot_successful()

        self.assertEqual(result["mode"], "frozen")

    def test_frozen_boot_success_rejects_stale_reset_proof(self) -> None:
        (self.state / "active-reset-boot-id").write_text("11111111-2222-3333-4444-555555555555\n")
        os.environ["CACHY_FREEZE_ROOT_SUBVOLUME"] = "@active"
        self.runner.mode = "frozen"

        with (
            patch.object(
                self.engine,
                "_current_boot_id",
                return_value="22222222-3333-4444-5555-666666666666",
            ),
            self.assertRaisesRegex(IntegrityError, "not reset during the current boot"),
        ):
            self.engine.mark_boot_successful()

    def test_thawed_boot_removes_stale_reset_proof(self) -> None:
        marker = self.state / "active-reset-boot-id"
        marker.write_text("11111111-2222-3333-4444-555555555555\n")

        self.engine.mark_boot_successful()

        self.assertFalse(marker.exists())

    def test_interrupted_auxiliary_capture_is_removed_during_recovery(self) -> None:
        (self.top / "@/home").mkdir()
        (self.top / "@home").mkdir()
        self.runner.mounted_sources["/home"] = "@home"
        self.runner.fail_snapshot_destination = "home"

        with self.assertRaisesRegex(IntegrityError, "injected"):
            self.engine.freeze()
        self.assertTrue((self.top / "@cachy-capture").exists())
        self.assertTrue((self.state / "transaction.json").exists())

        self.runner.fail_snapshot_destination = None
        self.engine.status()
        self.assertFalse((self.top / "@cachy-capture").exists())
        self.assertFalse((self.state / "transaction.json").exists())

    def test_legacy_snapshot_migration_requires_exact_owned_catalog(self) -> None:
        history = self.top / "@cachy-snapshots"
        history.mkdir()
        snapshot_id = "snap-20260801T120000Z-1234abcd"
        (history / snapshot_id).mkdir()
        (self.state / "snapshots.json").write_text(
            json.dumps(
                {
                    "schema": 1,
                    "snapshots": [
                        {
                            "snapshot_id": snapshot_id,
                            "subvolume": f"@cachy-snapshots/{snapshot_id}",
                        }
                    ],
                }
            )
        )
        with patch.object(self.engine, "_recover_transaction_locked"):
            removed = self.engine._delete_legacy_history_locked()
        self.assertEqual(removed, [snapshot_id])
        self.assertFalse(history.exists())

    def test_legacy_snapshot_migration_fails_closed_on_mismatch(self) -> None:
        history = self.top / "@cachy-snapshots"
        history.mkdir()
        (history / "unexpected").mkdir()
        (self.state / "snapshots.json").write_text('{"schema":1,"snapshots":[]}')
        with self.assertRaisesRegex(IntegrityError, "do not match"):
            self.engine._delete_legacy_history_locked()

    def test_legacy_snapshot_migration_resumes_after_committed_delete(self) -> None:
        history = self.top / "@cachy-snapshots"
        history.mkdir()
        deleted = "snap-20260801T120000Z-1234abcd"
        remaining = "snap-20260801T120001Z-5678abcd"
        (history / remaining).mkdir()
        items = [
            {"snapshot_id": item, "subvolume": f"@cachy-snapshots/{item}"}
            for item in (deleted, remaining)
        ]
        (self.state / "snapshots.json").write_text(json.dumps({"schema": 1, "snapshots": items}))
        (self.state / "history-migration.json").write_text(
            json.dumps(
                {
                    "schema": 1,
                    "owned_snapshots": [deleted, remaining],
                    "remaining_snapshots": [deleted, remaining],
                }
            )
        )
        removed = self.engine._delete_legacy_history_locked()
        self.assertEqual(removed, [deleted, remaining])
        self.assertFalse(history.exists())
        self.assertFalse((self.state / "history-migration.json").exists())

    def test_explicit_reboot_uses_structured_arguments(self) -> None:
        result = self.engine.request_reboot()
        self.assertEqual(result, {"reboot_queued": True})
        self.assertIn(["systemctl", "reboot", "--no-block"], self.runner.commands)

    def test_conflicting_kernel_marker_and_root_identity_is_unknown(self) -> None:
        with patch("cachy_freeze.engine.Path.read_text", return_value="cachy.freeze=1"):
            self.assertEqual(self.engine._current_mode(), "unknown")

    def test_status_rejects_invalid_scheduled_boot_state(self) -> None:
        self.runner.mode = "invalid"
        with self.assertRaisesRegex(IntegrityError, "scheduled GRUB mode"):
            self.engine.status()

    def test_status_rejects_exposed_recovery_menu(self) -> None:
        self.runner.recovery = "1"
        with self.assertRaisesRegex(IntegrityError, "single-entry GRUB menu"):
            self.engine.status()


class JournalTests(unittest.TestCase):
    def test_transaction_rejects_malformed_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            journal = OperationJournal(state)
            journal.path.write_text("not-json")
            with self.assertRaisesRegex(IntegrityError, "cannot be read"):
                journal.load()

    def test_audit_is_structured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            AuditLogger(path).write("warning", "test", "message", value=1)
            self.assertEqual(json.loads(path.read_text())["context"], {"value": 1})


if __name__ == "__main__":
    unittest.main()
