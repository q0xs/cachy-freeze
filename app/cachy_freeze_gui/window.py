"""Single-purpose installer and FROZEN/THAWED control window."""

from __future__ import annotations

import re
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .backend import BackendClient
from .styles import DARK_STYLE

BUTTON_MIN_HEIGHT = 48
BUTTON_MIN_WIDTH = 132
FIELD_MIN_HEIGHT = 44
MODE_BADGE_MIN_HEIGHT = 60


class MainWindow(QMainWindow):
    def __init__(self, backend: BackendClient) -> None:
        super().__init__()
        self.backend = backend
        self.running_mode = "unknown"
        self.scheduled_mode = "unknown"
        self.reboot_required = False
        self.verified = False
        self.workstation_ready_user = ""
        self.installer_mode = backend.setup_root is not None
        self.workstation_available = backend.workstation_available
        self.setWindowTitle("CachyFreeze Installer" if self.installer_mode else "CachyFreeze")
        self.setMinimumSize(420, 420)
        self.resize(640, 720 if self.installer_mode else 620)
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
        label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        return label

    @staticmethod
    def _mode_text(mode: str) -> str:
        return {"frozen": "FROZEN", "thawed": "THAWED"}.get(mode, "VERIFYING")

    @staticmethod
    def _button(text: str, *, name: str = "") -> QPushButton:
        button = QPushButton(text)
        if name:
            button.setObjectName(name)
        text_width = button.fontMetrics().horizontalAdvance(text)
        button.setMinimumSize(
            max(BUTTON_MIN_WIDTH, text_width + 48),
            max(BUTTON_MIN_HEIGHT, button.sizeHint().height()),
        )
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        return button

    @staticmethod
    def _line_edit(placeholder: str, *, password: bool = False) -> QLineEdit:
        field = QLineEdit()
        if password:
            field.setEchoMode(QLineEdit.EchoMode.Password)
        field.setPlaceholderText(placeholder)
        field.setMinimumHeight(max(FIELD_MIN_HEIGHT, field.sizeHint().height()))
        field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        return field

    @staticmethod
    def _button_row(*buttons: QPushButton) -> QWidget:
        row = QWidget()
        row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        for button in buttons:
            row_layout.addWidget(button)
        return row

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)
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
        self.reboot_button = self._button("REBOOT NOW", name="danger")
        self.reboot_button.hide()
        layout.addWidget(self.reboot_button)

        scroll.setWidget(container)
        self.setCentralWidget(scroll)

    def _build_manager(self, layout: QVBoxLayout) -> None:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(10)
        card_layout.addWidget(self._label("Current Mode", name="cardCaption", centered=True))
        self.mode_label = self._label("VERIFYING", name="modeBadge", centered=True)
        self.mode_label.setMinimumHeight(
            max(MODE_BADGE_MIN_HEIGHT, self.mode_label.sizeHint().height())
        )
        card_layout.addWidget(self.mode_label)
        self.next_mode_label = self._label("", name="muted", centered=True)
        card_layout.addWidget(self.next_mode_label)
        layout.addWidget(card)

        self.freeze_button = self._button("FREEZE COMPUTER", name="primary")
        self.thaw_button = self._button("THAW COMPUTER", name="primary")
        self.refresh_button = self._button("VERIFY STATE")
        layout.addWidget(self._button_row(self.freeze_button, self.thaw_button))
        layout.addWidget(self.refresh_button)
        if self.workstation_available:
            self._build_workstation(layout)

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
                "Finish Workstation preparation first. CachyFreeze installation will create "
                "the initial Golden baseline from the checked system.",
                name="muted",
            )
        )
        if self.workstation_available:
            self._build_workstation(layout)
        self.password = self._line_edit("Boot-maintenance password", password=True)
        self.password_confirm = self._line_edit("Confirm password", password=True)
        self.install_button = self._button("INSTALL CACHYFREEZE", name="primary")
        layout.addWidget(self.password)
        layout.addWidget(self.password_confirm)
        layout.addWidget(self.install_button)
        if self.workstation_available:
            self.install_button.setEnabled(False)

    def _build_workstation(self, layout: QVBoxLayout) -> None:
        layout.addWidget(
            self._label(
                "CachyWorkstation installs or repairs employee applications, launchers, "
                "MicroSIP/Wine, and idle policy for an existing standard user.",
                name="muted",
            )
        )
        self.workstation_user = self._line_edit("Employee username")
        self.workstation_install_button = self._button("INSTALL / REPAIR", name="primary")
        self.workstation_check_button = self._button("CHECK")
        self.workstation_report = QPlainTextEdit()
        self.workstation_report.setReadOnly(True)
        self.workstation_report.setMinimumHeight(132)
        self.workstation_report.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.workstation_report.setPlaceholderText("Workstation check output")
        layout.addWidget(self.workstation_user)
        layout.addWidget(
            self._button_row(self.workstation_install_button, self.workstation_check_button)
        )
        layout.addWidget(self.workstation_report)

    def _connect(self) -> None:
        self.backend.busy_changed.connect(self._busy_changed)
        self.backend.status_changed.connect(self._status_changed)
        self.backend.operation_finished.connect(self._operation_finished)
        self.backend.operation_output.connect(self._operation_output)
        self.reboot_button.clicked.connect(self._confirm_reboot)
        if self.workstation_available:
            self.workstation_install_button.clicked.connect(self._install_workstation)
            self.workstation_check_button.clicked.connect(self._check_workstation)
            self.workstation_user.textChanged.connect(self._workstation_user_changed)
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
        if self.installer_mode and self.workstation_available:
            target_user = self._workstation_user()
            if target_user is None:
                return
            if self.workstation_ready_user != target_user:
                QMessageBox.warning(
                    self,
                    "Workstation check required",
                    "Run CHECK WORKSTATION successfully for this employee before installing "
                    "CachyFreeze.",
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

    def _workstation_user(self) -> str | None:
        target_user = self.workstation_user.text().strip()
        if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,30}", target_user):
            QMessageBox.warning(
                self,
                "Invalid employee username",
                "Enter an existing standard Linux username, for example wrw1166.",
            )
            return None
        return target_user

    def _install_workstation(self) -> None:
        target_user = self._workstation_user()
        if target_user is None:
            return
        answer = QMessageBox.warning(
            self,
            "Install CachyWorkstation",
            "This will install or repair employee workstation applications, launchers, "
            "MicroSIP/Wine, and the idle policy for the selected standard user. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.workstation_ready_user = ""
            self._set_workstation_report(
                "Installing or repairing CachyWorkstation. Run CHECK WORKSTATION after manual "
                "application testing."
            )
            self.backend.run("setup-workstation-install", secret=target_user)

    def _check_workstation(self) -> None:
        target_user = self._workstation_user()
        if target_user is not None:
            self.workstation_ready_user = ""
            self._set_workstation_report(f"Checking CachyWorkstation for {target_user}...\n")
            self.backend.run("setup-workstation-check", secret=target_user)

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
            self.install_button.setEnabled(self._can_install_cachyfreeze())
            self.password.setEnabled(not busy)
            self.password_confirm.setEnabled(not busy)
            self._apply_workstation_controls(busy=busy)
        else:
            self._apply_mode_controls(busy=busy)

    def _status_changed(self, status: dict[str, Any]) -> None:
        self.verified = bool(status.get("verified"))
        if self.installer_mode:
            self.message_label.setText(
                "Ready to validate and install or safely reconcile CachyFreeze."
            )
            self.install_button.setEnabled(self._can_install_cachyfreeze())
            self._apply_workstation_controls(busy=self.backend.busy)
            return
        self.running_mode = str(status.get("running_mode", "unknown"))
        self.scheduled_mode = str(status.get("scheduled_mode", "unknown"))
        self.reboot_required = bool(status.get("reboot_required"))
        self.mode_label.setText(self._mode_text(self.running_mode))
        if self.verified and self.scheduled_mode != self.running_mode:
            self.next_mode_label.setText(f"Next Boot: {self._mode_text(self.scheduled_mode)}")
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
        self._apply_workstation_controls(busy=busy)

    def _apply_workstation_controls(self, *, busy: bool) -> None:
        if not self.workstation_available:
            return
        self.workstation_user.setEnabled(not busy)
        if self.installer_mode:
            can_install = not busy
            can_check = not busy
        else:
            verified = self.verified and not self.reboot_required
            can_install = verified and not busy and self.running_mode == "thawed"
            can_check = verified and not busy
        self.workstation_install_button.setEnabled(can_install)
        self.workstation_check_button.setEnabled(can_check)
        if self.installer_mode:
            self.install_button.setEnabled(self._can_install_cachyfreeze())

    def _can_install_cachyfreeze(self) -> bool:
        if not self.installer_mode or self.backend.busy:
            return False
        if not self.workstation_available:
            return True
        target_user = self.workstation_user.text().strip()
        return bool(target_user) and self.workstation_ready_user == target_user

    def _workstation_user_changed(self) -> None:
        if self.workstation_ready_user != self.workstation_user.text().strip():
            self.workstation_ready_user = ""
        self._apply_workstation_controls(busy=self.backend.busy)

    def _set_workstation_report(self, text: str) -> None:
        if self.workstation_available:
            self.workstation_report.setPlainText(text)

    def _operation_output(self, action: str, output: str) -> None:
        if not action.startswith("setup-workstation-") or not self.workstation_available:
            return
        cursor = self.workstation_report.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.workstation_report.setTextCursor(cursor)
        self.workstation_report.insertPlainText(output)
        self.workstation_report.ensureCursorVisible()

    def _operation_finished(self, action: str, success: bool, message: str) -> None:
        self.message_label.setText(message)
        if not success:
            if action.startswith("setup-workstation-") and self.workstation_available:
                self.workstation_ready_user = ""
                self._apply_workstation_controls(busy=self.backend.busy)
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
        elif action.startswith("setup-workstation-"):
            if action == "setup-workstation-check":
                self.workstation_ready_user = self.workstation_user.text().strip()
            else:
                self.workstation_ready_user = ""
            self._apply_workstation_controls(busy=self.backend.busy)
            QMessageBox.information(self, "CachyWorkstation", message)
