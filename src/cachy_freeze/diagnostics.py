"""Privacy-preserving diagnostic bundle generation."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import tempfile
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import CachyFreezeError
from .runner import CommandRunner
from .versioning import APP_VERSION

try:
    import pwd
except ImportError:  # pragma: no cover - Windows-only test compatibility
    pwd = None  # type: ignore[assignment]


_UUID_RE = re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
_MAC_RE = re.compile(r"(?i)\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b")
_IPV4_RE = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")
_IPV6_CANDIDATE_RE = re.compile(
    r"(?i)(?<![0-9a-f:])(?:[0-9a-f]{0,4}:){2,8}[0-9a-f]{0,4}"
    r"(?:%[A-Za-z0-9_.-]+)?(?![0-9a-f:])"
)
_HOME_RE = re.compile(r"/home/[A-Za-z_][A-Za-z0-9_.-]*")
_DEVICE_RE = re.compile(r"/dev/(?:disk/[^\s,;]+|[A-Za-z0-9_.-]+)")
_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|passwd|secret|token|authorization|cookie|api[_-]?key|"
    r"access[_-]?key|client[_-]?secret)\b(\s*[:=]\s*)"
    r"(?:\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;]+)"
)
_BEARER_RE = re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]+")
_SENSITIVE_KEY_RE = re.compile(
    r"(?i)(?:password|passwd|secret|token|authorization|cookie|hash|uuid|boot_id|"
    r"expected_user|requester|created_by|username|uid)"
)
_JOURNAL_UNITS = (
    "cachy-freeze-finalize.service",
    "cachy-freeze-boot-health.service",
    "cachy-employee-reset.service",
    "cachy-frozen-admin-restrict.service",
    "cachy-freeze-idle-power.service",
)


class DiagnosticBundleBuilder:
    """Collect bounded support data while removing device and identity data."""

    def __init__(
        self,
        *,
        state_dir: Path,
        export_dir: Path,
        log_file: Path,
        runner: CommandRunner | None = None,
    ) -> None:
        self.state_dir = state_dir
        self.export_dir = export_dir
        self.log_file = log_file
        self.runner = runner or CommandRunner()
        self.identities = self._local_identities()

    @staticmethod
    def _local_identities() -> set[str]:
        if pwd is None:
            return set()
        return {
            account.pw_name
            for account in pwd.getpwall()
            if account.pw_name == "localadm" or 1000 <= account.pw_uid < 65534
        }

    def _redact_text(self, value: str) -> str:
        def redact_ipv6(match: re.Match[str]) -> str:
            candidate = match.group(0)
            address = candidate.split("%", 1)[0]
            try:
                ipaddress.IPv6Address(address)
            except ValueError:
                return candidate
            return "<redacted-address>"

        value = _BEARER_RE.sub(r"\1 <redacted>", value)
        value = _SENSITIVE_ASSIGNMENT_RE.sub(r"\1\2<redacted>", value)
        value = _UUID_RE.sub("<redacted-uuid>", value)
        value = _MAC_RE.sub("<redacted-mac>", value)
        value = _IPV4_RE.sub("<redacted-address>", value)
        value = _IPV6_CANDIDATE_RE.sub(redact_ipv6, value)
        value = _HOME_RE.sub("/home/<redacted-user>", value)
        value = _DEVICE_RE.sub("<redacted-device>", value)
        for identity in sorted(self.identities, key=len, reverse=True):
            value = re.sub(
                rf"(?<![A-Za-z0-9_-]){re.escape(identity)}(?![A-Za-z0-9_-])",
                "<redacted-user>",
                value,
            )
        return value

    def redact(self, value: Any, *, key: str = "") -> Any:
        if _SENSITIVE_KEY_RE.search(key):
            return "<redacted>"
        if isinstance(value, dict):
            return {
                str(item_key): self.redact(item, key=str(item_key))
                for item_key, item in value.items()
            }
        if isinstance(value, list | tuple):
            return [self.redact(item, key=key) for item in value]
        if isinstance(value, str):
            return self._redact_text(value)
        return value

    def _command_output(self, command: list[str], *, limit: int = 262_144) -> str:
        completed = self.runner.run(command, check=False)
        raw = (completed.stdout or b"").decode("utf-8", errors="replace")
        return self._redact_text(raw[-limit:])

    def _audit_tail(self, *, lines: int = 500, byte_limit: int = 1_048_576) -> str:
        try:
            with self.log_file.open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                handle.seek(max(0, size - byte_limit))
                raw_lines = handle.read().decode("utf-8", errors="replace").splitlines()
        except OSError:
            return ""
        result: list[str] = []
        for raw_line in raw_lines[-lines:]:
            try:
                value = self.redact(json.loads(raw_line))
                result.append(json.dumps(value, ensure_ascii=False, sort_keys=True))
            except json.JSONDecodeError:
                result.append(self._redact_text(raw_line))
        return "\n".join(result) + ("\n" if result else "")

    def build(self, status: dict[str, Any]) -> dict[str, Any]:
        self.export_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.export_dir, 0o700)
        created_at = datetime.now(UTC)
        filename = (
            f"cachy-freeze-diagnostics-{created_at.strftime('%Y%m%dT%H%M%SZ')}-"
            f"{uuid.uuid4().hex[:8]}.zip"
        )
        destination = self.export_dir / filename
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{filename}.", suffix=".tmp", dir=self.export_dir
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        report = {
            "schema": 1,
            "application_version": APP_VERSION,
            "created_at": created_at.isoformat(),
            "privacy": "Device identifiers, account identities, addresses, and secrets redacted.",
            "status": self.redact(status),
            "system": {
                "kernel": self._command_output(["uname", "-srvmo"], limit=4096).strip(),
                "os_release": self._command_output(
                    ["systemd-analyze", "cat-config", "systemd/os-release"], limit=16_384
                ),
            },
        }
        try:
            with zipfile.ZipFile(
                temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
            ) as archive:
                archive.writestr(
                    "report.json",
                    json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                )
                audit = self._audit_tail()
                if audit:
                    archive.writestr("audit-redacted.jsonl", audit)
                for unit in _JOURNAL_UNITS:
                    journal = self._command_output(
                        [
                            "journalctl",
                            "--boot",
                            "--no-pager",
                            "--output=short-monotonic",
                            "--lines=400",
                            "--unit",
                            unit,
                        ]
                    )
                    archive.writestr(f"journal/{unit}.log", journal)
            os.chmod(temporary, 0o600)
            os.replace(temporary, destination)
        except (OSError, zipfile.BadZipFile) as error:
            raise CachyFreezeError(f"Diagnostic bundle could not be created: {error}") from error
        finally:
            temporary.unlink(missing_ok=True)
        return {
            "filename": filename,
            "path": str(destination),
            "redacted": True,
            "created_at": created_at.isoformat(),
        }
