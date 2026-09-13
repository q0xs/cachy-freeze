from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(os.environ.get("CWS_IDLE_TEST_AGENT"), "Run workstation/tests/static.sh")
class IdleAgentStartupTests(unittest.TestCase):
    def test_readonly_home_reaches_ready_without_kde_warning(self) -> None:
        self.assertNotEqual(
            os.geteuid(), 0, "The read-only configuration test must be unprivileged"
        )
        with tempfile.TemporaryDirectory(prefix="cachy-idle-startup-") as directory:
            root = Path(directory)
            config = root / "config"
            config.mkdir(mode=0o500)
            (root / "bin").mkdir()
            (root / "runtime").mkdir(mode=0o700)
            warning = root / "warning"
            # Observe dialog attempts without displaying or blocking on a real dialog.
            kdialog = root / "bin/kdialog"
            kdialog.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CWS_TEST_WARNING"\n')
            kdialog.chmod(0o755)
            environment = {
                "HOME": str(root),
                "PATH": f"{root / 'bin'}:/usr/bin",
                "XDG_CONFIG_HOME": str(config),
                "XDG_CACHE_HOME": str(root / "cache"),
                "XDG_DATA_HOME": str(root / "data"),
                "XDG_RUNTIME_DIR": str(root / "runtime"),
                "XDG_CURRENT_DESKTOP": "KDE",
                "KDE_FULL_SESSION": "true",
                "QT_QPA_PLATFORM": "offscreen",
                "QT_QPA_PLATFORMTHEME": "kde",
                "CWS_TEST_WARNING": str(warning),
            }
            try:
                # Only the event agent runs. No supervisor, lock or poweroff command
                # is connected, and the production intervals remain unchanged.
                with subprocess.Popen(
                    [
                        os.environ["CWS_IDLE_TEST_AGENT"],
                        "--lock-seconds",
                        "3600",
                        "--shutdown-seconds",
                        "7200",
                    ],
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                ) as process:
                    try:
                        stdout, stderr = process.communicate(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        stdout, stderr = process.communicate(timeout=5)
                    self.assertIn("CWS_EVENT READY ", stdout, stderr)
                self.assertFalse(warning.exists(), warning.read_text() if warning.exists() else "")
                self.assertEqual(list(config.iterdir()), [])
            finally:
                config.chmod(0o700)


if __name__ == "__main__":
    unittest.main()
