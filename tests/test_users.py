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
        for invalid in ("123", "Colon:Password42"):
            with self.subTest(invalid=invalid), self.assertRaises(CachyFreezeError):
                UserManager.validate_password(invalid)

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
                return SimpleNamespace(returncode=1 if arguments[:2] == ["getent", "group"] else 0)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir = root / "state"
            backup_id = "20260804T000000Z-person_01"
            backup_dir = state_dir / "user-backups" / backup_id
            backup_dir.mkdir(parents=True)
            password_hash = "$y$j9T$private-salt$private-hash"
            (backup_dir / "account.json").write_text(
                json.dumps(
                    {
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


if __name__ == "__main__":
    unittest.main()
