from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cachy_freeze.catalog import AuditLogger
from cachy_freeze.errors import CachyFreezeError
from cachy_freeze.users import UserManager


class UserValidationTests(unittest.TestCase):
    def test_username_contract(self) -> None:
        self.assertEqual(UserManager.validate_username("person_01"), "person_01")
        for invalid in ("LocalAdm", "1person", "bad.name", "../root"):
            with self.subTest(invalid=invalid), self.assertRaises(CachyFreezeError):
                UserManager.validate_username(invalid)

    def test_password_policy(self) -> None:
        UserManager.validate_password("1234")
        UserManager.validate_password("x" * 256)
        for invalid in (
            "123",
            "x" * 257,
            "Colon:Password42",
            "line\nbreak",
            "carriage\rreturn",
            "null\x00byte",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(CachyFreezeError):
                UserManager.validate_password(invalid)

    def test_new_username_and_display_name_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = UserManager(
                state_dir=root / "state",
                lock_file=root / "operation.lock",
                logger=AuditLogger(root / "audit.jsonl"),
            )
            invalid_values = (
                ("a", "Person"),
                ("a" * 32, "Person"),
                ("person01", ""),
                ("person01", "Name:Field"),
                ("person01", "x" * 101),
            )
            for username, display_name in invalid_values:
                with (
                    self.subTest(username=username, display_name=display_name),
                    patch.object(manager, "require_root"),
                    self.assertRaises(CachyFreezeError),
                ):
                    manager.create(username, display_name, "1234")

    def test_new_account_requires_normal_login_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = UserManager(
                state_dir=root / "state",
                lock_file=root / "operation.lock",
                logger=AuditLogger(root / "audit.jsonl"),
            )
            for invalid in ("a", "_service"):
                with (
                    self.subTest(invalid=invalid),
                    patch.object(manager, "require_root"),
                    self.assertRaises(CachyFreezeError),
                ):
                    manager.create(invalid, "Invalid User", "1234")

    def test_plasma_login_selection_requires_password_and_preserves_main_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager_unit = root / "plasmalogin.service"
            manager_unit.touch()
            display_manager = root / "display-manager.service"
            display_manager.symlink_to(manager_unit)
            main_config = root / "plasmalogin.conf"
            main_config.write_text(
                "# preserved comment\n[Autologin]\nSession=plasma\n\n[General]\nNamespaces=\n",
                encoding="utf-8",
            )
            original = main_config.read_text(encoding="utf-8")
            config = root / "plasmalogin.conf.d" / "90-cachy-freeze-autologin.conf"
            login_state = root / "plasmalogin" / "plasma-login-greeterstaterc"
            login_state.parent.mkdir()
            login_state.write_text(
                "[General]\nLastLoggedInSession=plasma.desktop\nLastLoggedInUser=localadm\n",
                encoding="utf-8",
            )
            manager = UserManager(
                state_dir=root / "state",
                lock_file=root / "operation.lock",
                logger=AuditLogger(root / "audit.jsonl"),
                display_manager_path=display_manager,
                plasmalogin_path=config,
                sddm_path=root / "sddm.conf",
                login_state_path=login_state,
            )

            self.assertEqual(manager.autologin_kind, "plasmalogin-drop-in")
            with (
                patch.object(manager, "require_root"),
                patch.object(manager, "_account", return_value=SimpleNamespace()),
                patch.object(manager, "_is_administrator", return_value=False),
            ):
                result = manager.set_autologin("person_01")
            disabled = config.read_text(encoding="utf-8")
            self.assertEqual(
                disabled,
                "[Autologin]\nUser=\nSession=plasma\nRelogin=false\n",
            )
            state = login_state.read_text(encoding="utf-8")
            self.assertIn("LastLoggedInUser=person_01", state)
            self.assertIn("LastLoggedInSession=plasma.desktop", state)
            self.assertTrue(result["password_required"])
            self.assertEqual(main_config.read_text(encoding="utf-8"), original)
            self.assertIsNone(manager._autologin_user())
            self.assertEqual(manager.preferred_login_user(), "person_01")

    def test_sddm_login_selection_removes_owned_autologin_drop_in(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "cachy-autologin.conf"
            manager = UserManager(
                state_dir=root / "state",
                lock_file=root / "operation.lock",
                logger=AuditLogger(root / "audit.jsonl"),
                autologin_path=config,
            )

            config.parent.mkdir(parents=True, exist_ok=True)
            config.write_text(
                "[Autologin]\nUser=person_01\nSession=plasma.desktop\nRelogin=true\n",
                encoding="utf-8",
            )
            with (
                patch.object(manager, "require_root"),
                patch.object(manager, "_account", return_value=SimpleNamespace()),
                patch.object(manager, "_is_administrator", return_value=False),
            ):
                manager.set_autologin("person_01")
            self.assertFalse(config.exists())
            state = manager.login_state_path.read_text(encoding="utf-8")
            self.assertIn("[Last]", state)
            self.assertIn("User=person_01", state)
            self.assertIn("Session=plasma.desktop", state)

    def test_finalization_adopts_and_disables_legacy_automatic_login(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "cachy-autologin.conf"
            config.write_text(
                "[Autologin]\nUser=person_01\nSession=plasma.desktop\nRelogin=true\n",
                encoding="utf-8",
            )
            manager = UserManager(
                state_dir=root / "state",
                lock_file=root / "operation.lock",
                logger=AuditLogger(root / "audit.jsonl"),
                autologin_path=config,
            )
            with (
                patch.object(manager, "require_root"),
                patch.object(manager, "_account", return_value=SimpleNamespace()),
                patch.object(manager, "_is_administrator", return_value=False),
            ):
                preferred = manager.prepare_login_for_finalization()

            self.assertEqual(preferred, "person_01")
            self.assertFalse(config.exists())
            self.assertEqual(manager.preferred_login_user(), "person_01")

    def test_finalization_restores_managed_home_from_clean_template(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "templates" / "person_01"
            home = root / "home" / "person_01"
            template.mkdir(parents=True)
            home.mkdir(parents=True)
            account = SimpleNamespace(pw_dir="/home/person_01", pw_uid=1001, pw_gid=1001)
            manager = UserManager(
                state_dir=root / "state",
                lock_file=root / "operation.lock",
                logger=AuditLogger(root / "audit.jsonl"),
                template_root=root / "templates",
            )
            with (
                patch.object(manager, "require_root"),
                patch.object(manager, "_account", return_value=account),
                patch("cachy_freeze.users.Path.is_dir", return_value=True),
                patch.object(manager.runner, "run") as run,
            ):
                restored = manager.restore_managed_homes()

            self.assertEqual(restored, ["person_01"])
            self.assertEqual(
                run.call_args_list[0].args[0],
                ["rsync", "-aHAX", "--delete", f"{template}/", "/home/person_01/"],
            )
            self.assertEqual(
                run.call_args_list[1].args[0],
                ["chown", "-R", "1001:1001", "/home/person_01"],
            )

    def test_encrypted_password_hash_uses_stdin_safe_payload(self) -> None:
        password_hash = "$y$j9T$example-salt$example-hash"
        self.assertEqual(
            UserManager._encrypted_password_payload("person_01", password_hash),
            f"person_01:{password_hash}\n".encode(),
        )
        for invalid in ("", "hash:field", "hash\nsecond-line", "hash\x00suffix"):
            with self.subTest(invalid=invalid), self.assertRaises(CachyFreezeError):
                UserManager._encrypted_password_payload("person_01", invalid)

    def test_restore_never_places_password_hash_in_process_arguments(self) -> None:
        class RecordingRunner:
            def __init__(self) -> None:
                self.calls: list[tuple[list[str], dict[str, object]]] = []

            def run(self, command: list[str], **kwargs: object) -> SimpleNamespace:
                arguments = list(command)
                self.calls.append((arguments, kwargs))
                return SimpleNamespace(returncode=0)

            def text(self, command: list[str], **_kwargs: object) -> str:
                self.calls.append((list(command), {"text": True}))
                return ""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir = root / "state"
            backup_id = "20260804T000000Z-1234abcd-person_01"
            backup_dir = state_dir / "user-backups" / backup_id
            backup_dir.mkdir(parents=True)
            password_hash = "$y$j9T$private-salt$private-hash"
            (backup_dir / "account.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "username": "person_01",
                        "uid": 1234,
                        "gid": 1234,
                        "home": "/home/person_01",
                        "shell": "/bin/bash",
                        "gecos": "Test Person",
                        "password_hash": password_hash,
                        "groups": ["person_01", "wheel", "sudo", "audio"],
                    }
                ),
                encoding="utf-8",
            )
            (backup_dir / "template.tar").touch()
            runner = RecordingRunner()
            manager = UserManager(
                state_dir=state_dir,
                lock_file=root / "operation.lock",
                logger=AuditLogger(root / "audit.jsonl"),
                runner=runner,  # type: ignore[arg-type]
                template_root=root / "templates",
            )
            restored_user = {"username": "person_01"}
            with (
                patch.object(manager, "require_root"),
                patch.object(manager, "_account", return_value=None),
                patch.object(manager, "list_users", return_value=[restored_user]),
            ):
                self.assertEqual(manager.restore(backup_id), restored_user)

            flattened_arguments = [part for command, _ in runner.calls for part in command]
            self.assertNotIn(password_hash, flattened_arguments)
            chpasswd_calls = [
                (command, kwargs)
                for command, kwargs in runner.calls
                if command == ["chpasswd", "--encrypted"]
            ]
            self.assertEqual(len(chpasswd_calls), 1)
            self.assertEqual(
                chpasswd_calls[0][1].get("input_data"),
                f"person_01:{password_hash}\n".encode(),
            )
            self.assertIn(
                ["usermod", "-aG", "wheel,sudo,audio", "person_01"],
                [c[0] for c in runner.calls],
            )

    def test_create_does_not_modify_group_membership(self) -> None:
        source = (Path(__file__).parents[1] / "src/cachy_freeze/users.py").read_text()
        self.assertNotIn('["gpasswd", "-d", username', source)

    def test_create_runs_verified_provisioner_before_capturing_template(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home" / "person_01"
            home.mkdir(parents=True)
            provisioner = root / "prepare-standard-user.sh"
            provisioner.touch()
            account = SimpleNamespace(pw_dir=str(home))
            manager = UserManager(
                state_dir=root / "state",
                lock_file=root / "operation.lock",
                logger=AuditLogger(root / "audit.jsonl"),
                template_root=root / "templates",
                provisioner_path=provisioner,
            )
            created_user = {"username": "person_01", "administrator": False}
            with (
                patch.object(manager, "require_root"),
                patch.object(manager, "_account", side_effect=[None, account]),
                patch.object(manager, "_set_password"),
                patch.object(manager, "_refresh_template") as refresh_template,
                patch.object(manager, "_is_administrator", return_value=False),
                patch.object(manager, "list_users", return_value=[created_user]),
                patch.object(manager.runner, "run") as run,
            ):
                self.assertEqual(manager.create("person_01", "Person One", "1234"), created_user)

            self.assertEqual(run.call_args_list[0].args[0][0], "useradd")
            self.assertEqual(
                run.call_args_list[1].args[0],
                ["bash", str(provisioner), "person_01"],
            )
            refresh_template.assert_called_once_with("person_01", home)

    def test_provisioning_failure_removes_partial_account(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provisioner = root / "prepare-standard-user.sh"
            provisioner.touch()
            account = SimpleNamespace(pw_dir=str(root / "home" / "person_01"))
            manager = UserManager(
                state_dir=root / "state",
                lock_file=root / "operation.lock",
                logger=AuditLogger(root / "audit.jsonl"),
                template_root=root / "templates",
                provisioner_path=provisioner,
            )
            with (
                patch.object(manager, "require_root"),
                patch.object(manager, "_account", side_effect=[None, account]),
                patch.object(manager, "_set_password"),
                patch.object(
                    manager.runner,
                    "run",
                    side_effect=[
                        SimpleNamespace(returncode=0),
                        RuntimeError("provision failed"),
                        None,
                    ],
                ) as run,
                self.assertRaisesRegex(RuntimeError, "provision failed"),
            ):
                manager.create("person_01", "Person One", "1234")

            self.assertEqual(run.call_args_list[-1].args[0], ["userdel", "--remove", "person_01"])

    def test_create_rejects_unexpected_administrator_membership(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home" / "person_01"
            home.mkdir(parents=True)
            provisioner = root / "prepare-standard-user.sh"
            provisioner.touch()
            account = SimpleNamespace(pw_dir=str(home))
            manager = UserManager(
                state_dir=root / "state",
                lock_file=root / "operation.lock",
                logger=AuditLogger(root / "audit.jsonl"),
                template_root=root / "templates",
                provisioner_path=provisioner,
            )
            with (
                patch.object(manager, "require_root"),
                patch.object(manager, "_account", side_effect=[None, account]),
                patch.object(manager, "_set_password"),
                patch.object(manager, "_is_administrator", return_value=True),
                patch.object(manager.runner, "run") as run,
                self.assertRaisesRegex(CachyFreezeError, "administrator membership"),
            ):
                manager.create("person_01", "Person One", "1234")

            self.assertEqual(run.call_args_list[-1].args[0], ["userdel", "--remove", "person_01"])

    def test_restore_rejects_mismatched_existing_primary_group(self) -> None:
        class GroupRunner:
            def __init__(self) -> None:
                self.calls: list[list[str]] = []

            def run(self, command: list[str], **_kwargs: object) -> SimpleNamespace:
                self.calls.append(list(command))
                return SimpleNamespace(returncode=0)

            def text(self, command: list[str], **_kwargs: object) -> str:
                self.calls.append(list(command))
                if command == ["getent", "group", "person_01"]:
                    return "person_01:x:9999:"
                return ""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backup_id = "20260804T000000Z-person_01"
            backup_dir = root / "state" / "user-backups" / backup_id
            backup_dir.mkdir(parents=True)
            (backup_dir / "account.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "username": "person_01",
                        "uid": 1234,
                        "gid": 1234,
                        "home": "/home/person_01",
                        "shell": "/bin/bash",
                        "gecos": "Person One",
                        "password_hash": "$y$j9T$salt$hash",
                        "groups": ["person_01", "audio"],
                    }
                ),
                encoding="utf-8",
            )
            runner = GroupRunner()
            manager = UserManager(
                state_dir=root / "state",
                lock_file=root / "operation.lock",
                logger=AuditLogger(root / "audit.jsonl"),
                runner=runner,  # type: ignore[arg-type]
                template_root=root / "templates",
            )
            with (
                patch.object(manager, "require_root"),
                patch.object(manager, "_account", return_value=None),
                self.assertRaisesRegex(CachyFreezeError, "primary group"),
            ):
                manager.restore(backup_id)

            self.assertFalse(any(command and command[0] == "useradd" for command in runner.calls))


if __name__ == "__main__":
    unittest.main()
