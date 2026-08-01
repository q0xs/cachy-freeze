from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from cachy_freeze.runner import CommandRunner


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


if __name__ == "__main__":
    unittest.main()
