"""Verification of workstation applications and reviewed policy artifacts."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .errors import IntegrityError
from .runner import CommandRunner

COMMANDS = {
    "Google Chrome": "google-chrome-stable",
    "Slack": "slack",
    "Wine": "wine",
    "LibreOffice": "libreoffice",
    "Zoiper": "zoiper",
    "AnyDesk": "anydesk",
    "X virtual framebuffer": "xvfb-run",
    "Archive extractor": "unzip",
    "Template synchronizer": "rsync",
    "User session launcher": "runuser",
}


class ApplicationVerifier:
    def __init__(
        self,
        runner: CommandRunner,
        *,
        which: Callable[[str], str | bytes | Path | None] = shutil.which,
        chrome_check: Callable[[], dict[str, Any]] | None = None,
        microsip_check: Callable[[Path], dict[str, Any]] | None = None,
    ) -> None:
        self.runner = runner
        self.which = which
        self.chrome_check = chrome_check or self.chrome_policy_status
        self.microsip_check = microsip_check or self.microsip_status

    def status(self) -> dict[str, Any]:
        applications = [
            {"name": name, "installed": self.which(command) is not None}
            for name, command in COMMANDS.items()
        ]
        anydesk_active = (
            self.runner.run(
                ["systemctl", "is-active", "--quiet", "anydesk.service"], check=False
            ).returncode
            == 0
        )
        applications.append(
            {
                "name": "AnyDesk background service",
                "installed": anydesk_active,
                "active": anydesk_active,
            }
        )
        applications.append(self.chrome_check())
        applications.append(self.microsip_check(Path("/opt/company/microsip")))
        return {
            "applications": applications,
            "all_installed": all(item["installed"] for item in applications),
        }

    @staticmethod
    def chrome_policy_status(
        installed: Path = Path("/etc/opt/chrome/policies/managed/company.json"),
        expected: Path = Path("/usr/lib/cachy-freeze/deployment/policies/chrome/managed.json"),
    ) -> dict[str, Any]:
        valid = False
        try:
            installed_document = json.loads(installed.read_text(encoding="utf-8"))
            expected_document = json.loads(expected.read_text(encoding="utf-8"))
            valid = isinstance(installed_document, dict) and installed_document == expected_document
        except (OSError, json.JSONDecodeError):
            pass
        return {"name": "Managed Chrome policy", "installed": valid, "valid": valid}

    @staticmethod
    def microsip_status(microsip_root: Path) -> dict[str, Any]:
        microsip_valid = False
        microsip_version = ""
        try:
            archive_name = (microsip_root / "CURRENT").read_text(encoding="utf-8").strip()
            if (
                Path(archive_name).name != archive_name
                or re.fullmatch(r"MicroSIP-[0-9]+(?:\.[0-9]+)+\.zip", archive_name) is None
            ):
                raise IntegrityError("MicroSIP CURRENT contains an invalid filename")
            checksum_line = (microsip_root / "SHA256SUMS").read_text(encoding="utf-8").strip()
            expected, recorded_name = checksum_line.split(None, 1)
            metadata = json.loads((microsip_root / "metadata.json").read_text(encoding="utf-8"))
            archive = microsip_root / archive_name
            archive_size = archive.stat().st_size
            digest = hashlib.sha256()
            with archive.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            with zipfile.ZipFile(archive) as bundle:
                executable_names = [
                    name
                    for name in bundle.namelist()
                    if Path(name).name.casefold() == "microsip.exe"
                ]
                if len(executable_names) != 1 or executable_names[0].casefold() != "microsip.exe":
                    raise IntegrityError(
                        "MicroSIP archive does not contain exactly one root executable"
                    )
                executable_digest = hashlib.sha256()
                with bundle.open(executable_names[0]) as executable:
                    for block in iter(lambda: executable.read(1024 * 1024), b""):
                        executable_digest.update(block)
            source_url = metadata.get("source_url")
            executable_checksum = metadata.get("executable_sha256")
            microsip_valid = (
                metadata.get("schema") == 1
                and recorded_name.strip() == archive_name
                and re.fullmatch(r"[0-9a-f]{64}", expected) is not None
                and digest.hexdigest() == expected
                and metadata.get("archive_sha256") == expected
                and isinstance(executable_checksum, str)
                and executable_digest.hexdigest() == executable_checksum
                and isinstance(source_url, str)
                and source_url.startswith("https://www.microsip.org/download/")
                and 1_048_576 <= archive_size <= 104_857_600
            )
            microsip_version = archive_name.removeprefix("MicroSIP-").removesuffix(".zip")
        except (
            OSError,
            ValueError,
            IntegrityError,
            json.JSONDecodeError,
            zipfile.BadZipFile,
        ):
            pass
        return {
            "name": "MicroSIP",
            "installed": microsip_valid,
            "version": microsip_version,
            "checksum_valid": microsip_valid,
        }
