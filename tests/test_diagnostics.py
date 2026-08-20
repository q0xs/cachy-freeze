from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from cachy_freeze.diagnostics import DiagnosticBundleBuilder


class FakeRunner:
    def run(self, command: list[str], **_: object):
        output = ""
        if command[0] == "uname":
            output = "Linux 6.18 test-host /dev/nvme0n1p2 10.20.30.40\n"
        elif command[0] == "journalctl":
            output = (
                "user=person_01 home=/home/person_01 "
                "uuid=12345678-1234-1234-1234-123456789abc "
                "address=2001:db8::25 token=journal-secret "
                "Authorization: Bearer bearer-secret\n"
            )
        return subprocess.CompletedProcess(command, 0, stdout=output.encode(), stderr=b"")


class DiagnosticBundleTests(unittest.TestCase):
    def test_bundle_is_private_bounded_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_file = root / "audit.jsonl"
            log_file.write_text(
                json.dumps(
                    {
                        "message": "Account person_01 at /home/person_01",
                        "context": {
                            "password": "never-export-this",
                            "btrfs_uuid": "12345678-1234-1234-1234-123456789abc",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            builder = DiagnosticBundleBuilder(
                state_dir=root / "state",
                export_dir=root / "exports",
                log_file=log_file,
                runner=FakeRunner(),  # type: ignore[arg-type]
            )
            with patch.object(builder, "identities", {"person_01"}):
                result = builder.build(
                    {
                        "created_by": "person_01",
                        "root": "/dev/nvme0n1p2",
                        "address": "10.20.30.40",
                    }
                )
            destination = Path(result["path"])
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
            with zipfile.ZipFile(destination) as archive:
                names = archive.namelist()
                self.assertIn("report.json", names)
                self.assertIn("audit-redacted.jsonl", names)
                content = "\n".join(
                    archive.read(name).decode("utf-8", errors="replace") for name in names
                )
            for secret in (
                "never-export-this",
                "person_01",
                "/home/person_01",
                "/dev/nvme0n1p2",
                "10.20.30.40",
                "2001:db8::25",
                "journal-secret",
                "bearer-secret",
                "12345678-1234-1234-1234-123456789abc",
            ):
                self.assertNotIn(secret, content)
            self.assertIn("<redacted", content)


if __name__ == "__main__":
    unittest.main()
