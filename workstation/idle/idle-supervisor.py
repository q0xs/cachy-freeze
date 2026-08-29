#!/usr/bin/env python3
"""Root supervisor for the CachyWorkstation KDE idle event agent."""

from __future__ import annotations

import argparse
import dataclasses
import os
import pwd
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

CONFIG_PATH = Path("/etc/cachy-workstation/workstation.conf")
AGENT_PATH = Path("/usr/lib/cachy-workstation/cachy-workstation-idle-agent")
LOGINCTL = "/usr/bin/loginctl"
SYSTEMCTL = "/usr/bin/systemctl"
RUNUSER = "/usr/bin/runuser"
ENV = "/usr/bin/env"
SESSION_TYPES = {"wayland", "x11"}
ALLOWED_ENVIRONMENT = {
    "DBUS_SESSION_BUS_ADDRESS",
    "DISPLAY",
    "KDE_FULL_SESSION",
    "KDE_SESSION_VERSION",
    "WAYLAND_DISPLAY",
    "XAUTHORITY",
    "XDG_CURRENT_DESKTOP",
    "XDG_RUNTIME_DIR",
    "XDG_SESSION_DESKTOP",
    "XDG_SESSION_TYPE",
}


class ConfigurationError(RuntimeError):
    """Raised when the root-owned policy configuration is invalid."""


@dataclasses.dataclass(frozen=True)
class Config:
    username: str
    uid: int
    gid: int
    home: str
    lock_seconds: int
    shutdown_seconds: int


@dataclasses.dataclass(frozen=True)
class Session:
    identifier: str
    properties: dict[str, str]


def log(message: str) -> None:
    print(f"cachy-workstation-idle: {message}", flush=True)


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator != "=" or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ConfigurationError(f"invalid configuration line: {raw_line!r}")
        if key in values:
            raise ConfigurationError(f"duplicate configuration key: {key}")
        values[key] = value
    return values


def read_config(
    path: Path = CONFIG_PATH,
    *,
    require_root_owner: bool = True,
    verify_account: bool = True,
) -> Config:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ConfigurationError(f"cannot read {path}: {error}") from error
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise ConfigurationError("configuration is not a regular file")
    if require_root_owner and (metadata.st_uid != 0 or metadata.st_gid != 0):
        raise ConfigurationError("configuration is not owned by root:root")
    if metadata.st_mode & 0o022:
        raise ConfigurationError("configuration is group/world writable")

    values = _parse_key_values(path.read_text(encoding="utf-8"))
    required = {
        "TARGET_USER",
        "TARGET_UID",
        "TARGET_GID",
        "TARGET_HOME",
        "LOCK_SECONDS",
        "SHUTDOWN_SECONDS",
    }
    if set(values) != required:
        missing = sorted(required - set(values))
        unexpected = sorted(set(values) - required)
        raise ConfigurationError(
            f"configuration keys differ; missing={missing}, unexpected={unexpected}"
        )
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,30}", values["TARGET_USER"]):
        raise ConfigurationError("invalid target username")
    if not re.fullmatch(r"/home/[A-Za-z0-9._-]+", values["TARGET_HOME"]):
        raise ConfigurationError("invalid target home")
    try:
        uid = int(values["TARGET_UID"])
        gid = int(values["TARGET_GID"])
        lock_seconds = int(values["LOCK_SECONDS"])
        shutdown_seconds = int(values["SHUTDOWN_SECONDS"])
    except ValueError as error:
        raise ConfigurationError("numeric configuration value is invalid") from error
    if not 1000 <= uid < 65534 or gid < 1:
        raise ConfigurationError("target account identifiers are invalid")
    if lock_seconds < 60 or shutdown_seconds <= lock_seconds:
        raise ConfigurationError("idle intervals are invalid")

    config = Config(
        username=values["TARGET_USER"],
        uid=uid,
        gid=gid,
        home=values["TARGET_HOME"],
        lock_seconds=lock_seconds,
        shutdown_seconds=shutdown_seconds,
    )
    if verify_account:
        try:
            account = pwd.getpwnam(config.username)
        except KeyError as error:
            raise ConfigurationError("configured target user no longer exists") from error
        if (account.pw_uid, account.pw_gid, account.pw_dir) != (
            config.uid,
            config.gid,
            config.home,
        ):
            raise ConfigurationError("configured account data no longer matches the user database")
    return config


