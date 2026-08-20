"""Reusable localized GUI formatting helpers and dialogs."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget

from .widgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
)


def human_bytes(value: int) -> str:
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TiB"


def local_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value).astimezone().strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return value or "—"


class MetricCard(QFrame):
    def __init__(self, caption: str) -> None:
        super().__init__()
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 15, 18, 15)
        caption_label = QLabel(caption)
        caption_label.setObjectName("cardCaption")
        self.value = QLabel("—")
        self.value.setObjectName("cardValue")
        self.detail = QLabel("")
        self.detail.setObjectName("muted")
        self.detail.setWordWrap(True)
        layout.addWidget(caption_label)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)


class UserDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create application-ready user")
        self.setMinimumWidth(480)
        layout = QFormLayout(self)
        intro = QLabel(
            "Creates a standard, non-administrator account and prepares its desktop, "
            "KDE settings, application shortcuts, and verified MicroSIP profile."
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        layout.addRow(intro)
        self.username = QLineEdit()
        self.username.setPlaceholderText("wrw21166")
        self.username.setToolTip(
            "Lowercase letters, digits, underscores, and hyphens; must start with a letter."
        )
        self.display_name = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_confirm = QLineEdit()
        self.password_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.autologin = QCheckBox("Sign in automatically as this user")
        layout.addRow("Username", self.username)
        layout.addRow("Display name", self.display_name)
        layout.addRow("Password", self.password)
        layout.addRow("Confirm password", self.password_confirm)
        layout.addRow("", self.autologin)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
