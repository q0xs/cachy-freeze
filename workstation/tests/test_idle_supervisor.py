from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


def load_supervisor() -> ModuleType:
    source = Path(__file__).parents[1] / "idle" / "idle-supervisor.py"
    specification = importlib.util.spec_from_file_location("cachy_idle_supervisor", source)
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load idle supervisor")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


SUPERVISOR = load_supervisor()


class ConfigTests(unittest.TestCase):
    def write_config(self, contents: str, mode: int = 0o600) -> Path:
        temporary = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        self.addCleanup(lambda: os.unlink(temporary.name))
        with temporary:
            temporary.write(contents)
        os.chmod(temporary.name, mode)
        return Path(temporary.name)

    def test_valid_config(self) -> None:
        path = self.write_config(
            "TARGET_USER=wrw1166\n"
            "TARGET_UID=1001\n"
            "TARGET_GID=1001\n"
            "TARGET_HOME=/home/wrw1166\n"
            "LOCK_SECONDS=3600\n"
            "SHUTDOWN_SECONDS=7200\n"
        )
        config = SUPERVISOR.read_config(path, require_root_owner=False, verify_account=False)
        self.assertEqual(config.username, "wrw1166")
        self.assertEqual(config.lock_seconds, 3600)
        self.assertEqual(config.shutdown_seconds, 7200)

    def test_rejects_group_writable_config(self) -> None:
        path = self.write_config(
            "TARGET_USER=wrw1166\n"
            "TARGET_UID=1001\n"
            "TARGET_GID=1001\n"
            "TARGET_HOME=/home/wrw1166\n"
            "LOCK_SECONDS=3600\n"
            "SHUTDOWN_SECONDS=7200\n",
            mode=0o620,
        )
        with self.assertRaises(SUPERVISOR.ConfigurationError):
            SUPERVISOR.read_config(path, require_root_owner=False, verify_account=False)

    def test_rejects_shutdown_before_lock(self) -> None:
        path = self.write_config(
            "TARGET_USER=wrw1166\n"
            "TARGET_UID=1001\n"
            "TARGET_GID=1001\n"
            "TARGET_HOME=/home/wrw1166\n"
            "LOCK_SECONDS=7200\n"
            "SHUTDOWN_SECONDS=3600\n"
        )
        with self.assertRaises(SUPERVISOR.ConfigurationError):
            SUPERVISOR.read_config(path, require_root_owner=False, verify_account=False)

    def test_rejects_unknown_key(self) -> None:
        path = self.write_config(
            "TARGET_USER=wrw1166\n"
            "TARGET_UID=1001\n"
            "TARGET_GID=1001\n"
            "TARGET_HOME=/home/wrw1166\n"
            "LOCK_SECONDS=3600\n"
            "SHUTDOWN_SECONDS=7200\n"
            "COMMAND=/bin/false\n"
        )
        with self.assertRaises(SUPERVISOR.ConfigurationError):
            SUPERVISOR.read_config(path, require_root_owner=False, verify_account=False)

    def test_parser_accepts_standard_underscore_environment_key(self) -> None:
        values = SUPERVISOR._parse_key_values(
            "_JAVA_AWT_WM_NONREPARENTING=1\nWAYLAND_DISPLAY=wayland-0\n"
        )
        self.assertEqual(values["_JAVA_AWT_WM_NONREPARENTING"], "1")
        self.assertEqual(values["WAYLAND_DISPLAY"], "wayland-0")


class SupervisorEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = SUPERVISOR.Config("wrw1166", 1001, 1001, "/home/wrw1166", 3600, 7200)
        self.calls: list[list[str]] = []

        def fake_run(arguments: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            self.calls.append(list(arguments))
            if arguments[:2] == [SUPERVISOR.LOGINCTL, "show-session"]:
                return subprocess.CompletedProcess(
                    arguments,
                    0,
                    stdout=(
                        "Id=9\nName=wrw1166\nUser=1001\nClass=user\nActive=yes\n"
                        "Remote=no\nType=wayland\nState=active\nSeat=seat0\n"
                    ),
                    stderr="",
                )
            return subprocess.CompletedProcess(arguments, 0, stdout="", stderr="")

        self.supervisor = SUPERVISOR.Supervisor(self.config, run=fake_run)
        properties = self.supervisor.session_properties("9")
        if properties is None:
            raise AssertionError("fixture session was not parsed")
        self.session = SUPERVISOR.Session("9", properties)

    def test_lock_event_uses_loginctl_for_verified_session(self) -> None:
        result = self.supervisor.handle_event(self.session, "CWS_EVENT LOCK")
        self.assertEqual(result, "continue")
        self.assertIn([SUPERVISOR.LOGINCTL, "lock-session", "9"], self.calls)

    def test_poweroff_event_uses_system_level_systemctl(self) -> None:
        result = self.supervisor.handle_event(self.session, "CWS_EVENT POWER_OFF")
        self.assertEqual(result, "poweroff")
        self.assertIn([SUPERVISOR.SYSTEMCTL, "--no-block", "poweroff"], self.calls)

    def test_agent_command_has_both_timeouts_and_clean_environment(self) -> None:
        command = self.supervisor.agent_command(
            {
                "HOME": "/home/wrw1166",
                "XDG_RUNTIME_DIR": "/run/user/1001",
                "QT_QPA_PLATFORM": "wayland",
            }
        )
        self.assertEqual(
            command[:6], [SUPERVISOR.RUNUSER, "-u", "wrw1166", "--", SUPERVISOR.ENV, "-i"]
        )
        self.assertEqual(command[-4:], ["--lock-seconds", "3600", "--shutdown-seconds", "7200"])

    def test_ineligible_session_cannot_trigger_poweroff(self) -> None:
        self.supervisor.eligible = lambda _properties: False
        result = self.supervisor.handle_event(self.session, "CWS_EVENT POWER_OFF")
        self.assertEqual(result, "restart")
        self.assertNotIn([SUPERVISOR.SYSTEMCTL, "--no-block", "poweroff"], self.calls)


if __name__ == "__main__":
    unittest.main()
