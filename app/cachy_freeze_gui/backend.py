"""Asynchronous, JSON-only bridge to the PolicyKit helper."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

HELPER = "/usr/lib/cachy-freeze/cachy-freeze-manager-helper"
STATUS_CACHE = Path("/var/lib/cachy-freeze/status.json")
SNAPSHOT_CATALOG = Path("/var/lib/cachy-freeze/snapshots.json")


class BackendClient(QObject):
    busy_changed = pyqtSignal(bool)
    status_changed = pyqtSignal(dict)
    snapshots_changed = pyqtSignal(list)
    logs_changed = pyqtSignal(list)
    users_changed = pyqtSignal(list)
    result_ready = pyqtSignal(str, object)
    operation_finished = pyqtSignal(str, bool, str)

    def __init__(self) -> None:
        super().__init__()
        self.process: QProcess | None = None
        self.pending_action = ""
        self.status: dict[str, Any] = {}
        self.snapshots: list[dict[str, Any]] = []
        self.logs: list[dict[str, Any]] = []
        self.users: list[dict[str, Any]] = []
        self.pending_secret: str | None = None

    @property
    def busy(self) -> bool:
        return self.process is not None

    @staticmethod
    def _read_json(path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def refresh_local(self) -> None:
        cached_status = self._read_json(STATUS_CACHE)
        if isinstance(cached_status, dict):
            self.status = cached_status
        else:
            self.status = self._fallback_status()
        self.status_changed.emit(self.status)

        catalog = self._read_json(SNAPSHOT_CATALOG)
        items = catalog.get("snapshots", []) if isinstance(catalog, dict) else []
        self.snapshots = sorted(
            [item for item in items if isinstance(item, dict)],
            key=lambda item: str(item.get("created_at", "")),
            reverse=True,
        )
        self.snapshots_changed.emit(self.snapshots)

    @staticmethod
    def _fallback_status() -> dict[str, Any]:
        try:
            command_line = Path("/proc/cmdline").read_text(encoding="utf-8").split()
        except OSError:
            command_line = []
        if "cachy.freeze=1" in command_line:
            mode = "frozen"
        elif "cachy.freeze=0" in command_line:
            mode = "thawed"
        else:
            mode = "unknown"
        return {
            "schema": 1,
            "running_mode": mode,
            "scheduled_mode": "unknown",
            "snapshot_count": 0,
            "last_snapshot": None,
            "golden_present": False,
            "active_present": False,
            "transaction_pending": False,
        }

    def run(self, action: str, *arguments: str, secret: str | None = None) -> bool:
        if self.busy:
            self.operation_finished.emit(
                action, False, "Başka bir Cachy Freeze işlemi devam ediyor."
            )
            return False
        if not os.access(HELPER, os.X_OK):
            self.operation_finished.emit(
                action, False, "Yetkili Cachy Freeze yardımcısı bulunamadı."
            )
            return False
        self.pending_action = action
        self.pending_secret = secret
        self.process = QProcess(self)
        self.process.setProgram("/usr/bin/pkexec")
        self.process.setArguments([HELPER, action, *arguments])
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self.process.started.connect(self._send_secret)
        self.busy_changed.emit(True)
        self.process.start()
        return True

    def _send_secret(self) -> None:
        if self.process is None or self.pending_secret is None:
            return
        self.process.write((self.pending_secret + "\n").encode("utf-8"))
        self.process.closeWriteChannel()
        self.pending_secret = None

    def _finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        if self.process is None:
            return
        action = self.pending_action
        stdout = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        stderr = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        self.process.deleteLater()
        self.process = None
        self.pending_action = ""
        self.pending_secret = None
        self.busy_changed.emit(False)
        if exit_code in (126, 127):
            self.operation_finished.emit(action, False, "Kimlik doğrulama iptal edildi.")
            return
        if exit_code != 0:
            self.operation_finished.emit(action, False, stderr.strip() or "İşlem tamamlanamadı.")
            return
        try:
            payload = json.loads(stdout)
            if payload.get("ok") is not True:
                raise ValueError("invalid backend response")
            result = payload.get("result")
        except (json.JSONDecodeError, AttributeError, ValueError):
            self.operation_finished.emit(
                action, False, "Yetkili servis geçersiz bir yanıt döndürdü."
            )
            return

        if action == "status" and isinstance(result, dict):
            self.status = result
            self.status_changed.emit(self.status)
        elif action == "snapshot-list" and isinstance(result, list):
            self.snapshots = result
            self.snapshots_changed.emit(self.snapshots)
        elif action == "logs" and isinstance(result, list):
            self.logs = result
            self.logs_changed.emit(self.logs)
        elif action == "user-list" and isinstance(result, list):
            self.users = result
            self.users_changed.emit(self.users)
        else:
            self.refresh_local()
        self.result_ready.emit(action, result)
        self.operation_finished.emit(action, True, self._success_message(action))

    def _process_error(self, _error: QProcess.ProcessError) -> None:
        if self.process is None or self.process.state() != QProcess.ProcessState.NotRunning:
            return
        action = self.pending_action
        self.process.deleteLater()
        self.process = None
        self.pending_action = ""
        self.pending_secret = None
        self.busy_changed.emit(False)
        self.operation_finished.emit(action, False, "Yetkili işlem başlatılamadı.")

    @staticmethod
    def _success_message(action: str) -> str:
        messages = {
            "status": "Sistem durumu yenilendi.",
            "thaw": "Sonraki açılış THAWED bakım moduna ayarlandı.",
            "thaw-once": "Yalnızca sonraki açılış THAWED olarak ayarlandı.",
            "freeze": "Golden yayınlandı ve sonraki açılış FROZEN olarak ayarlandı.",
            "snapshot-list": "Snapshot listesi yenilendi.",
            "snapshot-create": "Snapshot başarıyla oluşturuldu.",
            "snapshot-verify": "Snapshot doğrulaması tamamlandı.",
            "snapshot-delete": "Snapshot silindi.",
            "snapshot-rollback": "Rollback hazırlandı; sonraki açılış FROZEN olacak.",
            "snapshot-export": "Snapshot export klasörüne yazıldı.",
            "snapshot-import": "Snapshot checksum doğrulamasıyla içe aktarıldı.",
            "health": "Sistem sağlık kontrolü tamamlandı.",
            "logs": "Audit logları yenilendi.",
            "user-list": "Kullanıcı listesi yenilendi.",
            "user-create": "Standart kullanıcı oluşturuldu.",
            "user-delete": "Kullanıcı yedeklenerek silindi.",
            "user-restore": "Kullanıcı yedekten geri yüklendi.",
            "user-password": "Kullanıcı parolası değiştirildi.",
            "user-lock": "Kullanıcı hesabı kilitlendi.",
            "user-unlock": "Kullanıcı hesabı açıldı.",
            "user-autologin": "Otomatik giriş ayarı güncellendi.",
            "updates-check": "Güncelleme denetimi tamamlandı.",
            "updates-apply": "Güncellemeler uygulandı ve yeni Golden yayınlandı.",
            "settings-get": "Ayarlar yüklendi.",
            "settings-set": "Ayarlar doğrulanarak kaydedildi.",
            "applications-status": "Kurumsal uygulamalar doğrulandı.",
            "applications-install": "Uygulamalar kuruldu ve yeni Golden yayınlandı.",
            "reboot": "Sistem yeniden başlatılıyor.",
        }
        return messages.get(action, "İşlem başarıyla tamamlandı.")
