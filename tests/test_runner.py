from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cachy_freeze.runner import CommandRunner, ProcessLock


class CommandRunnerTests(unittest.TestCase):
    @patch("cachy_freeze.runner.subprocess.run")
    def test_binary_input_is_forwarded_without_a_file_descriptor(self, run) -> None:
        run.return_value = subprocess.CompletedProcess(["chpasswd"], 0, b"", b"")

        CommandRunner().run(["chpasswd"], input_data=b"person:secret\n")

        self.assertEqual(run.call_args.kwargs["input"], b"person:secret\n")
        self.assertIsNone(run.call_args.kwargs["stdin"])

    def test_stream_and_binary_input_are_mutually_exclusive(self) -> None:
        with self.assertRaises(ValueError):
            CommandRunner().run(["unused"], stdin=subprocess.PIPE, input_data=b"secret")

    def test_privileged_command_environment_is_allow_listed(self) -> None:
        self.assertEqual(
            set(CommandRunner().environment),
            {"LANG", "LC_ALL", "PATH", "SYSTEMD_COLORS"},
        )

    def test_process_lock_does_not_follow_symlinks(self) -> None:
        if not hasattr(os, "O_NOFOLLOW"):
            self.skipTest("O_NOFOLLOW is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_text("unchanged", encoding="utf-8")
            (root / "lock").symlink_to(target)
            with self.assertRaises(OSError), ProcessLock(root / "lock"):
                pass
            self.assertEqual(target.read_text(encoding="utf-8"), "unchanged")


if __name__ == "__main__":
    unittest.main()
