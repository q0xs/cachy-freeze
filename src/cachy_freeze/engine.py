"""Fail-closed Btrfs and GRUB orchestration for FROZEN and THAWED modes."""

from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .catalog import AuditLogger, OperationJournal, atomic_json_write
from .config import Config
from .errors import CachyFreezeError, IntegrityError
from .runner import CommandRunner, ProcessLock
from .versioning import APP_VERSION, STATE_SCHEMA_VERSION, StateMigrationManager

_LEGACY_SNAPSHOT_ID = re.compile(r"^snap-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
_FILESYSTEM_UUID = re.compile(
    r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-"
    r"[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$"
)
_LEGACY_TRANSIENTS = (
    "@golden.previous",
    "@golden.previous.pending",
    "@golden.failed",
    "@active.previous",
    "@active.previous.pending",
)


class FreezeEngine:
    def __init__(
        self,
        config: Config,
        *,
        runner: CommandRunner | None = None,
        journal: OperationJournal | None = None,
        logger: AuditLogger | None = None,
    ) -> None:
        self.config = config
        self.runner = runner or CommandRunner()
        self.journal = journal or OperationJournal(Path(config.STATE_DIR))
        self.logger = logger or AuditLogger(Path(config.LOG_FILE))
        self.top = Path(config.TOP_MOUNT)

    @staticmethod
    def require_root() -> None:
        if not hasattr(os, "geteuid") or os.geteuid() != 0:
            raise CachyFreezeError("This operation requires administrator authorization.")

    def _root_source(self) -> str:
        source = self.runner.text(["findmnt", "-n", "-o", "SOURCE", "/"])
        if not source:
            raise CachyFreezeError("The root mount source could not be detected.")
        return source

    def _root_device(self) -> str:
        return self.config.ROOT_DEVICE or self._root_source().split("[", 1)[0]

    def _root_uuid(self) -> str:
        test_override = os.environ.get("CACHY_FREEZE_ROOT_SUBVOLUME")
        if test_override and self.config.ROOT_DEVICE:
            mounted_uuid = self.runner.text(
                ["blkid", "-s", "UUID", "-o", "value", self.config.ROOT_DEVICE]
            )
        else:
            mounted_uuid = self.runner.text(["findmnt", "-n", "-o", "UUID", "/"])
        if not _FILESYSTEM_UUID.fullmatch(mounted_uuid):
            raise CachyFreezeError("The mounted root filesystem UUID is missing or malformed.")
        if self.config.ROOT_DEVICE:
            device_uuid = self.runner.text(
                ["blkid", "-s", "UUID", "-o", "value", self.config.ROOT_DEVICE]
            )
            if not device_uuid or device_uuid.lower() != mounted_uuid.lower():
                raise IntegrityError("Configured root device does not match the running root")
        if self.config.ROOT_UUID and self.config.ROOT_UUID.lower() != mounted_uuid.lower():
            raise IntegrityError("Configured root UUID does not match the running root")
        return mounted_uuid

    def _root_subvolume(self) -> str:
        override = os.environ.get("CACHY_FREEZE_ROOT_SUBVOLUME")
        if override:
            if override not in {self.config.MAINTENANCE_SUBVOL, self.config.ACTIVE_SUBVOL}:
                raise CachyFreezeError("Invalid test root-subvolume override.")
            return override
        source = self._root_source()
        if "[" not in source or not source.endswith("]"):
            raise CachyFreezeError(f"Root Btrfs subvolume was not found: {source}")
        return source.rsplit("[", 1)[1][:-1].lstrip("/")

    def _current_mode(self) -> str:
        try:
            arguments = Path("/proc/cmdline").read_text(encoding="utf-8").split()
        except OSError:
            arguments = []
        marker = "frozen" if "cachy.freeze=1" in arguments else None
        marker = "thawed" if "cachy.freeze=0" in arguments else marker
        try:
            subvolume = self._root_subvolume()
        except CachyFreezeError:
            return "unknown"
        actual = {
            self.config.MAINTENANCE_SUBVOL: "thawed",
            self.config.ACTIVE_SUBVOL: "frozen",
        }.get(subvolume, "unknown")
        if marker is not None and marker != actual:
            return "unknown"
        return marker or actual

    @contextmanager
    def mounted_top(self) -> Iterator[None]:
        if self.top.is_symlink():
            raise IntegrityError("The top-level Btrfs mount path must not be a symlink")
        self.top.mkdir(parents=True, exist_ok=True)
        mounted = self.runner.run(
            ["mountpoint", "-q", str(self.top)], check=False
        ).returncode == 0
        mounted_here = False
        if mounted:
            filesystem = self.runner.text(["findmnt", "-n", "-o", "FSTYPE", str(self.top)])
            mounted_uuid = self.runner.text(["findmnt", "-n", "-o", "UUID", str(self.top)])
            filesystem_root = self.runner.text(
                ["findmnt", "-n", "-o", "FSROOT", str(self.top)]
            )
            if (
                filesystem != "btrfs"
                or mounted_uuid != self._root_uuid()
                or filesystem_root != "/"
            ):
                raise CachyFreezeError(f"An unexpected filesystem is mounted at {self.top}.")
        else:
            self.runner.run(
                [
                    "mount",
                    "-t",
                    "btrfs",
                    "-o",
                    "rw,subvolid=5",
                    self._root_device(),
                    str(self.top),
                ]
            )
            mounted_here = True
        try:
            filesystem = self.runner.text(["findmnt", "-n", "-o", "FSTYPE", str(self.top)])
            mounted_uuid = self.runner.text(["findmnt", "-n", "-o", "UUID", str(self.top)])
            filesystem_root = self.runner.text(
                ["findmnt", "-n", "-o", "FSROOT", str(self.top)]
            )
            if (
                filesystem != "btrfs"
                or mounted_uuid != self._root_uuid()
                or filesystem_root != "/"
            ):
                raise CachyFreezeError(f"An unexpected filesystem is mounted at {self.top}.")
            yield
        finally:
            if mounted_here:
                self.runner.run(["umount", str(self.top)], check=False)

    def _managed_path(self, name: str) -> Path:
        if name not in self.config.managed_subvolumes:
            raise IntegrityError(f"Refusing unmanaged Btrfs target: {name}")
        path = self.top / name
        if path.parent != self.top or path.name != name or path.is_symlink():
            raise IntegrityError(f"Unsafe Btrfs target: {name}")
        return path

    def _subvolume_exists(self, name: str) -> bool:
        path = self._managed_path(name)
        return self.runner.run(
            ["btrfs", "subvolume", "show", str(path)], check=False
        ).returncode == 0

    def _delete_subvolume(self, name: str) -> None:
        path = self._managed_path(name)
        if self._subvolume_exists(name):
            self.runner.run(["btrfs", "subvolume", "delete", "--commit-after", str(path)])

    def _is_read_only(self, name: str) -> bool:
        output = self.runner.text(
            ["btrfs", "property", "get", "-ts", str(self._managed_path(name)), "ro"]
        )
        return output == "ro=true"

    def _validate_golden(self, name: str) -> None:
        path = self._managed_path(name)
        if not self._subvolume_exists(name):
            raise IntegrityError(f"Golden candidate is missing: {name}")
        if not self._is_read_only(name):
            raise IntegrityError(f"Golden candidate is not read-only: {name}")
        for relative in ("boot/vmlinuz-linux-cachyos", "boot/initramfs-linux-cachyos.img"):
            if not (path / relative).is_file():
                raise IntegrityError(f"Golden candidate is missing required boot file: {relative}")

    def _validate_active(self, name: str) -> None:
        if not self._subvolume_exists(name):
            raise IntegrityError(f"Disposable runtime is missing: {name}")
        if self._is_read_only(name):
            raise IntegrityError(f"Disposable runtime is unexpectedly read-only: {name}")

    def _replace_with_candidate(self, current: str, candidate: str, pending: str) -> None:
        if not self._subvolume_exists(candidate):
            raise IntegrityError(f"Transaction candidate is missing: {candidate}")
        if self._subvolume_exists(pending):
            raise IntegrityError(f"Transaction pending target already exists: {pending}")
        if self._subvolume_exists(current):
            os.replace(self._managed_path(current), self._managed_path(pending))
        os.replace(self._managed_path(candidate), self._managed_path(current))
        self.runner.run(["sync"])

    def _rollback_pair(self, current: str, candidate: str, pending: str) -> None:
        if self._subvolume_exists(pending):
            self._delete_subvolume(current)
            os.replace(self._managed_path(pending), self._managed_path(current))
        self._delete_subvolume(candidate)

    def _cleanup_transaction_subvolumes(self) -> None:
        for name in (
            self.config.GOLDEN_NEXT_SUBVOL,
            self.config.ACTIVE_NEXT_SUBVOL,
            self.config.GOLDEN_PENDING_SUBVOL,
            self.config.ACTIVE_PENDING_SUBVOL,
        ):
            self._delete_subvolume(name)

    def _recover_transaction_locked(self) -> None:
        transaction = self.journal.load()
        if transaction is None:
            unexpected = [
                name
                for name in (
                    self.config.GOLDEN_NEXT_SUBVOL,
                    self.config.GOLDEN_PENDING_SUBVOL,
                    self.config.ACTIVE_NEXT_SUBVOL,
                    self.config.ACTIVE_PENDING_SUBVOL,
                )
                if self._subvolume_exists(name)
            ]
            if unexpected:
                raise IntegrityError(
                    "Unowned transaction subvolumes require manual review: "
                    + ", ".join(unexpected)
                )
            return

        phase = str(transaction["phase"])
        self.logger.write(
            "WARNING",
            "transaction.recover",
            "Reconciling an interrupted baseline transaction",
            phase=phase,
            baseline_id=transaction["baseline_id"],
        )
        if phase == "boot-committed":
            self._validate_golden(self.config.GOLDEN_SUBVOL)
            self._validate_active(self.config.ACTIVE_SUBVOL)
            self._cleanup_transaction_subvolumes()
        else:
            self._rollback_pair(
                self.config.GOLDEN_SUBVOL,
                self.config.GOLDEN_NEXT_SUBVOL,
                self.config.GOLDEN_PENDING_SUBVOL,
            )
            self._rollback_pair(
                self.config.ACTIVE_SUBVOL,
                self.config.ACTIVE_NEXT_SUBVOL,
                self.config.ACTIVE_PENDING_SUBVOL,
            )
            # A crash can occur after grub-editenv succeeds but before the
            # durable commit phase is recorded. A rolled-back publication must
            # remain THAWED rather than booting the predecessor unexpectedly.
            self._set_boot_mode_locked("thawed")
        self.journal.finish()
        self.runner.run(["sync"])

    def _grub_environment(self) -> tuple[Path, dict[str, str]]:
        grub_env = self._managed_path(self.config.MAINTENANCE_SUBVOL) / "boot/grub/grubenv"
        if not grub_env.is_file():
            raise CachyFreezeError("Canonical maintenance GRUB environment was not found.")
        environment: dict[str, str] = {}
        for line in self.runner.text(["grub-editenv", str(grub_env), "list"]).splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                environment[key] = value
        return grub_env, environment

    def _set_boot_mode_locked(self, mode: str) -> None:
        if mode not in {"frozen", "thawed"}:
            raise CachyFreezeError(f"Invalid boot mode: {mode}")
        maintenance = self._managed_path(self.config.MAINTENANCE_SUBVOL)
        grub_cfg = maintenance / "boot/grub/grub.cfg"
        if not grub_cfg.is_file():
            raise CachyFreezeError("Canonical maintenance GRUB configuration was not found.")
        if "--id 'cachyos-current'" not in grub_cfg.read_text(
            encoding="utf-8", errors="replace"
        ):
            raise IntegrityError("The managed CachyFreeze GRUB entry was not found")
        grub_env, _environment = self._grub_environment()
        assignments = [f"cachy_mode={mode}", "saved_entry=cachyos-current"]
        self.runner.run(["grub-editenv", str(grub_env), "set", *assignments])
        _path, environment = self._grub_environment()
        if environment.get("cachy_mode") != mode or environment.get("saved_entry") != (
            "cachyos-current"
        ):
            raise IntegrityError("GRUB boot mode could not be verified after writing")

    def preflight(self) -> dict[str, Any]:
        self.require_root()
        filesystem = self.runner.text(["findmnt", "-n", "-o", "FSTYPE", "/"])
        if filesystem != "btrfs":
            raise CachyFreezeError("The root filesystem is not Btrfs.")
        if not Path("/sys/firmware/efi").is_dir():
            raise CachyFreezeError("The system was not booted in UEFI mode.")
        os_release = Path("/etc/os-release").read_text(encoding="utf-8", errors="replace")
        if not re.search(r"^(ID|ID_LIKE)=.*\b(arch|cachyos)\b", os_release, re.MULTILINE):
            raise CachyFreezeError("Only CachyOS/Arch Linux is supported.")
        for command in ("btrfs", "grub-editenv", "grub-mkconfig", "mkinitcpio"):
            if shutil.which(command) is None:
                raise CachyFreezeError(f"Required command was not found: {command}")
        if not Path("/boot/grub").is_dir() or not Path("/boot/efi/EFI").is_dir():
            raise CachyFreezeError("The supported GRUB and /boot/efi layout was not found.")
        if self.runner.text(["findmnt", "-n", "-o", "TARGET", "--target", "/boot"]) != "/":
            raise CachyFreezeError("A separate /boot filesystem is not supported.")
        if self.runner.text(
            ["findmnt", "-n", "-o", "TARGET", "--target", "/boot/efi"]
        ) != "/boot/efi" or self.runner.text(
            ["findmnt", "-n", "-o", "FSTYPE", "--target", "/boot/efi"]
        ) != "vfat":
            raise CachyFreezeError("The EFI System Partition is not mounted as vfat at /boot/efi.")
        current = self._root_subvolume()
        if current not in {self.config.MAINTENANCE_SUBVOL, self.config.ACTIVE_SUBVOL}:
            raise CachyFreezeError(f"Unexpected root subvolume: {current}")
        for image in ("/boot/vmlinuz-linux-cachyos", "/boot/initramfs-linux-cachyos.img"):
            if not Path(image).is_file():
                raise CachyFreezeError(f"Required boot image was not found: {image}")
        with self.mounted_top():
            if not self._subvolume_exists(self.config.MAINTENANCE_SUBVOL):
                raise CachyFreezeError("The persistent maintenance subvolume was not found.")
            nested = self.runner.text(
                [
                    "btrfs",
                    "subvolume",
                    "list",
                    "-o",
                    str(self._managed_path(self.config.MAINTENANCE_SUBVOL)),
                ]
            )
            nested_count = len([line for line in nested.splitlines() if line.strip()])
            if nested_count:
                raise CachyFreezeError(
                    "Nested subvolumes inside @ are unsupported because their data would not reset."
                )
        result = {
            "current_subvolume": current,
            "firmware": "UEFI",
            "filesystem": filesystem,
            "nested_subvolume_count": 0,
        }
        self.logger.write("INFO", "preflight", "Compatibility validation passed", **result)
        return result

    def status(self) -> dict[str, Any]:
        self.require_root()
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            self._recover_transaction_locked()
            _path, environment = self._grub_environment()
            scheduled_mode = environment.get("cachy_mode")
            if scheduled_mode not in {"frozen", "thawed"}:
                raise IntegrityError("The scheduled GRUB mode is missing or invalid")
            if environment.get("saved_entry") != "cachyos-current":
                raise IntegrityError("The managed CachyFreeze GRUB entry is not scheduled")
            running_mode = self._current_mode()
            if running_mode not in {"frozen", "thawed"}:
                raise IntegrityError("The running boot mode cannot be verified")
            golden_present = self._subvolume_exists(self.config.GOLDEN_SUBVOL)
            active_present = self._subvolume_exists(self.config.ACTIVE_SUBVOL)
            golden_valid = False
            if golden_present:
                try:
                    self._validate_golden(self.config.GOLDEN_SUBVOL)
                    golden_valid = True
                except IntegrityError:
                    golden_valid = False
            return {
                "schema": 3,
                "application_version": APP_VERSION,
                "state_schema": STATE_SCHEMA_VERSION,
                "running_mode": running_mode,
                "scheduled_mode": scheduled_mode,
                "current_subvolume": self._root_subvolume(),
                "golden_present": golden_present,
                "golden_valid": golden_valid,
                "active_present": active_present,
                "transaction_pending": self.journal.load() is not None,
                "reboot_required": scheduled_mode != running_mode,
            }

    def freeze(self) -> dict[str, Any]:
        self.require_root()
        if self._current_mode() != "thawed" or self._root_subvolume() != (
            self.config.MAINTENANCE_SUBVOL
        ):
            raise CachyFreezeError("FREEZE is allowed only from verified THAWED mode.")
        baseline_id = uuid.uuid4().hex
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            self._recover_transaction_locked()
            source = self._managed_path(self.config.MAINTENANCE_SUBVOL)
            if not self._subvolume_exists(self.config.MAINTENANCE_SUBVOL):
                raise IntegrityError("The THAWED source subvolume is missing")
            if self._is_read_only(self.config.MAINTENANCE_SUBVOL):
                raise IntegrityError("The THAWED source subvolume is read-only")
            self.journal.begin(
                baseline_id=baseline_id,
                source_subvolume=self.config.MAINTENANCE_SUBVOL,
            )
            try:
                self.runner.run(["sync"])
                self.runner.run(
                    [
                        "btrfs",
                        "subvolume",
                        "snapshot",
                        "-r",
                        str(source),
                        str(self._managed_path(self.config.GOLDEN_NEXT_SUBVOL)),
                    ]
                )
                self._validate_golden(self.config.GOLDEN_NEXT_SUBVOL)
                self.runner.run(
                    [
                        "btrfs",
                        "subvolume",
                        "snapshot",
                        str(self._managed_path(self.config.GOLDEN_NEXT_SUBVOL)),
                        str(self._managed_path(self.config.ACTIVE_NEXT_SUBVOL)),
                    ]
                )
                self._validate_active(self.config.ACTIVE_NEXT_SUBVOL)
                self.journal.set_phase("prepared")
                self._replace_with_candidate(
                    self.config.GOLDEN_SUBVOL,
                    self.config.GOLDEN_NEXT_SUBVOL,
                    self.config.GOLDEN_PENDING_SUBVOL,
                )
                self._validate_golden(self.config.GOLDEN_SUBVOL)
                self.journal.set_phase("golden-committed")
                self._replace_with_candidate(
                    self.config.ACTIVE_SUBVOL,
                    self.config.ACTIVE_NEXT_SUBVOL,
                    self.config.ACTIVE_PENDING_SUBVOL,
                )
                self._validate_active(self.config.ACTIVE_SUBVOL)
                self.journal.set_phase("active-committed")
                self._set_boot_mode_locked("frozen")
                self.journal.set_phase("boot-committed")
                self._cleanup_transaction_subvolumes()
                self.journal.finish()
                self.runner.run(["sync"])
            except Exception:
                self.logger.write(
                    "ERROR",
                    "freeze.failed",
                    "Baseline update failed; recovery metadata was retained",
                    baseline_id=baseline_id,
                )
                raise
        result = {"mode": "frozen", "baseline_id": baseline_id, "reboot_required": True}
        self.logger.write("INFO", "freeze", "Golden replaced and FROZEN scheduled", **result)
        return result

    def thaw(self) -> dict[str, Any]:
        self.require_root()
        if self._current_mode() != "frozen" or self._root_subvolume() != self.config.ACTIVE_SUBVOL:
            raise CachyFreezeError("THAW is allowed only from verified FROZEN mode.")
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            self._recover_transaction_locked()
            if not self._subvolume_exists(self.config.MAINTENANCE_SUBVOL):
                raise IntegrityError("The persistent THAWED environment is missing")
            self._set_boot_mode_locked("thawed")
        result = {"mode": "thawed", "reboot_required": True}
        self.logger.write("INFO", "thaw", "THAWED scheduled without runtime promotion")
        return result

    def mark_boot_successful(self) -> dict[str, Any]:
        self.require_root()
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            self._recover_transaction_locked()
            mode = self._current_mode()
            if mode == "frozen":
                self._validate_golden(self.config.GOLDEN_SUBVOL)
                self._validate_active(self.config.ACTIVE_SUBVOL)
            elif mode == "thawed":
                self._delete_subvolume(self.config.ACTIVE_SUBVOL)
                self._delete_subvolume(self.config.ACTIVE_NEXT_SUBVOL)
                self._delete_subvolume(self.config.ACTIVE_PENDING_SUBVOL)
            else:
                raise IntegrityError("The running boot mode cannot be verified")
        result = {"mode": mode, "verified_at": datetime.now(UTC).isoformat()}
        atomic_json_write(Path(self.config.STATE_DIR) / "boot-success.json", result, mode=0o600)
        self.logger.write("INFO", "boot.success", "Boot state verified", mode=mode)
        return result

    def _delete_legacy_history_locked(self) -> list[str]:
        parent_name = self.config.LEGACY_SNAPSHOT_SUBVOL
        catalog_path = Path(self.config.STATE_DIR) / "snapshots.json"
        migration_path = Path(self.config.STATE_DIR) / "history-migration.json"
        parent_exists = self._subvolume_exists(parent_name)
        if not parent_exists and not migration_path.exists() and not catalog_path.exists():
            return []
        if not catalog_path.is_file():
            raise IntegrityError(
                "Legacy snapshot ownership cannot be proven because snapshots.json is missing"
            )
        try:
            document = json.loads(catalog_path.read_text(encoding="utf-8"))
            items = document["snapshots"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise IntegrityError(
                f"Legacy snapshot ownership metadata is invalid: {error}"
            ) from error
        if document.get("schema") != 1 or not isinstance(items, list):
            raise IntegrityError("Legacy snapshot ownership metadata has an unsupported schema")
        expected: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                raise IntegrityError("Legacy snapshot ownership metadata is malformed")
            snapshot_id = str(item.get("snapshot_id", ""))
            if not _LEGACY_SNAPSHOT_ID.fullmatch(snapshot_id):
                raise IntegrityError("Legacy snapshot identity is malformed")
            if item.get("subvolume") != f"{parent_name}/{snapshot_id}":
                raise IntegrityError("Legacy snapshot path does not match its owned parent")
            expected.add(snapshot_id)
        remaining = set(expected)
        resuming = migration_path.exists()
        if resuming:
            try:
                migration = json.loads(migration_path.read_text(encoding="utf-8"))
                owned = set(migration["owned_snapshots"])
                remaining = set(migration["remaining_snapshots"])
            except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
                raise IntegrityError(
                    f"Legacy history migration state is invalid: {error}"
                ) from error
            if migration.get("schema") != 1 or owned != expected or not remaining <= expected:
                raise IntegrityError(
                    "Legacy history migration ownership does not match the catalog"
                )
        if not parent_exists:
            if resuming and remaining:
                raise IntegrityError("Legacy snapshot parent disappeared during migration")
            catalog_path.unlink()
            migration_path.unlink(missing_ok=True)
            return sorted(expected)

        parent = self._managed_path(parent_name)
        actual = {child.name for child in parent.iterdir()}
        if (not resuming and actual != expected) or (resuming and not actual <= remaining):
            raise IntegrityError("Legacy snapshot contents do not match the owned catalog")
        if not resuming:
            atomic_json_write(
                migration_path,
                {
                    "schema": 1,
                    "owned_snapshots": sorted(expected),
                    "remaining_snapshots": sorted(expected),
                },
                mode=0o600,
            )
        # A crash can occur after a subvolume delete commits but before the
        # remaining-set update. Missing owned children are therefore treated as
        # completed work only when the durable migration record exists.
        remaining = actual
        for snapshot_id in sorted(actual):
            child = parent / snapshot_id
            if child.parent != parent or child.is_symlink():
                raise IntegrityError("Legacy snapshot path failed validation")
            if self.runner.run(
                ["btrfs", "subvolume", "show", str(child)], check=False
            ).returncode != 0:
                raise IntegrityError("Legacy catalog entry is not a Btrfs subvolume")
            self.runner.run(["btrfs", "subvolume", "delete", "--commit-after", str(child)])
            remaining.remove(snapshot_id)
            atomic_json_write(
                migration_path,
                {
                    "schema": 1,
                    "owned_snapshots": sorted(expected),
                    "remaining_snapshots": sorted(remaining),
                },
                mode=0o600,
            )
        self._delete_subvolume(parent_name)
        catalog_path.unlink()
        migration_path.unlink()
        return sorted(expected)

    def migrate_state(self) -> dict[str, Any]:
        self.require_root()
        state_manager = StateMigrationManager(Path(self.config.STATE_DIR), self.logger)
        state_manager.status()
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            self._recover_transaction_locked()
            removed_snapshots = self._delete_legacy_history_locked()
            state_marker = Path(self.config.STATE_DIR) / "schema-version.json"
            old_transients: list[str] = []
            if state_marker.exists():
                for name in _LEGACY_TRANSIENTS:
                    path = self.top / name
                    if path.parent != self.top or path.is_symlink():
                        raise IntegrityError("Legacy transaction target failed validation")
                    if self.runner.run(
                        ["btrfs", "subvolume", "show", str(path)], check=False
                    ).returncode == 0:
                        self.runner.run(
                            ["btrfs", "subvolume", "delete", "--commit-after", str(path)]
                        )
                        old_transients.append(name)
            state = state_manager.migrate()
            for obsolete in (
                "settings.json",
                "boot-attempts",
                "boot-health.json",
                "boot-validation.json",
                "power-policy.json",
                "last-auto-snapshot",
            ):
                (Path(self.config.STATE_DIR) / obsolete).unlink(missing_ok=True)
        result = {
            **state,
            "removed_legacy_snapshots": removed_snapshots,
            "removed_legacy_transients": old_transients,
        }
        self.logger.write("INFO", "state.migrate", "Simplified state migration completed")
        return result

    def version_info(self) -> dict[str, Any]:
        state = StateMigrationManager(Path(self.config.STATE_DIR), self.logger).status()
        return {"application_version": APP_VERSION, "state": state}

    def request_reboot(self) -> dict[str, bool]:
        self.require_root()
        self.logger.write("INFO", "system.reboot", "Explicit reboot requested")
        self.runner.run(["systemctl", "reboot", "--no-block"])
        return {"reboot_queued": True}

    def write_status_cache(self, status: dict[str, Any]) -> None:
        atomic_json_write(Path(self.config.STATE_DIR) / "status.json", status, mode=0o644)
