from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from cachy_freeze.config import Config
from cachy_freeze.engine import FreezeEngine


class ServiceRunner:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        self.commands: list[list[str]] = []

    def run(
        self, command: list[str], *, check: bool = True, **_kwargs: object
    ) -> CompletedProcess[bytes]:
        self.commands.append(command)
        return CompletedProcess(command, self.returncode, b"", b"")


class ApplicationVerificationTests(unittest.TestCase):
    def test_application_status_requires_running_anydesk_service(self) -> None:
        for returncode, expected in ((0, True), (3, False)):
            with self.subTest(returncode=returncode):
                runner = ServiceRunner(returncode)
                with (
                    patch.object(FreezeEngine, "require_root"),
                    patch("cachy_freeze.engine.shutil.which", return_value=Path("/bin/tool")),
                    patch.object(
                        FreezeEngine,
                        "_chrome_policy_status",
                        return_value={"name": "policy", "installed": True},
                    ),
                    patch.object(
                        FreezeEngine,
                        "_microsip_status",
                        return_value={"name": "microsip", "installed": True},
                    ),
                ):
                    status = FreezeEngine(
                        Config(),
                        runner=runner,  # type: ignore[arg-type]
                        logger=None,
                    ).application_status()

                service = next(
                    item
                    for item in status["applications"]
                    if item["name"] == "AnyDesk background service"
                )
                self.assertEqual(service["installed"], expected)
                self.assertEqual(service["active"], expected)
                self.assertEqual(status["all_installed"], expected)
                self.assertEqual(
                    runner.commands,
                    [["systemctl", "is-active", "--quiet", "anydesk.service"]],
                )

    def test_incremental_send_dump_extracts_changed_and_renamed_paths(self) -> None:
        output = """\
mkfile          ./snap-new/etc/new-file
rename          ./snap-new/o123-4-0 dest=./snap-new/etc/renamed-file
chmod           ./snap-new/etc/new-file mode=600
utimes          ./different-snapshot/ignored
"""

        self.assertEqual(
            FreezeEngine._changed_paths_from_send_dump(output, "snap-new"),
            ["etc/new-file", "etc/renamed-file"],
        )

    def _microsip_bundle(self, root: Path) -> tuple[Path, dict[str, object]]:
        root.mkdir()
        archive = root / "MicroSIP-3.22.3.zip"
        executable = os.urandom(1_100_000)
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
            bundle.writestr("MicroSIP.exe", executable)
        archive_checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        metadata: dict[str, object] = {
            "schema": 1,
            "source_url": "https://www.microsip.org/download/MicroSIP-3.22.3.zip",
            "archive_sha256": archive_checksum,
            "executable_sha256": hashlib.sha256(executable).hexdigest(),
        }
        (root / "CURRENT").write_text(f"{archive.name}\n", encoding="utf-8")
        (root / "SHA256SUMS").write_text(f"{archive_checksum}  {archive.name}\n", encoding="utf-8")
        (root / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        return archive, metadata

    def test_microsip_bundle_verifies_archive_and_executable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "microsip"
            self._microsip_bundle(root)

            result = FreezeEngine._microsip_status(root)

            self.assertTrue(result["installed"])
            self.assertTrue(result["checksum_valid"])
            self.assertEqual(result["version"], "3.22.3")

    def test_microsip_bundle_rejects_tampered_executable_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "microsip"
            _archive, metadata = self._microsip_bundle(root)
            metadata["executable_sha256"] = "0" * 64
            (root / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

            result = FreezeEngine._microsip_status(root)

            self.assertFalse(result["installed"])
            self.assertFalse(result["checksum_valid"])

    def test_microsip_bundle_rejects_nested_or_duplicate_executable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "microsip"
            archive, metadata = self._microsip_bundle(root)
            with zipfile.ZipFile(archive, "a", compression=zipfile.ZIP_STORED) as bundle:
                bundle.writestr("nested/MicroSIP.exe", b"duplicate")
            archive_checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
            metadata["archive_sha256"] = archive_checksum
            (root / "SHA256SUMS").write_text(
                f"{archive_checksum}  {archive.name}\n", encoding="utf-8"
            )
            (root / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

            self.assertFalse(FreezeEngine._microsip_status(root)["installed"])

    def test_chrome_policy_must_match_reviewed_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root / "installed.json"
            expected = root / "expected.json"
            expected.write_text('{"HomepageLocation":"https://example.invalid"}', encoding="utf-8")
            installed.write_text(expected.read_text(encoding="utf-8"), encoding="utf-8")

            self.assertTrue(FreezeEngine._chrome_policy_status(installed, expected)["installed"])
            installed.write_text("{}", encoding="utf-8")
            self.assertFalse(FreezeEngine._chrome_policy_status(installed, expected)["installed"])


if __name__ == "__main__":
    unittest.main()
