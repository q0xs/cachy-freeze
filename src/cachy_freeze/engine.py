"""Btrfs, GRUB, snapshot, and recovery orchestration.

All mutating operations are serialized. Commands are passed as argument arrays,
never through a shell, and every multi-step rotation leaves enough state for a
forward recovery after an interrupted rename.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .catalog import AuditLogger, SnapshotCatalog, atomic_json_write, atomic_text_write
from .config import Config
from .errors import CachyFreezeError, CommandError, IntegrityError
from .models import SnapshotMetadata
from .runner import CommandRunner, ProcessLock
from .settings import SettingsStore

try:
    import pwd
except ImportError:  # pragma: no cover - Windows-only test compatibility
    pwd = None  # type: ignore[assignment]


_SNAPSHOT_ID_RE = re.compile(r"^snap-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")


class FreezeEngine:
    def __init__(
        self,
        config: Config,
        *,
        runner: CommandRunner | None = None,
        catalog: SnapshotCatalog | None = None,
        logger: AuditLogger | None = None,
    ) -> None:
        self.config = config
        self.runner = runner or CommandRunner()
        self.catalog = catalog or SnapshotCatalog(Path(config.STATE_DIR))
        self.logger = logger or AuditLogger(Path(config.LOG_FILE))
        self.top = Path(config.TOP_MOUNT)

    @staticmethod
    def require_root() -> None:
        if not hasattr(os, "geteuid") or os.geteuid() != 0:
            raise CachyFreezeError("This operation requires root privileges.")

    def _root_source(self) -> str:
        source = self.runner.text(["findmnt", "-n", "-o", "SOURCE", "/"])
        if not source:
            raise CachyFreezeError("The root mount source could not be detected.")
        return source

    def _root_device(self) -> str:
        if self.config.ROOT_DEVICE:
            return self.config.ROOT_DEVICE
        return self._root_source().split("[", 1)[0]

    def _root_uuid(self) -> str:
        if self.config.ROOT_DEVICE:
            value = self.runner.text(
                ["blkid", "-s", "UUID", "-o", "value", self.config.ROOT_DEVICE]
            )
            if value:
                return value
        value = self.runner.text(["findmnt", "-n", "-o", "UUID", "/"])
        if not value:
            raise CachyFreezeError("The root filesystem UUID could not be detected.")
        return value

    def _root_subvolume(self) -> str:
        if override := os.environ.get("CACHY_FREEZE_ROOT_SUBVOLUME"):
            if override not in {
                self.config.MAINTENANCE_SUBVOL,
                self.config.ACTIVE_SUBVOL,
            }:
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
            return "unknown"
        if "cachy.freeze=1" in arguments:
            return "frozen"
        if "cachy.freeze=0" in arguments:
            return "thawed"
        return "unknown"

    @contextmanager
    def mounted_top(self) -> Iterator[None]:
        self.top.mkdir(parents=True, exist_ok=True)
        mounted = self.runner.run(["mountpoint", "-q", str(self.top)], check=False).returncode == 0
        mounted_here = False
        if mounted:
            mounted_uuid = self.runner.text(["findmnt", "-n", "-o", "UUID", str(self.top)])
            if mounted_uuid != self._root_uuid():
                raise CachyFreezeError(f"A different filesystem is mounted at {self.top}.")
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
            yield
        finally:
            if mounted_here:
                self.runner.run(["umount", str(self.top)], check=False)

    def _subvolume_path(self, name: str) -> Path:
        return self.top / name

    def _subvolume_exists(self, name_or_path: str | Path) -> bool:
        path = (
            name_or_path if isinstance(name_or_path, Path) else self._subvolume_path(name_or_path)
        )
        return (
            self.runner.run(["btrfs", "subvolume", "show", str(path)], check=False).returncode == 0
        )

    def _delete_subvolume(self, name_or_path: str | Path) -> None:
        path = (
            name_or_path if isinstance(name_or_path, Path) else self._subvolume_path(name_or_path)
        )
        if self._subvolume_exists(path):
            # Commit the directory removal before returning, so a crash cannot
            # resurrect the subvolume name.  Full block reclamation remains an
            # asynchronous Btrfs job; waiting for ``subvolume sync`` here made
            # retention cleanup stall for many seconds per snapshot.
            self.runner.run(["btrfs", "subvolume", "delete", "--commit-after", str(path)])

    def _subvolume_details(self, path: Path) -> dict[str, str]:
        output = self.runner.text(["btrfs", "subvolume", "show", str(path)])
        details: dict[str, str] = {}
        for raw_line in output.splitlines():
            if ":" not in raw_line:
                continue
            key, value = raw_line.strip().split(":", 1)
            details[key.strip().lower().replace(" ", "_")] = value.strip()
        if not details.get("uuid"):
            raise IntegrityError(f"Btrfs UUID could not be read for {path}")
        return details

    def _subvolume_sizes(self, path: Path) -> tuple[int, int]:
        output = self.runner.text(["btrfs", "filesystem", "du", "-s", "--raw", str(path)])
        for raw_line in reversed(output.splitlines()):
            fields = raw_line.split()
            if len(fields) >= 3 and fields[0].isdigit() and fields[1].isdigit():
                return int(fields[0]), int(fields[1])
        raise IntegrityError(f"Btrfs size information could not be read for {path}")

    def _is_read_only(self, path: Path) -> bool:
        output = self.runner.text(["btrfs", "property", "get", "-ts", str(path), "ro"])
        return output == "ro=true"

    def _ensure_snapshot_parent(self) -> Path:
        parent = self._subvolume_path(self.config.SNAPSHOT_SUBVOL)
        if not self._subvolume_exists(parent):
            self.runner.run(["btrfs", "subvolume", "create", str(parent)])
        return parent

    @staticmethod
    def _creator() -> str:
        if pwd is not None and (uid := os.environ.get("PKEXEC_UID")):
            try:
                return pwd.getpwuid(int(uid)).pw_name
            except (KeyError, ValueError):
                pass
        return os.environ.get("SUDO_USER") or os.environ.get("USER") or "root"

    def _create_snapshot_locked(
        self,
        source: Path,
        description: str,
        *,
        frozen: bool,
    ) -> SnapshotMetadata:
        description = " ".join(description.split())
        if not description or len(description) > 512:
            raise CachyFreezeError("Snapshot description must contain 1-512 characters.")
        parent = self._ensure_snapshot_parent()
        snapshot_id = f"snap-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        temporary = parent / f".{snapshot_id}.next"
        destination = parent / snapshot_id
        started = time.monotonic()
        self._delete_subvolume(temporary)
        try:
            self.runner.run(["btrfs", "subvolume", "snapshot", "-r", str(source), str(temporary)])
            if not self._is_read_only(temporary):
                raise IntegrityError("Created snapshot is not read-only")
            os.replace(temporary, destination)
            self.runner.run(["sync"])
            details = self._subvolume_details(destination)
            apparent, exclusive = self._subvolume_sizes(destination)
            relative = f"{self.config.SNAPSHOT_SUBVOL}/{snapshot_id}"
            metadata = SnapshotMetadata.create(
                snapshot_id=snapshot_id,
                subvolume=relative,
                btrfs_uuid=details["uuid"],
                parent_uuid=details.get("parent_uuid", "-"),
                created_at=datetime.now(UTC).isoformat(),
                kernel=platform.release(),
                apparent_size_bytes=apparent,
                exclusive_size_bytes=exclusive,
                description=description,
                created_by=self._creator(),
                frozen=frozen,
                bootable=(destination / "boot" / "vmlinuz-linux-cachyos").is_file(),
                creation_duration_ms=round((time.monotonic() - started) * 1000),
                source_subvolume=source.name,
            )
            self.catalog.add(metadata)
        except Exception:
            self._delete_subvolume(temporary)
            self._delete_subvolume(destination)
            raise
        self.logger.write(
            "INFO",
            "snapshot.create",
            "Snapshot created",
            snapshot_id=snapshot_id,
            btrfs_uuid=metadata.btrfs_uuid,
            source=source.name,
        )
        return metadata

    def _restore_pair(
        self,
        current: str,
        candidate: str,
        previous: str,
        pending: str,
        *,
        require_current: bool = True,
    ) -> None:
        current_path = self._subvolume_path(current)
        candidate_path = self._subvolume_path(candidate)
        previous_path = self._subvolume_path(previous)
        pending_path = self._subvolume_path(pending)

        has_current = self._subvolume_exists(current_path)
        has_candidate = self._subvolume_exists(candidate_path)
        has_pending = self._subvolume_exists(pending_path)
        if not has_current and has_candidate:
            os.replace(candidate_path, current_path)
            has_current = True
            has_candidate = False
        if not has_current and has_pending:
            os.replace(pending_path, current_path)
            has_current = True
            has_pending = False
        if has_current and has_pending:
            self._delete_subvolume(previous_path)
            os.replace(pending_path, previous_path)
            has_pending = False
        if has_current and has_candidate:
            self._delete_subvolume(candidate_path)
        if require_current and not has_current:
            raise IntegrityError(f"Recovery could not restore subvolume {current}")
        if has_pending:
            raise IntegrityError(f"Recovery could not finalize subvolume {pending}")

    def _commit_pair(self, current: str, candidate: str, previous: str, pending: str) -> None:
        current_path = self._subvolume_path(current)
        candidate_path = self._subvolume_path(candidate)
        previous_path = self._subvolume_path(previous)
        pending_path = self._subvolume_path(pending)
        if not self._subvolume_exists(candidate_path):
            raise IntegrityError(f"Transaction candidate is missing: {candidate}")
        if self._subvolume_exists(pending_path):
            self._restore_pair(current, candidate, previous, pending)
            return
        if self._subvolume_exists(current_path):
            os.replace(current_path, pending_path)
        os.replace(candidate_path, current_path)
        self._delete_subvolume(previous_path)
        if self._subvolume_exists(pending_path):
            os.replace(pending_path, previous_path)
        self.runner.run(["sync"])

    def _recover_transaction_locked(self) -> None:
        transaction = self.catalog.transaction()
        if transaction is None:
            return
        if transaction["kind"] not in {"publish", "rollback"}:
            raise IntegrityError(f"Unsupported interrupted transaction: {transaction['kind']}")
        phase = str(transaction.get("phase", ""))
        self.logger.write(
            "WARNING",
            "transaction.recover",
            "Recovering an interrupted snapshot operation",
            kind=transaction["kind"],
            phase=phase,
        )
        if phase == "preparing":
            self._delete_subvolume(self.config.GOLDEN_NEXT_SUBVOL)
            self._delete_subvolume(self.config.NEXT_SUBVOL)
            self._restore_pair(
                self.config.GOLDEN_SUBVOL,
                self.config.GOLDEN_NEXT_SUBVOL,
                self.config.GOLDEN_PREVIOUS_SUBVOL,
                self.config.GOLDEN_PENDING_SUBVOL,
                require_current=False,
            )
            self._restore_pair(
                self.config.ACTIVE_SUBVOL,
                self.config.NEXT_SUBVOL,
                self.config.PREVIOUS_SUBVOL,
                self.config.ACTIVE_PENDING_SUBVOL,
                require_current=False,
            )
            self.catalog.finish_transaction()
            return

        if phase == "prepared":
            self._commit_pair(
                self.config.GOLDEN_SUBVOL,
                self.config.GOLDEN_NEXT_SUBVOL,
                self.config.GOLDEN_PREVIOUS_SUBVOL,
                self.config.GOLDEN_PENDING_SUBVOL,
            )
            self.catalog.set_transaction_phase("golden-committed")
            phase = "golden-committed"
        else:
            self._restore_pair(
                self.config.GOLDEN_SUBVOL,
                self.config.GOLDEN_NEXT_SUBVOL,
                self.config.GOLDEN_PREVIOUS_SUBVOL,
                self.config.GOLDEN_PENDING_SUBVOL,
            )

        if phase == "golden-committed":
            if not self._subvolume_exists(self.config.NEXT_SUBVOL):
                self.runner.run(
                    [
                        "btrfs",
                        "subvolume",
                        "snapshot",
                        str(self._subvolume_path(self.config.GOLDEN_SUBVOL)),
                        str(self._subvolume_path(self.config.NEXT_SUBVOL)),
                    ]
                )
            self._commit_pair(
                self.config.ACTIVE_SUBVOL,
                self.config.NEXT_SUBVOL,
                self.config.PREVIOUS_SUBVOL,
                self.config.ACTIVE_PENDING_SUBVOL,
            )
            self.catalog.set_transaction_phase("active-committed")
        else:
            self._restore_pair(
                self.config.ACTIVE_SUBVOL,
                self.config.NEXT_SUBVOL,
                self.config.PREVIOUS_SUBVOL,
                self.config.ACTIVE_PENDING_SUBVOL,
            )
        self.catalog.finish_transaction()
        self.logger.write(
            "INFO",
            "transaction.recover",
            "Interrupted snapshot operation completed successfully",
            kind=transaction["kind"],
        )

    def _publish_source_locked(self, source: Path, kind: str, snapshot_id: str) -> None:
        golden_candidate = self._subvolume_path(self.config.GOLDEN_NEXT_SUBVOL)
        active_candidate = self._subvolume_path(self.config.NEXT_SUBVOL)
        self.catalog.begin_transaction(
            kind,
            "preparing",
            {"source": str(source), "snapshot_id": snapshot_id},
        )
        try:
            self._delete_subvolume(golden_candidate)
            self._delete_subvolume(active_candidate)
            self.runner.run(
                [
                    "btrfs",
                    "subvolume",
                    "snapshot",
                    "-r",
                    str(source),
                    str(golden_candidate),
                ]
            )
            if not self._is_read_only(golden_candidate):
                raise IntegrityError("Golden candidate is not read-only")
            self.runner.run(
                [
                    "btrfs",
                    "subvolume",
                    "snapshot",
                    str(golden_candidate),
                    str(active_candidate),
                ]
            )
            self.runner.run(["sync"])
            self.catalog.set_transaction_phase("prepared")
            self._commit_pair(
                self.config.GOLDEN_SUBVOL,
                self.config.GOLDEN_NEXT_SUBVOL,
                self.config.GOLDEN_PREVIOUS_SUBVOL,
                self.config.GOLDEN_PENDING_SUBVOL,
            )
            self.catalog.set_transaction_phase("golden-committed")
            self._commit_pair(
                self.config.ACTIVE_SUBVOL,
                self.config.NEXT_SUBVOL,
                self.config.PREVIOUS_SUBVOL,
                self.config.ACTIVE_PENDING_SUBVOL,
            )
            self.catalog.set_transaction_phase("active-committed")
            self.catalog.finish_transaction()
        except Exception:
            self.logger.write(
                "ERROR",
                f"{kind}.failed",
                "Snapshot rotation failed; the recovery journal was retained",
                snapshot_id=snapshot_id,
            )
            raise

    def preflight(self) -> dict[str, Any]:
        self.require_root()
        filesystem = self.runner.text(["findmnt", "-n", "-o", "FSTYPE", "/"])
        if filesystem != "btrfs":
            raise CachyFreezeError("The root filesystem is not Btrfs.")
        if not Path("/sys/firmware/efi").is_dir():
            raise CachyFreezeError("The system was not booted in UEFI mode.")
        for command in ("btrfs", "grub-editenv", "grub-mkconfig", "mkinitcpio"):
            if shutil.which(command) is None:
                raise CachyFreezeError(f"Required command was not found: {command}")
        if not Path("/boot/grub").is_dir():
            raise CachyFreezeError("/boot/grub was not found.")
        if not Path("/boot/efi/EFI").is_dir():
            raise CachyFreezeError("The EFI system partition is not mounted at /boot/efi.")
        boot_target = self.runner.text(["findmnt", "-n", "-o", "TARGET", "--target", "/boot"])
        if boot_target != "/":
            raise CachyFreezeError(
                "/boot is a separate filesystem; the supported layout keeps /boot in "
                "the Btrfs root and mounts EFI at /boot/efi."
            )
        for image in (
            Path("/boot/vmlinuz-linux-cachyos"),
            Path("/boot/initramfs-linux-cachyos.img"),
        ):
            if not image.is_file():
                raise CachyFreezeError(f"Required boot image was not found: {image}")
        current = self._root_subvolume()
        if current not in {
            self.config.MAINTENANCE_SUBVOL,
            self.config.ACTIVE_SUBVOL,
        }:
            raise CachyFreezeError(f"Unexpected root subvolume: {current}")
        with self.mounted_top():
            if not self._subvolume_exists(self.config.MAINTENANCE_SUBVOL):
                raise CachyFreezeError(
                    f"Maintenance subvolume was not found: {self.config.MAINTENANCE_SUBVOL}"
                )
            nested_output = self.runner.text(
                [
                    "btrfs",
                    "subvolume",
                    "list",
                    "-o",
                    str(self._subvolume_path(self.config.MAINTENANCE_SUBVOL)),
                ]
            )
        result = {
            "root_device": self._root_device(),
            "root_uuid": self._root_uuid(),
            "current_subvolume": current,
            "nested_subvolume_count": len(
                [line for line in nested_output.splitlines() if line.strip()]
            ),
            "firmware": "UEFI",
            "filesystem": filesystem,
        }
        self.logger.write("INFO", "preflight", "Preflight passed", **result)
        return result

    def status(self) -> dict[str, Any]:
        self.require_root()
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            self._recover_transaction_locked()
            grub_environment: dict[str, str] = {}
            grub_env = self._subvolume_path(self.config.MAINTENANCE_SUBVOL) / "boot/grub/grubenv"
            if grub_env.is_file():
                output = self.runner.text(["grub-editenv", str(grub_env), "list"])
                for line in output.splitlines():
                    if "=" in line:
                        key, value = line.split("=", 1)
                        grub_environment[key] = value
            snapshots = self.catalog.list()
            state_dir = Path(self.config.STATE_DIR)
            boot_attempts = 0
            try:
                boot_attempts = int(
                    (state_dir / "boot-attempts").read_text(encoding="utf-8").strip() or "0"
                )
            except (OSError, ValueError):
                pass
            try:
                boot_health = json.loads(
                    (state_dir / "boot-health.json").read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                boot_health = {}
            return {
                "schema": 1,
                "running_mode": self._current_mode(),
                "scheduled_mode": (
                    "thawed-once"
                    if grub_environment.get("cachy_once") == "thawed"
                    else grub_environment.get("cachy_mode", "frozen")
                ),
                "grub_entry": grub_environment.get("saved_entry", "unset"),
                "current_subvolume": self._root_subvolume(),
                "golden_present": self._subvolume_exists(self.config.GOLDEN_SUBVOL),
                "active_present": self._subvolume_exists(self.config.ACTIVE_SUBVOL),
                "previous_present": self._subvolume_exists(self.config.PREVIOUS_SUBVOL),
                "failed_golden_present": self._subvolume_exists(self.config.FAILED_GOLDEN_SUBVOL),
                "snapshot_count": len(snapshots),
                "last_snapshot": snapshots[0].to_dict() if snapshots else None,
                "transaction_pending": self.catalog.transaction() is not None,
                "boot_attempts": boot_attempts,
                "boot_failure_limit": self.config.BOOT_FAILURE_LIMIT,
                "last_successful_boot": boot_health.get("last_successful_boot"),
                "last_automatic_recovery": boot_health.get("last_automatic_recovery"),
            }

    def mark_boot_successful(self) -> dict[str, Any]:
        """Confirm graphical userspace reached its healthy target.

        The initramfs increments the durable attempt counter before mounting
        the root. Reaching this service is the positive acknowledgement that
        prevents a failed Golden from boot-looping forever.
        """

        self.require_root()
        state_dir = Path(self.config.STATE_DIR)
        event_path = state_dir / "recovery-event"
        event = ""
        try:
            event = event_path.read_text(encoding="utf-8").strip()
        except OSError:
            pass
        now = datetime.now(UTC).isoformat()
        one_time_thaw_cleared = False
        if self._current_mode() == "thawed":
            grub_env = Path("/boot/grub/grubenv")
            if grub_env.is_file():
                environment = self.runner.text(["grub-editenv", str(grub_env), "list"])
                if "cachy_once=thawed" in environment.splitlines():
                    self.runner.run(["grub-editenv", str(grub_env), "unset", "cachy_once"])
                    verified = self.runner.text(["grub-editenv", str(grub_env), "list"])
                    if "cachy_once=thawed" in verified.splitlines():
                        raise IntegrityError("One-time THAWED boot setting could not be cleared")
                    one_time_thaw_cleared = True
        try:
            current = json.loads((state_dir / "boot-health.json").read_text(encoding="utf-8"))
            if not isinstance(current, dict):
                current = {}
        except (OSError, json.JSONDecodeError):
            current = {}
        current.update({"schema": 1, "last_successful_boot": now})
        automatic_recovery = "automatic-rollback" in event
        if automatic_recovery:
            current["last_automatic_recovery"] = now
        atomic_text_write(state_dir / "boot-attempts", "0\n")
        atomic_json_write(state_dir / "boot-health.json", current, mode=0o644)
        event_path.unlink(missing_ok=True)
        self.logger.write(
            "WARNING" if event else "INFO",
            "boot.success",
            "Boot verified after recovery" if event else "Boot health verification completed",
            recovery_event=event or None,
            automatic_recovery=automatic_recovery,
            one_time_thaw_cleared=one_time_thaw_cleared,
        )
        return {
            "healthy": True,
            "automatic_recovery": automatic_recovery,
            "confirmed_at": now,
            "one_time_thaw_cleared": one_time_thaw_cleared,
        }

    def get_settings(self) -> dict[str, Any]:
        self.require_root()
        return SettingsStore(Path(self.config.STATE_DIR)).load()

    def update_settings(self, changes: dict[str, Any]) -> dict[str, Any]:
        self.require_root()
        with ProcessLock(Path(self.config.LOCK_FILE)):
            result = SettingsStore(Path(self.config.STATE_DIR)).update(changes)
            self._trim_audit_log(int(result["log_retention_lines"]))
        self.logger.write(
            "WARNING",
            "settings.update",
            "Management settings changed",
            changed=sorted(changes),
        )
        return result

    def _trim_audit_log(self, keep: int) -> None:
        path = Path(self.config.LOG_FILE)
        if not path.is_file():
            return
        lines = path.read_bytes().splitlines(keepends=True)
        if len(lines) <= keep:
            return
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            with temporary.open("wb") as handle:
                handle.writelines(lines[-keep:])
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o640)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def automatic_snapshot(self) -> dict[str, Any]:
        self.require_root()
        settings = SettingsStore(Path(self.config.STATE_DIR)).load()
        if not settings["auto_snapshot_enabled"]:
            return {"created": False, "reason": "disabled"}
        if self._root_subvolume() != self.config.MAINTENANCE_SUBVOL:
            return {"created": False, "reason": "frozen"}
        marker = Path(self.config.STATE_DIR) / "last-auto-snapshot"
        try:
            last_run = float(marker.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            last_run = 0.0
        interval = int(settings["auto_snapshot_interval_minutes"]) * 60
        if time.time() - last_run < interval:
            return {"created": False, "reason": "interval"}
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            self._recover_transaction_locked()
            snapshot = self._create_snapshot_locked(
                self._subvolume_path(self.config.MAINTENANCE_SUBVOL),
                "Scheduled automatic snapshot",
                frozen=False,
            )
            atomic_text_write(marker, f"{time.time()}\n")
            removed = self._cleanup_snapshots_locked(int(settings["retention_count"]))
        return {"created": True, "snapshot": snapshot.to_dict(), "removed": removed}

    def check_updates(self) -> dict[str, Any]:
        self.require_root()
        settings = SettingsStore(Path(self.config.STATE_DIR)).load()
        if not settings["update_checks_enabled"]:
            return {"enabled": False, "reason": "disabled", "count": 0, "packages": []}
        if not settings["network_online_checks"]:
            return {"enabled": False, "reason": "network", "count": 0, "packages": []}
        command = ["timeout", "120", "checkupdates"]
        if shutil.which("checkupdates") is None:
            command = ["pacman", "-Qu"]
        completed = self.runner.run(command, check=False)
        if completed.returncode not in {0, 2}:
            detail = completed.stderr.decode("utf-8", errors="replace")
            raise CommandError(command, completed.returncode, detail)
        output = (completed.stdout or b"").decode("utf-8", errors="replace")
        packages = [line.strip() for line in output.splitlines() if line.strip()]
        result = {"enabled": True, "count": len(packages), "packages": packages[:500]}
        self.logger.write("INFO", "updates.check", "Updates checked", count=len(packages))
        return result

    def apply_updates(self) -> dict[str, Any]:
        self.require_root()
        if self._root_subvolume() != self.config.MAINTENANCE_SUBVOL:
            raise CachyFreezeError("Updates can be applied only in THAWED maintenance mode.")
        settings = SettingsStore(Path(self.config.STATE_DIR)).load()
        if not settings["network_online_checks"]:
            raise CachyFreezeError("Online management operations are disabled in settings.")
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            self._recover_transaction_locked()
            before = self._create_snapshot_locked(
                self._subvolume_path(self.config.MAINTENANCE_SUBVOL),
                "Automatic snapshot before system update",
                frozen=False,
            )
            try:
                self.runner.run(
                    ["pacman", "-Syu", "--needed", "--noconfirm"],
                    stdout=subprocess.DEVNULL,
                )
                self.runner.run(["pacman", "-Dk"], stdout=subprocess.DEVNULL)
                after = self._create_snapshot_locked(
                    self._subvolume_path(self.config.MAINTENANCE_SUBVOL),
                    "Golden after system update",
                    frozen=True,
                )
                self._publish_source_locked(
                    self._subvolume_path(self.config.MAINTENANCE_SUBVOL),
                    "publish",
                    after.snapshot_id,
                )
                self._cleanup_snapshots_locked(int(settings["retention_count"]))
            except Exception:
                self.logger.write(
                    "ERROR",
                    "updates.apply.failed",
                    "System update failed; the rollback snapshot was retained",
                    rollback_snapshot=before.snapshot_id,
                )
                raise
        self.logger.write(
            "INFO",
            "updates.apply",
            "System updated and a new Golden published",
            before_snapshot=before.snapshot_id,
            after_snapshot=after.snapshot_id,
        )
        return {"before_snapshot": before.to_dict(), "after_snapshot": after.to_dict()}

    def application_status(self) -> dict[str, Any]:
        self.require_root()
        commands = {
            "Google Chrome": "google-chrome-stable",
            "Slack": "slack",
            "Wine": "wine",
            "LibreOffice": "libreoffice",
            "Zoiper": "zoiper",
            "AnyDesk": "anydesk",
        }
        applications = [
            {"name": name, "installed": shutil.which(command) is not None}
            for name, command in commands.items()
        ]
        microsip_root = Path("/opt/company/microsip")
        microsip_valid = False
        microsip_version = ""
        try:
            archive_name = (microsip_root / "CURRENT").read_text(encoding="utf-8").strip()
            if Path(archive_name).name != archive_name:
                raise IntegrityError("MicroSIP CURRENT contains an invalid filename")
            checksum_line = (microsip_root / "SHA256SUMS").read_text(encoding="utf-8").strip()
            expected, recorded_name = checksum_line.split(None, 1)
            metadata = json.loads((microsip_root / "metadata.json").read_text(encoding="utf-8"))
            archive = microsip_root / archive_name
            digest = hashlib.sha256()
            with archive.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            microsip_valid = (
                recorded_name.strip() == archive_name
                and digest.hexdigest() == expected
                and metadata.get("archive_sha256") == expected
                and isinstance(metadata.get("executable_sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", metadata["executable_sha256"]) is not None
            )
            microsip_version = archive_name.removeprefix("MicroSIP-").removesuffix(".zip")
        except (OSError, ValueError, IntegrityError, json.JSONDecodeError):
            pass
        applications.append(
            {
                "name": "MicroSIP",
                "installed": microsip_valid,
                "version": microsip_version,
                "checksum_valid": microsip_valid,
            }
        )
        return {
            "applications": applications,
            "all_installed": all(item["installed"] for item in applications),
        }

    def install_applications(self) -> dict[str, Any]:
        self.require_root()
        if self._root_subvolume() != self.config.MAINTENANCE_SUBVOL:
            raise CachyFreezeError("Applications can be installed only in THAWED mode.")
        settings = SettingsStore(Path(self.config.STATE_DIR)).load()
        if not settings["network_online_checks"]:
            raise CachyFreezeError("Online management operations are disabled in settings.")
        script = Path("/usr/lib/cachy-freeze/deployment/installer/install-applications.sh")
        if not script.is_file():
            raise CachyFreezeError("The verified application installer was not found.")
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            self._recover_transaction_locked()
            before = self._create_snapshot_locked(
                self._subvolume_path(self.config.MAINTENANCE_SUBVOL),
                "Snapshot before application installation",
                frozen=False,
            )
            try:
                self.runner.run(["bash", str(script)], stdout=subprocess.DEVNULL)
                status = self.application_status()
                if not status["all_installed"]:
                    raise IntegrityError("One or more applications could not be verified")
                after = self._create_snapshot_locked(
                    self._subvolume_path(self.config.MAINTENANCE_SUBVOL),
                    "Golden after application installation",
                    frozen=True,
                )
                self._publish_source_locked(
                    self._subvolume_path(self.config.MAINTENANCE_SUBVOL),
                    "publish",
                    after.snapshot_id,
                )
                self._cleanup_snapshots_locked(int(settings["retention_count"]))
            except Exception:
                self.logger.write(
                    "ERROR",
                    "applications.install.failed",
                    "Application installation failed; the rollback snapshot was retained",
                    rollback_snapshot=before.snapshot_id,
                )
                raise
        self.logger.write(
            "INFO",
            "applications.install",
            "Applications verified and a new Golden published",
            before_snapshot=before.snapshot_id,
            after_snapshot=after.snapshot_id,
        )
        return {**status, "before_snapshot": before.to_dict(), "after_snapshot": after.to_dict()}

    def create_snapshot(self, description: str) -> SnapshotMetadata:
        self.require_root()
        if self._root_subvolume() != self.config.MAINTENANCE_SUBVOL:
            raise CachyFreezeError("Snapshots can be created only in THAWED mode.")
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            self._recover_transaction_locked()
            snapshot = self._create_snapshot_locked(
                self._subvolume_path(self.config.MAINTENANCE_SUBVOL),
                description,
                frozen=False,
            )
            self._cleanup_snapshots_locked(self._retention_count())
            return snapshot

    def list_snapshots(self) -> list[SnapshotMetadata]:
        return self.catalog.list()

    def verify_snapshot(self, snapshot_id: str, *, full: bool = False) -> dict[str, Any]:
        self.require_root()
        metadata = self.catalog.get(snapshot_id)
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            result = self._verify_snapshot_locked(metadata, full=full)
            self.logger.write(
                "INFO" if result["healthy"] else "ERROR",
                "snapshot.verify",
                "Snapshot verification completed",
                **result,
            )
            return result

    def _verify_snapshot_locked(
        self, metadata: SnapshotMetadata, *, full: bool = False
    ) -> dict[str, Any]:
        path = self._subvolume_path(metadata.subvolume)
        errors: list[str] = []
        if not metadata.verifies():
            errors.append("metadata checksum mismatch")
        if not self._subvolume_exists(path):
            errors.append("Btrfs subvolume is missing")
        else:
            details = self._subvolume_details(path)
            if details.get("uuid") != metadata.btrfs_uuid:
                errors.append("Btrfs UUID mismatch")
            if not self._is_read_only(path):
                errors.append("snapshot is not read-only")
        stream_checksum: str | None = None
        if full and not errors:
            digest = hashlib.sha256()
            process = subprocess.Popen(
                ["btrfs", "send", str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.runner.environment,
            )
            assert process.stdout is not None
            for block in iter(lambda: process.stdout.read(1024 * 1024), b""):
                digest.update(block)
            _, stderr = process.communicate()
            if process.returncode != 0:
                raise CommandError(
                    ["btrfs", "send", str(path)],
                    process.returncode,
                    stderr.decode("utf-8", errors="replace"),
                )
            stream_checksum = digest.hexdigest()
        healthy = not errors
        desired_health = "healthy" if healthy else "error"
        if metadata.health != desired_health:
            self.catalog.set_health(metadata.snapshot_id, desired_health)
        return {
            "snapshot_id": metadata.snapshot_id,
            "healthy": healthy,
            "errors": errors,
            "metadata_checksum": metadata.checksum,
            "stream_sha256": stream_checksum,
        }

    def delete_snapshot(self, snapshot_id: str) -> SnapshotMetadata:
        self.require_root()
        if not _SNAPSHOT_ID_RE.fullmatch(snapshot_id):
            raise CachyFreezeError("Invalid snapshot ID.")
        metadata = self.catalog.get(snapshot_id)
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            path = self._subvolume_path(metadata.subvolume)
            self._delete_subvolume(path)
            removed = self.catalog.remove(snapshot_id)
            self.logger.write(
                "INFO",
                "snapshot.delete",
                "Snapshot silindi",
                snapshot_id=snapshot_id,
                btrfs_uuid=removed.btrfs_uuid,
            )
            return removed

    def compare_snapshots(self, older_id: str, newer_id: str) -> dict[str, Any]:
        self.require_root()
        older = self.catalog.get(older_id)
        newer = self.catalog.get(newer_id)
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            older_path = self._subvolume_path(older.subvolume)
            newer_path = self._subvolume_path(newer.subvolume)
            older_details = self._subvolume_details(older_path)
            generation = older_details.get("generation")
            if not generation or not generation.isdigit():
                raise IntegrityError("Older snapshot generation is unavailable")
            output = self.runner.text(
                ["btrfs", "subvolume", "find-new", str(newer_path), generation]
            )
            changed_paths: list[str] = []
            for line in output.splitlines():
                marker = " path "
                if marker in line:
                    changed_paths.append(line.split(marker, 1)[1])
            return {
                "older": older_id,
                "newer": newer_id,
                "changed_path_count": len(set(changed_paths)),
                "changed_paths": sorted(set(changed_paths))[:5000],
                "truncated": len(set(changed_paths)) > 5000,
            }

    def export_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        self.require_root()
        metadata = self.catalog.get(snapshot_id)
        export_dir = Path(self.config.EXPORT_DIR)
        destination = export_dir / f"{snapshot_id}.btrfs"
        manifest = export_dir / f"{snapshot_id}.json"
        if destination.exists() or manifest.exists():
            raise CachyFreezeError(
                "An export already exists for this snapshot; move it to a safe location first."
            )
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            verification = self._verify_snapshot_locked(metadata)
            if not verification["healthy"]:
                raise IntegrityError("Bozuk snapshot export edilemez")
            export_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(export_dir, 0o700)
            temporary = export_dir / f".{snapshot_id}.{uuid.uuid4().hex}.tmp"
            source = self._subvolume_path(metadata.subvolume)
            try:
                descriptor = os.open(
                    temporary,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
                with os.fdopen(descriptor, "wb") as handle:
                    self.runner.run(["btrfs", "send", str(source)], stdout=handle)
                    handle.flush()
                    os.fsync(handle.fileno())
                digest = hashlib.sha256()
                with temporary.open("rb") as handle:
                    for block in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(block)
                stream_checksum = digest.hexdigest()
                size = temporary.stat().st_size
                if size == 0:
                    raise IntegrityError("Btrfs export stream is empty")
                os.replace(temporary, destination)
                atomic_json_write(
                    manifest,
                    {
                        "schema": 1,
                        "created_at": datetime.now(UTC).isoformat(),
                        "stream_sha256": stream_checksum,
                        "stream_size_bytes": size,
                        "snapshot": metadata.to_dict(),
                    },
                    mode=0o600,
                )
            finally:
                temporary.unlink(missing_ok=True)
            result = {
                "snapshot_id": snapshot_id,
                "archive": str(destination),
                "manifest": str(manifest),
                "stream_sha256": stream_checksum,
                "stream_size_bytes": size,
            }
            self.logger.write(
                "INFO",
                "snapshot.export",
                "Snapshot Btrfs send stream olarak export edildi",
                **result,
            )
            return result

    def import_snapshot(self, archive_name: str) -> SnapshotMetadata:
        self.require_root()
        if Path(archive_name).name != archive_name or not archive_name.endswith(".btrfs"):
            raise CachyFreezeError("Import accepts only a filename from the export directory.")
        source = Path(self.config.EXPORT_DIR) / archive_name
        manifest = source.with_suffix(".json")
        if not source.is_file() or not manifest.is_file():
            raise CachyFreezeError("Snapshot archive or manifest was not found.")
        try:
            document = json.loads(manifest.read_text(encoding="utf-8"))
            expected_checksum = str(document["stream_sha256"])
            exported_metadata = SnapshotMetadata.from_dict(document["snapshot"])
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise IntegrityError(f"Snapshot export manifest is invalid: {error}") from error
        if not exported_metadata.verifies():
            raise IntegrityError("Snapshot export metadata checksum verification failed")
        digest = hashlib.sha256()
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected_checksum:
            raise IntegrityError("Snapshot export checksum verification failed")

        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            parent = self._ensure_snapshot_parent()
            staging = parent / f".import-{uuid.uuid4().hex}"
            staging.mkdir(mode=0o700)
            received: Path | None = None
            destination: Path | None = None
            try:
                with source.open("rb") as handle:
                    self.runner.run(
                        ["btrfs", "receive", str(staging)],
                        stdin=handle,
                        stdout=subprocess.DEVNULL,
                    )
                children = list(staging.iterdir())
                if len(children) != 1 or not self._subvolume_exists(children[0]):
                    raise IntegrityError("Btrfs receive did not produce exactly one snapshot")
                received = children[0]
                snapshot_id = (
                    f"snap-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
                )
                destination = parent / snapshot_id
                # A received subvolume carries received_uuid and is read-only.
                # Some Btrfs versions reject renaming that object with EROFS.
                # Create a local read-only snapshot instead, then remove the
                # transient received object. This also gives the catalog a
                # normal local UUID without weakening the received snapshot.
                self.runner.run(
                    [
                        "btrfs",
                        "subvolume",
                        "snapshot",
                        "-r",
                        str(received),
                        str(destination),
                    ]
                )
                self._delete_subvolume(received)
                received = None
                details = self._subvolume_details(destination)
                apparent, exclusive = self._subvolume_sizes(destination)
                metadata = SnapshotMetadata.create(
                    snapshot_id=snapshot_id,
                    subvolume=f"{self.config.SNAPSHOT_SUBVOL}/{snapshot_id}",
                    btrfs_uuid=details["uuid"],
                    parent_uuid=details.get("parent_uuid", "-"),
                    created_at=datetime.now(UTC).isoformat(),
                    kernel=exported_metadata.kernel,
                    apparent_size_bytes=apparent,
                    exclusive_size_bytes=exclusive,
                    description=f"Imported: {exported_metadata.description}"[:512],
                    created_by=self._creator(),
                    frozen=exported_metadata.frozen,
                    bootable=(destination / "boot" / "vmlinuz-linux-cachyos").is_file(),
                    creation_duration_ms=0,
                    source_subvolume=f"import:{exported_metadata.snapshot_id}",
                )
                self.catalog.add(metadata)
            except Exception:
                if destination is not None:
                    self._delete_subvolume(destination)
                if staging.exists():
                    for child in staging.iterdir():
                        if self._subvolume_exists(child):
                            self._delete_subvolume(child)
                        elif child.is_dir():
                            shutil.rmtree(child)
                        else:
                            child.unlink(missing_ok=True)
                raise
            finally:
                if staging.exists():
                    staging.rmdir()
            self._cleanup_snapshots_locked(self._retention_count())
            self.logger.write(
                "INFO",
                "snapshot.import",
                "Snapshot imported with checksum verification",
                snapshot_id=metadata.snapshot_id,
                source_archive=archive_name,
            )
            return metadata

    def health(self) -> dict[str, Any]:
        self.require_root()
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            snapshot_results = [
                self._verify_snapshot_locked(snapshot) for snapshot in self.catalog.list()
            ]
            device_output = self.runner.text(["btrfs", "device", "stats", self._root_device()])
            device_errors: dict[str, int] = {}
            for line in device_output.splitlines():
                if "." not in line or " " not in line:
                    continue
                key, raw_value = line.rsplit(None, 1)
                if raw_value.isdigit():
                    device_errors[key] = int(raw_value)
            scrub = self.runner.text(["btrfs", "scrub", "status", self._root_device()], check=False)
            unhealthy = [
                result["snapshot_id"] for result in snapshot_results if not result["healthy"]
            ]
            result = {
                "healthy": not unhealthy and not any(device_errors.values()),
                "unhealthy_snapshots": unhealthy,
                "device_errors": device_errors,
                "scrub_status": scrub,
            }
            self.logger.write(
                "INFO" if result["healthy"] else "ERROR",
                "health",
                "Btrfs and snapshot health check completed",
                **result,
            )
            return result

    def publish(self, description: str) -> SnapshotMetadata:
        self.require_root()
        if self._root_subvolume() != self.config.MAINTENANCE_SUBVOL:
            raise CachyFreezeError("Golden can be published only in THAWED mode.")
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            from .users import UserManager

            self._recover_transaction_locked()
            UserManager(
                state_dir=Path(self.config.STATE_DIR),
                lock_file=Path(self.config.LOCK_FILE),
                logger=self.logger,
                runner=self.runner,
            ).refresh_templates(already_locked=True)
            archived = self._create_snapshot_locked(
                self._subvolume_path(self.config.MAINTENANCE_SUBVOL),
                description,
                frozen=True,
            )
            self._publish_source_locked(
                self._subvolume_path(self.config.MAINTENANCE_SUBVOL),
                "publish",
                archived.snapshot_id,
            )
            self._cleanup_snapshots_locked(self._retention_count())
            self.logger.write(
                "INFO",
                "publish",
                "New Golden and Active snapshots published atomically",
                snapshot_id=archived.snapshot_id,
            )
            return archived

    def rollback(self, snapshot_id: str) -> SnapshotMetadata:
        self.require_root()
        metadata = self.catalog.get(snapshot_id)
        if not metadata.bootable:
            raise CachyFreezeError("The selected snapshot is not bootable.")
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            self._recover_transaction_locked()
            result = self._verify_snapshot_locked(metadata)
            if not result["healthy"]:
                raise IntegrityError("An unhealthy snapshot cannot be restored")
            self._publish_source_locked(
                self._subvolume_path(metadata.subvolume), "rollback", snapshot_id
            )
            updated = self.catalog.increment_rollback(snapshot_id)
            self._set_boot_mode_locked("frozen")
            self.logger.write(
                "WARNING",
                "snapshot.rollback",
                "Golden rolled back to the selected snapshot",
                snapshot_id=snapshot_id,
                rollback_count=updated.rollback_count,
            )
            return updated

    def _retention_count(self) -> int:
        store = SettingsStore(Path(self.config.STATE_DIR))
        if not store.path.exists():
            return self.config.RETENTION_COUNT
        settings = store.load()
        return int(settings.get("retention_count", self.config.RETENTION_COUNT))

    def _cleanup_snapshots_locked(self, retention: int) -> list[str]:
        if not 1 <= retention <= 1000:
            raise CachyFreezeError("Retention count must be between 1 and 1000.")
        snapshots = self.catalog.list()
        removed: list[str] = []
        for snapshot in snapshots[retention:]:
            self._delete_subvolume(self._subvolume_path(snapshot.subvolume))
            self.catalog.remove(snapshot.snapshot_id)
            removed.append(snapshot.snapshot_id)
        return removed

    def cleanup(self, keep: int | None = None) -> list[str]:
        self.require_root()
        retention = keep if keep is not None else self._retention_count()
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            self._recover_transaction_locked()
            removed = self._cleanup_snapshots_locked(retention)
        self.logger.write(
            "INFO",
            "snapshot.cleanup",
            "Snapshot retention policy applied",
            retention=retention,
            removed=removed,
        )
        return removed

    def _set_boot_mode_locked(self, mode: str) -> None:
        if mode not in {"frozen", "thawed", "thawed-once"}:
            raise CachyFreezeError(f"Invalid boot mode: {mode}")
        maintenance = self._subvolume_path(self.config.MAINTENANCE_SUBVOL)
        grub_cfg = maintenance / "boot/grub/grub.cfg"
        grub_env = maintenance / "boot/grub/grubenv"
        if not grub_cfg.is_file() or not grub_env.is_file():
            raise CachyFreezeError("Canonical maintenance GRUB files were not found.")
        if "--id 'cachyos-current'" not in grub_cfg.read_text(encoding="utf-8", errors="replace"):
            raise IntegrityError("The cachyos-current GRUB entry was not found")
        persistent_mode = "frozen" if mode == "thawed-once" else mode
        assignments = [
            f"cachy_mode={persistent_mode}",
            "saved_entry=cachyos-current",
        ]
        if mode == "thawed-once":
            assignments.append("cachy_once=thawed")
        self.runner.run(["grub-editenv", str(grub_env), "set", *assignments])
        if mode != "thawed-once":
            self.runner.run(["grub-editenv", str(grub_env), "unset", "cachy_once"], check=False)
        environment = self.runner.text(["grub-editenv", str(grub_env), "list"])
        expected = {f"cachy_mode={persistent_mode}", "saved_entry=cachyos-current"}
        if mode == "thawed-once":
            expected.add("cachy_once=thawed")
        if not expected.issubset(set(environment.splitlines())):
            raise IntegrityError("GRUB boot mode could not be verified after writing")

    def set_boot_mode(self, mode: str) -> None:
        self.require_root()
        with ProcessLock(Path(self.config.LOCK_FILE)), self.mounted_top():
            self._recover_transaction_locked()
            if mode in {"frozen", "thawed-once"}:
                for required in (
                    self.config.GOLDEN_SUBVOL,
                    self.config.ACTIVE_SUBVOL,
                ):
                    if not self._subvolume_exists(required):
                        raise CachyFreezeError(f"Gerekli snapshot yok: {required}")
            self._set_boot_mode_locked(mode)
            self.logger.write(
                "INFO",
                "boot.mode",
                "Next persistent boot mode changed",
                mode=mode,
            )

    def recent_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise CachyFreezeError("Log line limit must be between 1 and 1000.")
        path = Path(self.config.LOG_FILE)
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        entries: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                entries.append(item)
        return entries

    def write_status_cache(self, status: dict[str, Any]) -> None:
        cache = Path(self.config.STATE_DIR) / "status.json"
        atomic_json_write(cache, status, mode=0o644)
