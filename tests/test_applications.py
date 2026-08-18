from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from cachy_freeze.engine import FreezeEngine


class ApplicationVerificationTests(unittest.TestCase):
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