class Supervisor:
    def __init__(
        self,
        config: Config,
        *,
        run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        popen: Callable[..., subprocess.Popen[str]] = subprocess.Popen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self.run = run
        self.popen = popen
        self.sleep = sleep
        self.stopping = False

    def command(self, arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return self.run(
            list(arguments),
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def session_properties(self, identifier: str) -> dict[str, str] | None:
        result = self.command(
            [
                LOGINCTL,
                "show-session",
                identifier,
                "--property=Id",
                "--property=Name",
                "--property=User",
                "--property=Class",
                "--property=Active",
                "--property=Remote",
                "--property=Type",
                "--property=State",
                "--property=Seat",
            ]
        )
        if result.returncode != 0:
            return None
        try:
            return _parse_key_values(result.stdout)
        except ConfigurationError:
            return None

    def eligible(self, properties: dict[str, str] | None) -> bool:
        if not properties:
            return False
        return (
            properties.get("Name") == self.config.username
            and properties.get("User") == str(self.config.uid)
            and properties.get("Class") == "user"
            and properties.get("Active") == "yes"
            and properties.get("Remote") == "no"
            and properties.get("Type") in SESSION_TYPES
        )

    def find_session(self) -> Session | None:
        result = self.command([LOGINCTL, "list-sessions", "--no-legend", "--no-pager"])
        if result.returncode != 0:
            return None
        candidates: list[Session] = []
        for line in result.stdout.splitlines():
            fields = line.split()
            if not fields:
                continue
            identifier = fields[0]
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", identifier):
                continue
            properties = self.session_properties(identifier)
            if self.eligible(properties):
                candidates.append(Session(identifier, properties or {}))
        candidates.sort(key=lambda session: session.properties.get("Seat") != "seat0")
        return candidates[0] if candidates else None

    def user_environment(self, session: Session) -> dict[str, str] | None:
        result = self.command(
            [SYSTEMCTL, "--user", f"--machine={self.config.username}@", "show-environment"]
        )
        if result.returncode != 0:
            return None
        try:
            raw_environment = _parse_key_values(result.stdout)
        except ConfigurationError:
            return None
        environment = {
            key: value
            for key, value in raw_environment.items()
            if key in ALLOWED_ENVIRONMENT and "\x00" not in value and "\n" not in value
        }
        runtime_dir = f"/run/user/{self.config.uid}"
        environment["HOME"] = self.config.home
        environment["USER"] = self.config.username
        environment["LOGNAME"] = self.config.username
        environment["PATH"] = "/usr/local/bin:/usr/bin:/usr/sbin"
        environment["XDG_RUNTIME_DIR"] = runtime_dir
        environment["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={runtime_dir}/bus"
        environment["XDG_SESSION_ID"] = session.identifier
        environment["XDG_SESSION_TYPE"] = session.properties["Type"]
        environment.setdefault("XDG_CURRENT_DESKTOP", "KDE")
        environment.setdefault("KDE_FULL_SESSION", "true")
        environment.setdefault("KDE_SESSION_VERSION", "6")

        if session.properties["Type"] == "wayland":
            display = environment.get("WAYLAND_DISPLAY", "")
            if not re.fullmatch(r"wayland-[0-9]+", display):
                return None
            display_path = Path(runtime_dir, display)
            try:
                if not stat.S_ISSOCK(display_path.stat().st_mode):
                    return None
            except OSError:
                return None
            environment["QT_QPA_PLATFORM"] = "wayland"
        else:
            display = environment.get("DISPLAY", "")
            if not re.fullmatch(r":[0-9]+(?:\.[0-9]+)?", display):
                return None
            environment["QT_QPA_PLATFORM"] = "xcb"
        return environment

    def agent_command(self, environment: dict[str, str]) -> list[str]:
        assignments = [f"{key}={value}" for key, value in sorted(environment.items())]
        return [
            RUNUSER,
            "-u",
            self.config.username,
            "--",
            ENV,
            "-i",
            *assignments,
            str(AGENT_PATH),
            "--lock-seconds",
            str(self.config.lock_seconds),
            "--shutdown-seconds",
            str(self.config.shutdown_seconds),
        ]

    def verified_session(self, session: Session) -> bool:
        return self.eligible(self.session_properties(session.identifier))

    def lock_session(self, session: Session) -> bool:
        if not self.verified_session(session):
            log("ignored LOCK from a session that is no longer eligible")
            return False
        result = self.command([LOGINCTL, "lock-session", session.identifier])
        if result.returncode != 0:
            log(f"lock-session failed: {result.stderr.strip() or result.returncode}")
            return False
        log(f"locked session {session.identifier} after {self.config.lock_seconds} seconds idle")
        return True

    def power_off(self, session: Session) -> bool:
        if not self.verified_session(session):
            log("ignored POWER_OFF from a session that is no longer eligible")
            return False
        result = self.command([SYSTEMCTL, "--no-block", "poweroff"])
        if result.returncode != 0:
            log(f"poweroff failed: {result.stderr.strip() or result.returncode}")
            return False
        log(f"poweroff requested after {self.config.shutdown_seconds} seconds idle")
        return True

    def handle_event(self, session: Session, line: str) -> str:
        if not line.startswith("CWS_EVENT "):
            log(f"agent[{session.identifier}]: {line}")
            return "continue"
        event = line.removeprefix("CWS_EVENT ")
        if event.startswith("READY "):
            log(f"agent ready for session {session.identifier}: {event.removeprefix('READY ')}")
        elif event == "LOCK":
            if not self.lock_session(session):
                return "restart"
        elif event == "POWER_OFF":
            return "poweroff" if self.power_off(session) else "restart"
        elif event == "RESUMED":
            log(f"input resumed; idle interval reset for session {session.identifier}")
        else:
            log(f"ignored unknown agent event: {event}")
        return "continue"

    @staticmethod
    def terminate_agent(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=5)

    def supervise_session(self, session: Session, environment: dict[str, str]) -> None:
        process = self.popen(
            self.agent_command(environment),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        if process.stdout is None:
            raise RuntimeError("agent stdout pipe was not created")
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            while not self.stopping and process.poll() is None:
                events = selector.select(timeout=10)
                if not events:
                    if not self.verified_session(session):
                        log(f"session {session.identifier} is no longer active")
                        break
                    continue
                line = process.stdout.readline()
                if not line:
                    break
                action = self.handle_event(session, line.rstrip("\n"))
                if action in {"restart", "poweroff"}:
                    break
        finally:
            selector.close()
            self.terminate_agent(process)
        if process.returncode not in {None, 0, -signal.SIGTERM, -signal.SIGKILL}:
            log(f"agent exited with status {process.returncode}")

    def serve(self) -> None:
        log(
            f"policy active for {self.config.username}: "
            f"lock={self.config.lock_seconds}s poweroff={self.config.shutdown_seconds}s"
        )
        while not self.stopping:
            session = self.find_session()
            if session is None:
                self.sleep(10)
                continue
            environment = self.user_environment(session)
            if environment is None:
                log(f"graphical environment is not ready for session {session.identifier}")
                self.sleep(10)
                continue
            log(f"starting KDE idle event agent for session {session.identifier}")
            self.supervise_session(session, environment)
            if not self.stopping:
                self.sleep(2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-config", type=Path, help="validate a config without starting")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.check_config:
        read_config(arguments.check_config, require_root_owner=False, verify_account=False)
        print("configuration: PASS")
        return 0
    if os.geteuid() != 0:
        print("idle supervisor must run as root", file=sys.stderr)
        return 1
    try:
        config = read_config()
    except ConfigurationError as error:
        print(f"invalid idle policy: {error}", file=sys.stderr)
        return 1

    supervisor = Supervisor(config)

    def stop(_signum: int, _frame: object) -> None:
        supervisor.stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    supervisor.serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
