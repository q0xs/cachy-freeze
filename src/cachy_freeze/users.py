"""Transactional local account management for the workstation GUI."""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .catalog import AuditLogger, atomic_json_write, atomic_text_write
from .errors import CachyFreezeError
from .runner import CommandRunner, ProcessLock

try:
    import pwd
except ImportError:  # pragma: no cover - Windows test host
    pwd = None  # type: ignore[assignment]

_USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,30}$")
_BACKUP_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-z_][a-z0-9_-]{0,30}$")


class UserManager:
    def __init__(
        self,
        *,
        state_dir: Path,
        lock_file: Path,
        logger: AuditLogger,
        runner: CommandRunner | None = None,
        autologin_path: Path = Path("/etc/sddm.conf.d/cachy-autologin.conf"),
        template_root: Path = Path("/var/lib/cachy-user-template"),
    ) -> None:
        self.state_dir = state_dir
        self.lock_file = lock_file
        self.logger = logger
        self.runner = runner or CommandRunner()
        self.autologin_path = autologin_path
        self.template_root = template_root

    @staticmethod
    def require_root() -> None:
        if os.geteuid() != 0:
            raise CachyFreezeError("Kullanıcı yönetimi root yetkisi gerektirir.")

    @staticmethod
    def validate_username(username: str) -> str:
        if not _USERNAME_RE.fullmatch(username):
            raise CachyFreezeError(
                "Kullanıcı adı küçük harf/rakam ile _, - işaretlerinden oluşmalıdır."
            )
        return username

    @staticmethod
    def validate_password(password: str) -> None:
        if not 4 <= len(password) <= 256:
            raise CachyFreezeError("Çalışan parolası 4-256 karakter olmalıdır.")
        if "\n" in password or "\r" in password or "\x00" in password or ":" in password:
            raise CachyFreezeError("Parola desteklenmeyen bir karakter içeriyor.")

    @staticmethod
    def _account(username: str) -> pwd.struct_passwd | None:
        if pwd is None:
            raise CachyFreezeError("Kullanıcı yönetimi yalnızca Linux üzerinde desteklenir.")
        try:
            return pwd.getpwnam(username)
        except KeyError:
            return None

    def _autologin_user(self) -> str | None:
        try:
            for line in self.autologin_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("User="):
                    value = line.split("=", 1)[1].strip()
                    return value or None
        except OSError:
            pass
        return None

    def list_users(self) -> list[dict[str, Any]]:
        self.require_root()
        if pwd is None:
            raise CachyFreezeError("Kullanıcı yönetimi yalnızca Linux üzerinde desteklenir.")
        autologin = self._autologin_user()
        result: list[dict[str, Any]] = []
        for account in pwd.getpwall():
            if account.pw_name != "localadm" and not 1000 <= account.pw_uid < 65534:
                continue
            status = self.runner.text(["passwd", "-S", account.pw_name], check=False).split()
            groups = self.runner.text(["id", "-nG", account.pw_name], check=False).split()
            result.append(
                {
                    "username": account.pw_name,
                    "display_name": account.pw_gecos.split(",", 1)[0],
                    "uid": account.pw_uid,
                    "home": account.pw_dir,
                    "shell": account.pw_shell,
                    "administrator": "wheel" in groups or account.pw_name == "localadm",
                    "locked": len(status) > 1 and status[1] == "L",
                    "autologin": account.pw_name == autologin,
                }
            )
        return sorted(result, key=lambda item: (not item["administrator"], item["username"]))

    def _set_password(self, username: str, password: str) -> None:
        self.validate_password(password)
        payload = f"{username}:{password}\n".encode()
        self.runner.run(["chpasswd"], input_data=payload)

    @staticmethod
    def _encrypted_password_payload(username: str, password_hash: str) -> bytes:
        if (
            not password_hash
            or len(password_hash) > 4096
            or any(character in password_hash for character in (":", "\n", "\r", "\x00"))
        ):
            raise CachyFreezeError("Kullanıcı yedeğindeki parola hash'i geçersiz.")
        return f"{username}:{password_hash}\n".encode()

    def _refresh_template(self, username: str, home: Path) -> None:
        self.template_root.mkdir(parents=True, mode=0o700, exist_ok=True)
        template = self.template_root / username
        candidate = self.template_root / f"{username}.next"
        previous = self.template_root / f"{username}.previous"
        for path in (candidate, previous):
            if path.exists():
                shutil.rmtree(path)
        candidate.mkdir(mode=0o700)
        self.runner.run(["rsync", "-aHAX", "--delete", f"{home}/", f"{candidate}/"])
        if template.exists():
            os.replace(template, previous)
        os.replace(candidate, template)

    def refresh_templates(self, *, already_locked: bool = False) -> list[str]:
        self.require_root()
        refreshed: list[str] = []
        lock = nullcontext() if already_locked else ProcessLock(self.lock_file)
        with lock:
            if not self.template_root.is_dir():
                return refreshed
            for template in self.template_root.iterdir():
                username = template.name
                if not template.is_dir() or not _USERNAME_RE.fullmatch(username):
                    continue
                account = self._account(username)
                if account is None or not Path(account.pw_dir).is_dir():
                    continue
                self._refresh_template(username, Path(account.pw_dir))
                refreshed.append(username)
        self.logger.write(
            "INFO",
            "user.templates",
            "Yönetilen kullanıcı ev şablonları yenilendi",
            users=refreshed,
        )
        return refreshed

    def create(self, username: str, display_name: str, password: str) -> dict[str, Any]:
        self.require_root()
        username = self.validate_username(username)
        display_name = " ".join(display_name.split())
        if not display_name or len(display_name) > 100 or ":" in display_name:
            raise CachyFreezeError("Görünen ad 1-100 karakter olmalıdır.")
        self.validate_password(password)
        with ProcessLock(self.lock_file):
            if self._account(username) is not None:
                raise CachyFreezeError("Bu kullanıcı zaten var.")
            self.runner.run(
                [
                    "useradd",
                    "--create-home",
                    "--user-group",
                    "--shell",
                    "/bin/bash",
                    "--comment",
                    display_name,
                    username,
                ]
            )
            try:
                self._set_password(username, password)
                self.runner.run(["gpasswd", "-d", username, "wheel"], check=False)
                self.runner.run(["gpasswd", "-d", username, "sudo"], check=False)
                account = self._account(username)
                assert account is not None
                self._refresh_template(username, Path(account.pw_dir))
            except Exception:
                self.runner.run(["userdel", "--remove", username], check=False)
                shutil.rmtree(self.template_root / username, ignore_errors=True)
                shutil.rmtree(self.template_root / f"{username}.next", ignore_errors=True)
                raise
        self.logger.write(
            "INFO", "user.create", "Standart kullanıcı oluşturuldu", username=username
        )
        return next(item for item in self.list_users() if item["username"] == username)

    def _backup_account(self, account: pwd.struct_passwd) -> str:
        backup_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{account.pw_name}"
        backup_dir = self.state_dir / "user-backups" / backup_id
        backup_dir.mkdir(parents=True, mode=0o700)
        shadow = self.runner.text(["getent", "shadow", account.pw_name])
        groups = self.runner.text(["id", "-nG", account.pw_name], check=False).split()
        atomic_json_write(
            backup_dir / "account.json",
            {
                "schema": 1,
                "backup_id": backup_id,
                "created_at": datetime.now(UTC).isoformat(),
                "username": account.pw_name,
                "uid": account.pw_uid,
                "gid": account.pw_gid,
                "gecos": account.pw_gecos,
                "home": account.pw_dir,
                "shell": account.pw_shell,
                "password_hash": shadow.split(":", 2)[1],
                "groups": groups,
            },
        )
        home = Path(account.pw_dir)
        if home.is_dir():
            self.runner.run(
                [
                    "tar",
                    "--acls",
                    "--xattrs",
                    "--numeric-owner",
                    "-cpf",
                    str(backup_dir / "home.tar"),
                    "-C",
                    "/",
                    str(home).lstrip("/"),
                ]
            )
        template = self.template_root / account.pw_name
        if template.is_dir():
            self.runner.run(
                [
                    "tar",
                    "--acls",
                    "--xattrs",
                    "--numeric-owner",
                    "-cpf",
                    str(backup_dir / "template.tar"),
                    "-C",
                    str(self.template_root),
                    account.pw_name,
                ]
            )
        return backup_id

    def delete(self, username: str) -> dict[str, Any]:
        self.require_root()
        username = self.validate_username(username)
        if username == "localadm":
            raise CachyFreezeError("localadm korumalı yönetici hesabıdır ve silinemez.")
        with ProcessLock(self.lock_file):
            account = self._account(username)
            if account is None:
                raise CachyFreezeError("Kullanıcı bulunamadı.")
            backup_id = self._backup_account(account)
            if self._autologin_user() == username:
                self._write_autologin(None)
            self.runner.run(["userdel", "--remove", username])
            shutil.rmtree(self.template_root / username, ignore_errors=True)
            shutil.rmtree(self.template_root / f"{username}.previous", ignore_errors=True)
        self.logger.write(
            "WARNING",
            "user.delete",
            "Kullanıcı geri yüklenebilir yedekle silindi",
            username=username,
            backup_id=backup_id,
        )
        return {"username": username, "backup_id": backup_id}

    def restore(self, backup_id: str) -> dict[str, Any]:
        self.require_root()
        if not _BACKUP_ID_RE.fullmatch(backup_id):
            raise CachyFreezeError("Geçersiz kullanıcı yedek kimliği.")
        backup_dir = self.state_dir / "user-backups" / backup_id
        try:
            metadata = json.loads((backup_dir / "account.json").read_text(encoding="utf-8"))
            username = self.validate_username(str(metadata["username"]))
            password_payload = self._encrypted_password_payload(
                username, str(metadata["password_hash"])
            )
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise CachyFreezeError(f"Kullanıcı yedeği okunamadı: {error}") from error
        with ProcessLock(self.lock_file):
            if self._account(username) is not None:
                raise CachyFreezeError("Yedekteki kullanıcı adı sistemde zaten var.")
            group_name = username
            if self.runner.run(["getent", "group", group_name], check=False).returncode != 0:
                self.runner.run(["groupadd", "--gid", str(int(metadata["gid"])), group_name])
            self.runner.run(
                [
                    "useradd",
                    "--uid",
                    str(int(metadata["uid"])),
                    "--gid",
                    group_name,
                    "--home-dir",
                    str(metadata["home"]),
                    "--shell",
                    str(metadata["shell"]),
                    "--comment",
                    str(metadata["gecos"]),
                    username,
                ]
            )
            try:
                self.runner.run(["chpasswd", "--encrypted"], input_data=password_payload)
                archive = backup_dir / "home.tar"
                if archive.is_file():
                    self.runner.run(["tar", "--acls", "--xattrs", "-xpf", str(archive), "-C", "/"])
                template_archive = backup_dir / "template.tar"
                if template_archive.is_file():
                    self.template_root.mkdir(parents=True, mode=0o700, exist_ok=True)
                    self.runner.run(
                        [
                            "tar",
                            "--acls",
                            "--xattrs",
                            "-xpf",
                            str(template_archive),
                            "-C",
                            str(self.template_root),
                        ]
                    )
                else:
                    self._refresh_template(username, Path(str(metadata["home"])))
                safe_groups = [
                    group
                    for group in metadata.get("groups", [])
                    if group not in {group_name, "wheel", "sudo"}
                    and re.fullmatch(r"[a-z_][a-z0-9_-]{0,30}", str(group))
                ]
                if safe_groups:
                    self.runner.run(["usermod", "-aG", ",".join(safe_groups), username])
            except Exception:
                self.runner.run(["userdel", "--remove", username], check=False)
                shutil.rmtree(self.template_root / username, ignore_errors=True)
                raise
        self.logger.write(
            "WARNING",
            "user.restore",
            "Standart kullanıcı yedekten geri yüklendi",
            username=username,
            backup_id=backup_id,
        )
        return next(item for item in self.list_users() if item["username"] == username)

    def set_password(self, username: str, password: str) -> None:
        self.require_root()
        username = self.validate_username(username)
        if self._account(username) is None:
            raise CachyFreezeError("Kullanıcı bulunamadı.")
        with ProcessLock(self.lock_file):
            self._set_password(username, password)
        self.logger.write(
            "WARNING", "user.password", "Kullanıcı parolası sıfırlandı", username=username
        )

    def set_locked(self, username: str, locked: bool) -> None:
        self.require_root()
        username = self.validate_username(username)
        if username == "localadm":
            raise CachyFreezeError("localadm yönetici hesabı kilitlenemez.")
        if self._account(username) is None:
            raise CachyFreezeError("Kullanıcı bulunamadı.")
        with ProcessLock(self.lock_file):
            self.runner.run(["usermod", "--lock" if locked else "--unlock", username])
        self.logger.write(
            "WARNING",
            "user.lock" if locked else "user.unlock",
            "Kullanıcı hesabı kilitlendi" if locked else "Kullanıcı hesabı açıldı",
            username=username,
        )

    def _write_autologin(self, username: str | None) -> None:
        if username is None:
            self.autologin_path.unlink(missing_ok=True)
            return
        atomic_text_write(
            self.autologin_path,
            f"[Autologin]\nUser={username}\nSession=plasma.desktop\nRelogin=true\n",
            mode=0o644,
        )

    def set_autologin(self, username: str | None) -> dict[str, Any]:
        self.require_root()
        if username is not None:
            username = self.validate_username(username)
            account = self._account(username)
            if account is None:
                raise CachyFreezeError("Kullanıcı bulunamadı.")
            if username == "localadm":
                raise CachyFreezeError("Yönetici hesabında otomatik giriş etkinleştirilemez.")
        with ProcessLock(self.lock_file):
            self.autologin_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_autologin(username)
        self.logger.write(
            "WARNING",
            "user.autologin",
            "Otomatik giriş ayarı değiştirildi",
            username=username,
        )
        return {"username": username, "enabled": username is not None, "changed_at": time.time()}
