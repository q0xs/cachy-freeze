"""Single-purpose installer and FROZEN/THAWED control window."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .backend import BackendClient
from .styles import DARK_STYLE


class MainWindow(QMainWindow):
    def __init__(self, backend: BackendClient) -> None:
        super().__init__()
        self.backend = backend
        self.running_mode = "unknown"
        self.scheduled_mode = "unknown"
        self.reboot_required = False
        self.verified = False
        self.installer_mode = backend.setup_root is not None
        self.setWindowTitle("CachyFreeze Installer" if self.installer_mode else "CachyFreeze")
        self.setMinimumSize(560, 520 if self.installer_mode else 460)
        self.resize(620, 560 if self.installer_mode else 500)
        self.setStyleSheet(DARK_STYLE)
        self._build_ui()
        self._connect()
        self.backend.refresh_local()
        if not self.installer_mode:
            self.backend.run("status")

    @staticmethod
    def _label(text: str, *, name: str = "", centered: bool = False) -> QLabel:
        label = QLabel(text)
        if name:
            label.setObjectName(name)
        label.setWordWrap(True)
        if centered:
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def _build_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(54, 44, 54, 44)
        layout.setSpacing(18)
        title = self._label(
            "CachyFreeze Installer" if self.installer_mode else "CachyFreeze",
            name="pageTitle",
            centered=True,
        )
        layout.addWidget(title)
        if self.installer_mode:
            self._build_installer(layout)
        else:
            self._build_manager(layout)
        layout.addStretch(1)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.message_label = self._label("Verifying system state…", name="muted", centered=True)
        layout.addWidget(self.message_label)
        self.reboot_button = QPushButton("REBOOT NOW")
        self.reboot_button.setObjectName("danger")
        self.reboot_button.hide()
        layout.addWidget(self.reboot_button)
        self.setCentralWidget(container)

    def _build_manager(self, layout: QVBoxLayout) -> None:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(14)
        card_layout.addWidget(self._label("Current Mode", name="cardCaption", centered=True))
        self.mode_label = self._label("VERIFYING", name="modeBadge", centered=True)
        card_layout.addWidget(self.mode_label)
        self.next_mode_label = self._label("", name="muted", centered=True)
        card_layout.addWidget(self.next_mode_label)
        layout.addWidget(card)

        self.freeze_button = QPushButton("FREEZE COMPUTER")
        self.freeze_button.setObjectName("primary")
        self.thaw_button = QPushButton("THAW COMPUTER")
        self.thaw_button.setObjectName("primary")
        self.refresh_button = QPushButton("Refresh verified state")
        layout.addWidget(self.freeze_button)
        layout.addWidget(self.thaw_button)
        layout.addWidget(self.refresh_button)

    def _build_installer(self, layout: QVBoxLayout) -> None:
        layout.addWidget(
            self._label(
                "Compatibility checks, Btrfs layout, boot integration, PolicyKit, "
                "the initial Golden baseline, and the KDE launcher are configured automatically.",
                name="muted",
                centered=True,
            )
        )
        layout.addWidget(
            self._label(
                "Set a boot-maintenance password. It protects THAWED access in GRUB and is "
                "sent only through the installer process input channel.",
                name="muted",
            )
        )
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Boot-maintenance password")
        self.password_confirm = QLineEdit()
        self.password_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_confirm.setPlaceholderText("Confirm password")
        self.install_button = QPushButton("INSTALL CACHYFREEZE")
        self.install_button.setObjectName("primary")
        layout.addWidget(self.password)
        layout.addWidget(self.password_confirm)
        layout.addWidget(self.install_button)

    def _connect(self) -> None:
        self.backend.busy_changed.connect(self._busy_changed)
        self.backend.status_changed.connect(self._status_changed)
        self.backend.operation_finished.connect(self._operation_finished)
        self.reboot_button.clicked.connect(self._confirm_reboot)
        if self.installer_mode:
            self.install_button.clicked.connect(self._install)
        else:
            self.freeze_button.clicked.connect(self._freeze)
            self.thaw_button.clicked.connect(self._thaw)
            self.refresh_button.clicked.connect(lambda: self.backend.run("status"))

    @staticmethod
    def _strong_password(value: str) -> bool:
        if not 12 <= len(value) <= 256 or any(character in value for character in ":\r\n"):
            return False
        classes = sum(
            (
                any(character.islower() for character in value),
                any(character.isupper() for character in value),
                any(character.isdigit() for character in value),
                any(not character.isalnum() for character in value),
            )
        )
        return classes >= 3

    def _install(self) -> None:
        secret = self.password.text()
        confirmation = self.password_confirm.text()
        if secret != confirmation or not self._strong_password(secret):
            QMessageBox.warning(
                self,
                "Invalid password",
                "Passwords must match, contain 12-256 characters, avoid ':' and use at "
                "least three character classes.",
            )
            return
        answer = QMessageBox.warning(
            self,
            "Install CachyFreeze",
            "The installer will validate and then modify CachyFreeze-owned Btrfs and GRUB "
            "state. Unrelated subvolumes and boot entries must be preserved. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.password.clear()
        self.password_confirm.clear()
        self.backend.run("setup-install", secret=secret)

    def _freeze(self) -> None:
        answer = QMessageBox.warning(
            self,
            "Freeze computer",
            "Save work and close applications first. CachyFreeze will build and validate a "
            "new Golden baseline from the current THAWED system. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.backend.run("freeze")

    def _thaw(self) -> None:
        answer = QMessageBox.question(
            self,
            "Thaw computer",
            "Schedule the persistent maintenance environment for the next boot? The current "
            "FROZEN runtime will not be copied or retained.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.backend.run("thaw")

    def _confirm_reboot(self) -> None:
        answer = QMessageBox.question(
            self,
            "Reboot now",
            "Save all work before rebooting. Reboot now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.backend.run("reboot")

    def _busy_changed(self, busy: bool) -> None:
        self.progress.setVisible(busy)
        self.reboot_button.setEnabled(not busy)
        if self.installer_mode:
            self.install_button.setEnabled(not busy and not self.verified)
            self.password.setEnabled(not busy)
            self.password_confirm.setEnabled(not busy)
        else:
            self._apply_mode_controls(busy=busy)

    def _status_changed(self, status: dict[str, Any]) -> None:
        self.verified = bool(status.get("verified"))
        if self.installer_mode:
            self.message_label.setText(
                "Ready to validate and install or safely reconcile CachyFreeze."
            )
            self.install_button.setEnabled(not self.backend.busy)
            return
        self.running_mode = str(status.get("running_mode", "unknown"))
        self.scheduled_mode = str(status.get("scheduled_mode", "unknown"))
        self.reboot_required = bool(status.get("reboot_required"))
        self.mode_label.setText(self.running_mode.upper() if self.verified else "VERIFYING")
        if self.verified and self.scheduled_mode != self.running_mode:
            self.next_mode_label.setText(f"Next Boot: {self.scheduled_mode.upper()}")
        else:
            self.next_mode_label.setText("")
        if not self.verified:
            self.message_label.setText(
                "Cached state is shown only while privileged verification runs."
            )
        elif status.get("transaction_pending"):
            self.message_label.setText("An interrupted transaction requires safe reconciliation.")
        elif self.reboot_required:
            self.message_label.setText(
                f"Reboot required to enter {self.scheduled_mode.upper()} mode."
            )
        else:
            self.message_label.setText("System state verified.")
        self.reboot_button.setVisible(self.verified and self.reboot_required)
        self._apply_mode_controls(busy=self.backend.busy)

    def _apply_mode_controls(self, *, busy: bool) -> None:
        if self.installer_mode:
            return
        valid = self.verified and not busy and not self.reboot_required
        self.freeze_button.setEnabled(valid and self.running_mode == "thawed")
        self.thaw_button.setEnabled(valid and self.running_mode == "frozen")
        self.refresh_button.setEnabled(not busy)

    def _operation_finished(self, action: str, success: bool, message: str) -> None:
        self.message_label.setText(message)
        if not success:
            QMessageBox.critical(self, "CachyFreeze operation failed", message)
            return
        if action in {"freeze", "thaw", "setup-install"}:
            self.reboot_required = True
            self.reboot_button.show()
            if self.installer_mode and action == "setup-install":
                self.install_button.setEnabled(False)
            QMessageBox.information(
                self,
                "Reboot required",
                message + " Save all work, then use REBOOT NOW when ready.",
            )
