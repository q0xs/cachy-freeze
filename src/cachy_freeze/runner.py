"""Safe subprocess execution and process-level locking."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import IO

from .errors import CommandError

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows-only test compatibility
    fcntl = None  # type: ignore[assignment]


class CommandRunner:
    def __init__(self) -> None:
        self.environment = {
            "LC_ALL": "C",
            "LANG": "C",
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/bin:/usr/sbin",
            "SYSTEMD_COLORS": "0",
        }

    def run(
        self,
        command: Iterable[str],
        *,
        check: bool = True,
        stdin: IO[bytes] | None = None,
        input_data: bytes | None = None,
        stdout: IO[bytes] | int | None = subprocess.PIPE,
    ) -> subprocess.CompletedProcess[bytes]:
        if stdin is not None and input_data is not None:
            raise ValueError("stdin and input_data cannot be used together")
        arguments = [str(part) for part in command]
        completed = subprocess.run(
            arguments,
            check=False,
            env=self.environment,
            stdin=stdin,
            input=input_data,
            stdout=stdout,
            stderr=subprocess.PIPE,
        )
        if check and completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace")
            raise CommandError(arguments, completed.returncode, detail)
        return completed

    def text(self, command: Iterable[str], *, check: bool = True) -> str:
        completed = self.run(command, check=check)
        return (completed.stdout or b"").decode("utf-8", errors="replace").strip()


class ProcessLock(AbstractContextManager["ProcessLock"]):
    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle: IO[str] | None = None

    def __enter__(self) -> ProcessLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_APPEND | os.O_CREAT
        flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(self.path, flags, 0o600)
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)
        self._handle = os.fdopen(descriptor, "a+", encoding="utf-8")
        if fcntl is not None:
            try:
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise CommandError(
                    ["cachy-freeze"], 75, "Another operation is already running"
                ) from error
        return self

    def __exit__(self, *args: object) -> None:
        if self._handle is not None:
            if fcntl is not None:
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            self._handle.close()
            self._handle = None
