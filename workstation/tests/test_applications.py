from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class SlackProvisioningTests(unittest.TestCase):
    def run_shell(self, script: str, directory: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", "-euo", "pipefail", "-c", script],
            env={
                **os.environ,
                "CWS_PROJECT_ROOT": str(ROOT),
                "TEST_ROOT": directory,
            },
            capture_output=True,
            text=True,
            check=False,
        )

    def test_slack_install_requires_package_and_executable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "slack"
            binary.write_text("#!/bin/sh\nexit 0\n")
            binary.chmod(0o755)
            result = self.run_shell(
                """
source "$CWS_PROJECT_ROOT/workstation/lib/packages.sh"
ensure_package() { [[ $1 == slack-desktop ]]; }
fail() { return 1; }
PATH="$TEST_ROOT"
install_slack
""",
                directory,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            binary.unlink()
            result = self.run_shell(
                """
source "$CWS_PROJECT_ROOT/workstation/lib/packages.sh"
ensure_package() { [[ $1 == slack-desktop ]]; }
fail() { return 1; }
PATH="$TEST_ROOT"
install_slack
""",
                directory,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_slack_package_failure_is_propagated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_shell(
                """
source "$CWS_PROJECT_ROOT/workstation/lib/packages.sh"
ensure_package() { return 1; }
install_slack
""",
                directory,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_install_and_repair_slack_launchers_and_reject_missing_shortcut(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_shell(
                """
exec 3>/dev/null
source "$CWS_PROJECT_ROOT/workstation/lib/common.sh"
source "$CWS_PROJECT_ROOT/workstation/lib/user.sh"
source "$CWS_PROJECT_ROOT/workstation/lib/health.sh"
TARGET_HOME="$TEST_ROOT/home"
TARGET_DESKTOP="$TARGET_HOME/Masaustu"
TARGET_UID=$(id -u)
TARGET_GID=$(id -g)
TARGET_USER=testemployee
mkdir -p "$TARGET_HOME"
# Replace only privileged staging/identity operations; install and validation
# still operate on real files as the unprivileged test account.
mktemp() { command mktemp -d "$TEST_ROOT/launchers.XXXXXXXX"; }
install() {
  if [[ ${1:-} == -o ]]; then shift 4; fi
  command install "$@"
}
run_as_target() { "$@"; }
install_microsip_wrapper() { :; }
install_user_launchers
check_launcher_set
test -x "$TARGET_DESKTOP/Slack.desktop"
rm "$TARGET_DESKTOP/Slack.desktop"
if check_launcher_set; then exit 10; fi
install_user_launchers
check_launcher_set
""",
                directory,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            desktop = Path(directory) / "home/Masaustu/Slack.desktop"
            menu = (
                Path(directory) / "home/.local/share/applications/cachy-workstation-slack.desktop"
            )
            template = ROOT / "workstation/assets/desktop/slack.desktop"
            self.assertEqual(desktop.read_bytes(), template.read_bytes())
            self.assertEqual(menu.read_bytes(), template.read_bytes())

    def test_health_report_requires_slack(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_shell(
                """
source "$CWS_PROJECT_ROOT/workstation/lib/health.sh"
TARGET_USER=testemployee
log_event() { :; }
health_assert() {
  if [[ $2 == check_slack ]]; then health_fail "$1"; else health_pass "$1"; fi
}
run_health_check
""",
                directory,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Slack package and executable", result.stdout)
            self.assertIn("Ready for freeze: NO", result.stdout)

    def test_slack_dependencies_are_in_provisioned_runtime(self) -> None:
        result = self.run_shell(
            """
source "$CWS_PROJECT_ROOT/workstation/lib/packages.sh"
printf '%s\\n' "${CWS_BASE_PACKAGES[@]}" "${CWS_APP_RUNTIME_PACKAGES[@]}"
""",
            "/tmp",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        source = ROOT / "workstation/vendor/aur/slack-desktop/.SRCINFO"
        dependencies = {
            line.partition(" = ")[2]
            for line in source.read_text().splitlines()
            if line.startswith("\tdepends = ")
        }
        self.assertTrue(dependencies <= set(result.stdout.splitlines()))


if __name__ == "__main__":
    unittest.main()
