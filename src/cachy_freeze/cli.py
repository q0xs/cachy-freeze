"""Minimal privileged command contract used by the PolicyKit helper."""

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


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="cachy-freeze")
    commands = result.add_subparsers(dest="command", required=True)
    for command in ("preflight", "version", "migrate", "status", "freeze"):
        commands.add_parser(command)
    thaw = commands.add_parser("thaw")
    thaw.add_argument(
        "--authorized",
        "--remote",
        action="store_true",
        dest="authorized",
        help="schedule one passwordless remote THAWED boot and consume it after boot verification",
    )
    commands.add_parser("boot-success")
    commands.add_parser("reboot")
    return result


def _config_path() -> Path:
    configured = os.environ.get("CACHY_FREEZE_CONFIG")
    return Path(configured) if configured else Path("/etc/cachy-freeze.conf")


def dispatch(engine: FreezeEngine, arguments: argparse.Namespace) -> Any:
    operations = {
        "preflight": engine.preflight,
        "version": engine.version_info,
        "migrate": engine.migrate_state,
        "status": engine.status,
        "freeze": engine.freeze,
        "boot-success": engine.mark_boot_successful,
        "reboot": engine.request_reboot,
    }
    if arguments.command == "thaw":
        return engine.thaw(authorized=arguments.authorized)
    return operations[arguments.command]()


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    engine: FreezeEngine | None = None
    try:
        engine = FreezeEngine(Config.load(_config_path()))
        result = dispatch(engine, arguments)
        if arguments.command in {"status", "freeze", "thaw", "boot-success"}:
            engine.write_status_cache(engine.status())
    except CachyFreezeError as error:
        if engine is not None:
            try:
                engine.logger.write(
                    "ERROR",
                    "command.failed",
                    "Privileged CachyFreeze command failed",
                    command=arguments.command,
                    error_type=type(error).__name__,
                )
            except OSError:
                pass
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"ERROR: Unexpected system error: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
