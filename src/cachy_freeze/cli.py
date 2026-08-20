"""Command-line contract consumed by the privileged GUI helper."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .config import Config
from .engine import FreezeEngine
from .errors import CachyFreezeError


def _json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="cachy-freeze")
    subcommands = result.add_subparsers(dest="command", required=True)
    subcommands.add_parser("preflight")
    subcommands.add_parser("version")
    subcommands.add_parser("migrate")
    subcommands.add_parser("status")
    subcommands.add_parser("freeze")
    subcommands.add_parser("thaw")
    subcommands.add_parser("thaw-once")
    subcommands.add_parser("health")
    subcommands.add_parser("diagnostics")
    subcommands.add_parser("boot-success")
    subcommands.add_parser("auto-snapshot")

    finalize = subcommands.add_parser("finalize")
    finalize_commands = finalize.add_subparsers(dest="finalize_command", required=True)
    finalize_request = finalize_commands.add_parser("request")
    finalize_request.add_argument("username")
    finalize_request.add_argument("--uid", type=int, required=True)
    finalize_run = finalize_commands.add_parser("run")
    finalize_run.add_argument("--timeout", type=int, default=180)
    finalize_commands.add_parser("status")

    idle_power = subcommands.add_parser("idle-power")
    idle_power_commands = idle_power.add_subparsers(dest="idle_power_command", required=True)
    idle_power_commands.add_parser("status")
    idle_power_run = idle_power_commands.add_parser("run")
    idle_power_run.add_argument("--poll", type=int, default=15)

    updates = subcommands.add_parser("updates")
    updates.add_argument("operation", choices=("check", "apply"))
    applications = subcommands.add_parser("applications")
    applications.add_argument("operation", choices=("status", "install"))

    settings = subcommands.add_parser("settings")
    settings_commands = settings.add_subparsers(dest="settings_command", required=True)
    settings_commands.add_parser("get")
    settings_set = settings_commands.add_parser("set")
    settings_set.add_argument("--retention-count", type=int, required=True)
    settings_set.add_argument("--auto-snapshot-enabled", choices=("true", "false"), required=True)
    settings_set.add_argument("--auto-snapshot-interval", type=int, required=True)
    settings_set.add_argument("--update-checks-enabled", choices=("true", "false"), required=True)
    settings_set.add_argument("--network-online-checks", choices=("true", "false"), required=True)
    settings_set.add_argument("--boot-failure-limit", type=int, required=True)
    settings_set.add_argument("--log-retention-lines", type=int, required=True)
    settings_set.add_argument("--language", choices=("en", "tr"), required=True)
    settings_set.add_argument("--theme", choices=("dark", "light"), required=True)

    publish = subcommands.add_parser("publish")
    publish.add_argument("--description", default="Automatic snapshot before Golden publication")

    snapshot = subcommands.add_parser("snapshot")
    snapshot_commands = snapshot.add_subparsers(dest="snapshot_command", required=True)
    create = snapshot_commands.add_parser("create")
    create.add_argument("--description", required=True)
    snapshot_commands.add_parser("list")
    verify = snapshot_commands.add_parser("verify")
    verify.add_argument("snapshot_id")
    verify.add_argument("--full", action="store_true")
    delete = snapshot_commands.add_parser("delete")
    delete.add_argument("snapshot_id")
    compare = snapshot_commands.add_parser("compare")
    compare.add_argument("older_id")
    compare.add_argument("newer_id")
    rollback = snapshot_commands.add_parser("rollback")
    rollback.add_argument("snapshot_id")
    export = snapshot_commands.add_parser("export")
    export.add_argument("snapshot_id")
    import_command = snapshot_commands.add_parser("import")
    import_command.add_argument("archive_name")
    cleanup = snapshot_commands.add_parser("cleanup")
    cleanup.add_argument("--keep", type=int)

    logs = subcommands.add_parser("logs")
    logs.add_argument("--limit", type=int, default=100)

    user = subcommands.add_parser("user")
    user_commands = user.add_subparsers(dest="user_command", required=True)
    user_commands.add_parser("list")
    user_create = user_commands.add_parser("create")
    user_create.add_argument("username")
    user_create.add_argument("--display-name", required=True)
    user_delete = user_commands.add_parser("delete")
    user_delete.add_argument("username")
    user_restore = user_commands.add_parser("restore")
    user_restore.add_argument("backup_id")
    user_password = user_commands.add_parser("password")
    user_password.add_argument("username")
    user_lock = user_commands.add_parser("lock")
    user_lock.add_argument("username")
    user_unlock = user_commands.add_parser("unlock")
    user_unlock.add_argument("username")
    user_autologin = user_commands.add_parser("autologin")
    user_autologin.add_argument("username", nargs="?")
    return result


def _config_path() -> Path:
    configured = os.environ.get("CACHY_FREEZE_CONFIG")
    if configured:
        return Path(configured)
    return Path("/etc/cachy-freeze.conf")


def dispatch(engine: FreezeEngine, arguments: argparse.Namespace) -> Any:
    if arguments.command == "preflight":
        return engine.preflight()
    if arguments.command == "version":
        return engine.version_info()
    if arguments.command == "migrate":
        return engine.migrate_state()
    if arguments.command == "status":
        status = engine.status()
        engine.write_status_cache(status)
        return status
    if arguments.command == "freeze":
        engine.set_boot_mode("frozen")
        return {"mode": "frozen"}
    if arguments.command == "thaw":
        engine.set_boot_mode("thawed")
        return {"mode": "thawed"}
    if arguments.command == "thaw-once":
        engine.set_boot_mode("thawed-once")
        return {"mode": "thawed-once"}
    if arguments.command == "health":
        return engine.health()
    if arguments.command == "diagnostics":
        return engine.diagnostics()
    if arguments.command == "boot-success":
        return engine.mark_boot_successful()
    if arguments.command == "auto-snapshot":
        return engine.automatic_snapshot()
    if arguments.command == "finalize":
        if arguments.finalize_command == "request":
            return engine.request_finalization(arguments.username, arguments.uid)
        if arguments.finalize_command == "run":
            return engine.run_pending_finalization(arguments.timeout)
        return engine.finalization_status()
    if arguments.command == "idle-power":
        if arguments.idle_power_command == "run":
            return engine.run_power_policy(arguments.poll)
        return engine.power_policy_status()
    if arguments.command == "updates":
        return engine.check_updates() if arguments.operation == "check" else engine.apply_updates()
    if arguments.command == "applications":
        return (
            engine.application_status()
            if arguments.operation == "status"
            else engine.install_applications()
        )
    if arguments.command == "settings":
        if arguments.settings_command == "get":
            return engine.get_settings()
        return engine.update_settings(
            {
                "retention_count": arguments.retention_count,
                "auto_snapshot_enabled": arguments.auto_snapshot_enabled == "true",
                "auto_snapshot_interval_minutes": arguments.auto_snapshot_interval,
                "update_checks_enabled": arguments.update_checks_enabled == "true",
                "network_online_checks": arguments.network_online_checks == "true",
                "boot_failure_limit": arguments.boot_failure_limit,
                "log_retention_lines": arguments.log_retention_lines,
                "language": arguments.language,
                "theme": arguments.theme,
            }
        )
    if arguments.command == "publish":
        return engine.publish(arguments.description).to_dict()
    if arguments.command == "logs":
        return engine.recent_logs(arguments.limit)
    if arguments.command == "user":
        from .users import UserManager

        manager = UserManager(
            state_dir=Path(engine.config.STATE_DIR),
            lock_file=Path(engine.config.LOCK_FILE),
            logger=engine.logger,
            runner=engine.runner,
        )
        operation = arguments.user_command
        if operation == "list":
            return manager.list_users()
        if engine._root_subvolume() != engine.config.MAINTENANCE_SUBVOL:
            raise CachyFreezeError("User changes are allowed only in THAWED maintenance mode.")
        if operation == "create":
            return manager.create(
                arguments.username,
                arguments.display_name,
                _password_from_stdin(),
            )
        if operation == "delete":
            return manager.delete(arguments.username)
        if operation == "restore":
            return manager.restore(arguments.backup_id)
        if operation == "password":
            manager.set_password(arguments.username, _password_from_stdin())
            return {"username": arguments.username, "password_changed": True}
        if operation == "lock":
            manager.set_locked(arguments.username, True)
            return {"username": arguments.username, "locked": True}
        if operation == "unlock":
            manager.set_locked(arguments.username, False)
            return {"username": arguments.username, "locked": False}
        if operation == "autologin":
            return manager.set_autologin(arguments.username)
    if arguments.command == "snapshot":
        operation = arguments.snapshot_command
        if operation == "create":
            return engine.create_snapshot(arguments.description).to_dict()
        if operation == "list":
            return [snapshot.to_dict() for snapshot in engine.list_snapshots()]
        if operation == "verify":
            return engine.verify_snapshot(arguments.snapshot_id, full=arguments.full)
        if operation == "delete":
            return engine.delete_snapshot(arguments.snapshot_id).to_dict()
        if operation == "compare":
            return engine.compare_snapshots(arguments.older_id, arguments.newer_id)
        if operation == "rollback":
            return engine.rollback(arguments.snapshot_id).to_dict()
        if operation == "export":
            return engine.export_snapshot(arguments.snapshot_id)
        if operation == "import":
            return engine.import_snapshot(arguments.archive_name).to_dict()
        if operation == "cleanup":
            return {"removed": engine.cleanup(arguments.keep)}
    raise AssertionError(f"Unhandled command: {arguments.command}")


def _password_from_stdin() -> str:
    password = sys.stdin.readline(258)
    if not password.endswith("\n") or len(password) > 257:
        raise CachyFreezeError("Password was not received through the secure input channel.")
    return password[:-1]


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        config = Config.load(_config_path())
        engine = FreezeEngine(config)
        value = dispatch(engine, arguments)
        if (
            arguments.command in {"freeze", "thaw", "thaw-once", "publish"}
            or (
                arguments.command == "finalize" and arguments.finalize_command in {"request", "run"}
            )
            or (
                arguments.command == "snapshot"
                and arguments.snapshot_command
                in {"create", "delete", "rollback", "import", "cleanup"}
            )
            or (arguments.command == "updates" and arguments.operation == "apply")
            or (arguments.command == "applications" and arguments.operation == "install")
        ):
            engine.write_status_cache(engine.status())
    except CachyFreezeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"ERROR: Unexpected system error: {error}", file=sys.stderr)
        return 1
    _json({"ok": True, "result": value})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
