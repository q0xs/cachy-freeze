"""Main window for dashboard, snapshots, users, updates, logs, and settings."""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from typing import Any

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .backend import BackendClient
from .styles import DARK_STYLE, LIGHT_STYLE


def _human_bytes(value: int) -> str:
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TiB"


def _date(value: str) -> str:
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
        caption_label = QLabel(caption.upper())
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
        self.freeze_after_create = QCheckBox(
            "Publish Golden and schedule FROZEN mode after creation"
        )
        self.freeze_after_create.setChecked(True)
        layout.addRow("Username", self.username)
        layout.addRow("Display name", self.display_name)
        layout.addRow("Password", self.password)
        layout.addRow("Confirm password", self.password_confirm)
        layout.addRow("", self.autologin)
        layout.addRow("", self.freeze_after_create)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class MainWindow(QMainWindow):
    def __init__(self, backend: BackendClient) -> None:
        super().__init__()
        self.backend = backend
        self.settings = QSettings("CachyOS Workstation", "CachyFreeze")
        self.settings.remove("pending_autologin")
        self.setup_preflight_ok = False
        self.pending_user_freeze = False
        self.pending_autologin_user: str | None = None
        self.pending_user_create_check = False
        self.setWindowTitle("CachyFreeze Management Center")
        self.setMinimumSize(980, 640)
        self.resize(1180, 740)
        self._build_ui()
        self._connect()
        self._apply_theme(str(self.settings.value("theme", "dark")))
        self.backend.refresh_local()

    def _build_ui(self) -> None:
        central = QWidget()
        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(232)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 22, 16, 18)
        brand = QLabel("❄  CachyFreeze")
        brand.setObjectName("brand")
        side_layout.addWidget(brand)
        product_note = QLabel("WORKSTATION CONTROL")
        product_note.setObjectName("sidebarCaption")
        side_layout.addWidget(product_note)
        self.nav_buttons: list[QPushButton] = []
        self.page_titles = (
            "Overview",
            "Snapshots",
            "Users",
            "Updates",
            "Audit Logs",
            "Settings",
            "Setup",
        )
        nav_icons = ("⌂", "◇", "♙", "↻", "≡", "⚙", "✦")
        for title, icon in zip(self.page_titles, nav_icons, strict=True):
            button = QPushButton(f"{icon}   {title}")
            button.setObjectName("nav")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            self.nav_buttons.append(button)
            side_layout.addWidget(button)
        self.nav_buttons[0].setChecked(True)
        side_layout.addStretch()
        self.theme_button = QPushButton("Light / Dark Theme")
        side_layout.addWidget(self.theme_button)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 18)
        content_layout.setSpacing(14)
        header = QHBoxLayout()
        self.page_title = QLabel("Overview")
        self.page_title.setObjectName("pageTitle")
        self.mode_badge = QLabel("LOADING STATUS")
        self.mode_badge.setObjectName("modeBadge")
        self.refresh_button = QPushButton("Refresh status")
        header.addWidget(self.page_title)
        header.addStretch()
        header.addWidget(self.mode_badge)
        header.addWidget(self.refresh_button)
        content_layout.addLayout(header)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        content_layout.addWidget(self.progress)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._dashboard_page())
        self.pages.addWidget(self._snapshot_page())
        self.pages.addWidget(self._users_page())
        self.pages.addWidget(self._updates_page())
        self.pages.addWidget(self._logs_page())
        self.pages.addWidget(self._settings_page())
        self.pages.addWidget(self._setup_page())
        content_layout.addWidget(self.pages, 1)

        shell.addWidget(sidebar)
        shell.addWidget(content, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready")

    def open_setup_page(self) -> None:
        index = len(self.page_titles) - 1
        self.nav_buttons[index].setChecked(True)
        self._select_page(index, self.page_titles[index])

    def _dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(16)
        cards = QGridLayout()
        cards.setSpacing(14)
        self.mode_card = MetricCard("Running mode")
        self.snapshot_card = MetricCard("Latest snapshot")
        self.disk_card = MetricCard("Disk usage")
        self.health_card = MetricCard("System status")
        self.count_card = MetricCard("Snapshot count")
        self.update_card = MetricCard("Updates")
        for index, card in enumerate(
            (
                self.mode_card,
                self.snapshot_card,
                self.disk_card,
                self.health_card,
                self.count_card,
                self.update_card,
            )
        ):
            cards.addWidget(card, index // 2, index % 2)
        layout.addLayout(cards)

        actions = QFrame()
        actions.setObjectName("card")
        action_layout = QVBoxLayout(actions)
        action_layout.setContentsMargins(20, 18, 20, 18)
        title = QLabel("Boot mode")
        title.setObjectName("cardValue")
        text = QLabel(
            "THAWED keeps changes. FROZEN recreates a clean Active root from Golden at every boot."
        )
        text.setObjectName("muted")
        text.setWordWrap(True)
        button_row = QHBoxLayout()
        self.thaw_button = QPushButton("Switch to THAWED maintenance")
        self.freeze_button = QPushButton("Publish Golden and enable FROZEN")
        self.freeze_button.setObjectName("primary")
        self.reboot_button = QPushButton("Reboot")
        self.health_button = QPushButton("Health scan")
        button_row.addWidget(self.thaw_button)
        button_row.addWidget(self.freeze_button)
        button_row.addWidget(self.health_button)
        button_row.addStretch()
        button_row.addWidget(self.reboot_button)
        action_layout.addWidget(title)
        action_layout.addWidget(text)
        action_layout.addLayout(button_row)
        layout.addWidget(actions)
        self.alert_label = QLabel("No warnings.")
        self.alert_label.setObjectName("muted")
        self.alert_label.setWordWrap(True)
        layout.addWidget(self.alert_label)
        recent_title = QLabel("Recent operations")
        recent_title.setObjectName("cardCaption")
        self.recent_log_view = QPlainTextEdit()
        self.recent_log_view.setReadOnly(True)
        self.recent_log_view.setMaximumHeight(105)
        self.recent_log_view.setPlaceholderText("Refresh from the Audit Logs page.")
        layout.addWidget(recent_title)
        layout.addWidget(self.recent_log_view)
        layout.addStretch()
        return page

    def _snapshot_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        buttons = QHBoxLayout()
        self.create_button = QPushButton("Create snapshot")
        self.create_button.setObjectName("primary")
        self.verify_button = QPushButton("Verify")
        self.compare_button = QPushButton("Compare")
        self.snapshot_details_button = QPushButton("Metadata")
        self.export_button = QPushButton("Export")
        self.import_button = QPushButton("Import")
        self.rollback_button = QPushButton("Roll back")
        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("danger")
        for button in (
            self.create_button,
            self.verify_button,
            self.compare_button,
            self.snapshot_details_button,
            self.export_button,
            self.import_button,
            self.rollback_button,
            self.delete_button,
        ):
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.snapshot_table = QTableWidget(0, 9)
        self.snapshot_table.setHorizontalHeaderLabels(
            [
                "Created",
                "Description",
                "Created by",
                "Size",
                "Kernel",
                "Health",
                "Rollback",
                "Boot",
                "UUID",
            ]
        )
        self.snapshot_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.snapshot_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.snapshot_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.snapshot_table.setAlternatingRowColors(True)
        self.snapshot_table.verticalHeader().setVisible(False)
        self.snapshot_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.snapshot_table, 1)
        return page

    def _users_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        buttons = QHBoxLayout()
        self.user_create_button = QPushButton("Create ready user")
        self.user_create_button.setObjectName("primary")
        self.user_password_button = QPushButton("Reset password")
        self.user_lock_button = QPushButton("Lock / Unlock")
        self.user_autologin_button = QPushButton("Automatic login")
        self.user_delete_button = QPushButton("Delete")
        self.user_delete_button.setObjectName("danger")
        self.user_restore_button = QPushButton("Restore backup")
        self.user_refresh_button = QPushButton("Refresh")
        for button in (
            self.user_create_button,
            self.user_password_button,
            self.user_lock_button,
            self.user_autologin_button,
            self.user_delete_button,
            self.user_restore_button,
        ):
            buttons.addWidget(button)
        buttons.addStretch()
        buttons.addWidget(self.user_refresh_button)
        layout.addLayout(buttons)
        note = QLabel(
            "New accounts use CachyOS defaults and remain standard users. Their group "
            "membership is never rewritten. Verified applications and a clean FROZEN "
            "home template are prepared before creation is reported as complete."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.user_table = QTableWidget(0, 7)
        self.user_table.setHorizontalHeaderLabels(
            [
                "User",
                "Display name",
                "Type",
                "Groups",
                "Status",
                "Automatic login",
                "Home",
            ]
        )
        self.user_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.user_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.user_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.user_table.setAlternatingRowColors(True)
        self.user_table.verticalHeader().setVisible(False)
        self.user_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.user_table, 1)
        return page

    def _updates_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        title = QLabel("System and application updates")
        title.setObjectName("cardValue")
        description = QLabel(
            "Checking does not change the system. Applying updates runs only in THAWED, "
            "creates a rollback snapshot, verifies pacman, and publishes a new Golden."
        )
        description.setObjectName("muted")
        description.setWordWrap(True)
        row = QHBoxLayout()
        self.update_check_button = QPushButton("Check for updates")
        self.update_apply_button = QPushButton("Snapshot and update")
        self.update_apply_button.setObjectName("primary")
        self.app_status_button = QPushButton("Verify applications")
        self.app_install_button = QPushButton("Install / repair applications")
        row.addWidget(self.update_check_button)
        row.addWidget(self.update_apply_button)
        row.addWidget(self.app_status_button)
        row.addWidget(self.app_install_button)
        row.addStretch()
        card_layout.addWidget(title)
        card_layout.addWidget(description)
        card_layout.addLayout(row)
        layout.addWidget(card)
        self.update_view = QPlainTextEdit()
        self.update_view.setReadOnly(True)
        self.update_view.setPlaceholderText("No update check has been run yet.")
        layout.addWidget(self.update_view, 1)
        return page

    @staticmethod
    def _setting_spin(minimum: int, maximum: int, suffix: str = "") -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        if suffix:
            spin.setSuffix(suffix)
        return spin

    def _settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        grid = QGridLayout()

        snapshot_group = QGroupBox("Snapshots and FROZEN mode")
        snapshot_form = QFormLayout(snapshot_group)
        self.retention_spin = self._setting_spin(1, 1000)
        self.auto_snapshot_check = QCheckBox("Enabled")
        self.auto_interval_spin = self._setting_spin(15, 10080, " min")
        self.boot_failure_spin = self._setting_spin(2, 10, " attempts")
        snapshot_form.addRow("Retention count", self.retention_spin)
        snapshot_form.addRow("Automatic snapshot", self.auto_snapshot_check)
        snapshot_form.addRow("Automatic interval", self.auto_interval_spin)
        snapshot_form.addRow("Boot rollback limit", self.boot_failure_spin)

        system_group = QGroupBox("Updates, network, and logs")
        system_form = QFormLayout(system_group)
        self.update_checks_check = QCheckBox("Enabled")
        self.network_checks_check = QCheckBox("Allow online operations")
        self.log_retention_spin = self._setting_spin(100, 100000, " lines")
        system_form.addRow("Update checks", self.update_checks_check)
        system_form.addRow("Network", self.network_checks_check)
        system_form.addRow("Log retention", self.log_retention_spin)

        appearance_group = QGroupBox("Appearance and language")
        appearance_form = QFormLayout(appearance_group)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("Light", "light")
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        appearance_form.addRow("Theme", self.theme_combo)
        appearance_form.addRow("Language", self.language_combo)

        boot_group = QGroupBox("Next boot")
        boot_layout = QVBoxLayout(boot_group)
        self.thaw_once_button = QPushButton("Boot THAWED once")
        self.boot_frozen_button = QPushButton("Always use FROZEN")
        self.boot_thawed_button = QPushButton("THAWED maintenance mode")
        boot_layout.addWidget(self.thaw_once_button)
        boot_layout.addWidget(self.boot_frozen_button)
        boot_layout.addWidget(self.boot_thawed_button)

        grid.addWidget(snapshot_group, 0, 0)
        grid.addWidget(system_group, 0, 1)
        grid.addWidget(appearance_group, 1, 0)
        grid.addWidget(boot_group, 1, 1)
        layout.addLayout(grid)
        row = QHBoxLayout()
        self.settings_save_button = QPushButton("Validate and save settings")
        self.settings_save_button.setObjectName("primary")
        self.settings_refresh_button = QPushButton("Reload settings")
        row.addWidget(self.settings_save_button)
        row.addWidget(self.settings_refresh_button)
        row.addStretch()
        layout.addLayout(row)
        layout.addStretch()
        return page

    def _setup_page(self) -> QWidget:
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 4, 8, 0)
        layout.setSpacing(14)

        state_card = QFrame()
        state_card.setObjectName("card")
        state_layout = QVBoxLayout(state_card)
        state_title = QLabel("Independent setup")
        state_title.setObjectName("cardValue")
        self.setup_state_label = QLabel("Checking setup status…")
        self.setup_state_label.setObjectName("muted")
        self.setup_state_label.setWordWrap(True)
        self.setup_preflight_button = QPushButton("1. Run system preflight")
        state_layout.addWidget(state_title)
        state_layout.addWidget(self.setup_state_label)
        state_layout.addWidget(self.setup_preflight_button)
        layout.addWidget(state_card)

        stages = QGridLayout()
        stages.setSpacing(14)

        provision_group = QGroupBox("2. Install CachyFreeze")
        provision_form = QFormLayout(provision_group)
        install_note = QLabel(
            "Installs only the freeze engine and management app. User accounts are "
            "optional and can be managed separately from the Users page."
        )
        install_note.setWordWrap(True)
        self.setup_backup_check = QCheckBox("Recovery media and a restorable backup are ready")
        self.setup_disposable_check = QCheckBox(
            "Disposable test device: I accept the loss of all local data"
        )
        self.setup_start_button = QPushButton("Install CachyFreeze")
        self.setup_start_button.setObjectName("primary")
        provision_form.addRow(install_note)
        provision_form.addRow("", self.setup_backup_check)
        provision_form.addRow("", self.setup_disposable_check)
        provision_form.addRow("", self.setup_start_button)
        stages.addWidget(provision_group, 0, 0)

        finalize_group = QGroupBox("3. Enable FROZEN mode")
        finalize_form = QFormLayout(finalize_group)
        freeze_note = QLabel(
            "This step is independent from user creation. It protects maintenance mode, "
            "publishes Golden, and schedules the next boot as FROZEN. Use the fixed "
            "username cachyadmin with the password you set here to enter THAWED mode."
        )
        freeze_note.setWordWrap(True)
        self.setup_grub_username = QLabel("cachyadmin")
        self.setup_grub_username.setObjectName("cardValue")
        self.setup_grub_username.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.setup_grub_password = QLineEdit()
        self.setup_grub_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.setup_grub_confirm = QLineEdit()
        self.setup_grub_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.setup_finish_button = QPushButton("Publish Golden and enable FROZEN")
        self.setup_finish_button.setObjectName("primary")
        finalize_form.addRow(freeze_note)
        finalize_form.addRow("GRUB maintenance username", self.setup_grub_username)
        finalize_form.addRow("GRUB maintenance password", self.setup_grub_password)
        finalize_form.addRow("Confirm password", self.setup_grub_confirm)
        finalize_form.addRow("", self.setup_finish_button)
        stages.addWidget(finalize_group, 0, 1)
        layout.addLayout(stages)

        output_title = QLabel("Setup progress and error details")
        output_title.setObjectName("cardCaption")
        self.setup_output = QPlainTextEdit()
        self.setup_output.setReadOnly(True)
        self.setup_output.setMaximumBlockCount(2000)
        self.setup_output.setMinimumHeight(140)
        self.setup_output.setPlaceholderText("Preflight and setup output appears here.")
        layout.addWidget(output_title)
        layout.addWidget(self.setup_output)
        layout.addStretch()
        page.setWidget(body)
        return page

    def _logs_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        row = QHBoxLayout()
        description = QLabel("Shows the latest 200 root operations with level and context.")
        description.setObjectName("muted")
        self.logs_button = QPushButton("Refresh logs")
        row.addWidget(description)
        row.addStretch()
        row.addWidget(self.logs_button)
        layout.addLayout(row)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_view, 1)
        return page

    def _connect(self) -> None:
        for index, button in enumerate(self.nav_buttons):
            button.clicked.connect(
                lambda _checked, page=index: self._select_page(page, self.page_titles[page])
            )
        self.theme_button.clicked.connect(self._toggle_theme)
        self.refresh_button.clicked.connect(self._refresh_current_page)
        self.thaw_button.clicked.connect(self._confirm_thaw)
        self.freeze_button.clicked.connect(self._confirm_freeze)
        self.reboot_button.clicked.connect(self._confirm_reboot)
        self.health_button.clicked.connect(lambda: self.backend.run("health"))
        self.create_button.clicked.connect(self._create_snapshot)
        self.verify_button.clicked.connect(self._verify_snapshot)
        self.compare_button.clicked.connect(self._compare_snapshots)
        self.snapshot_details_button.clicked.connect(self._snapshot_details)
        self.delete_button.clicked.connect(self._delete_snapshot)
        self.rollback_button.clicked.connect(self._rollback_snapshot)
        self.export_button.clicked.connect(self._export_snapshot)
        self.import_button.clicked.connect(self._import_snapshot)
        self.logs_button.clicked.connect(lambda: self.backend.run("logs"))
        self.user_refresh_button.clicked.connect(lambda: self.backend.run("user-list"))
        self.user_create_button.clicked.connect(self._create_user)
        self.user_password_button.clicked.connect(self._reset_user_password)
        self.user_lock_button.clicked.connect(self._toggle_user_lock)
        self.user_autologin_button.clicked.connect(self._toggle_autologin)
        self.user_delete_button.clicked.connect(self._delete_user)
        self.user_restore_button.clicked.connect(self._restore_user)
        self.update_check_button.clicked.connect(lambda: self.backend.run("updates-check"))
        self.update_apply_button.clicked.connect(self._confirm_update)
        self.app_status_button.clicked.connect(lambda: self.backend.run("applications-status"))
        self.app_install_button.clicked.connect(self._confirm_application_install)
        self.settings_refresh_button.clicked.connect(lambda: self.backend.run("settings-get"))
        self.settings_save_button.clicked.connect(self._save_settings)
        self.thaw_once_button.clicked.connect(self._confirm_thaw_once)
        self.boot_frozen_button.clicked.connect(self._confirm_freeze)
        self.boot_thawed_button.clicked.connect(self._confirm_thaw)
        self.setup_preflight_button.clicked.connect(lambda: self.backend.run("setup-preflight"))
        self.setup_start_button.clicked.connect(self._start_setup)
        self.setup_finish_button.clicked.connect(self._finish_setup)
        self.backend.busy_changed.connect(self._busy_changed)
        self.backend.status_changed.connect(self._status_changed)
        self.backend.snapshots_changed.connect(self._snapshots_changed)
        self.backend.logs_changed.connect(self._logs_changed)
        self.backend.users_changed.connect(self._users_changed)
        self.backend.result_ready.connect(self._result_ready)
        self.backend.operation_finished.connect(self._operation_finished)
        self.backend.operation_output.connect(self._operation_output)

    def _refresh_current_page(self) -> None:
        action = "setup-status" if self.pages.currentIndex() == 6 else "status"
        self.backend.run(action)

    def _select_page(self, index: int, title: str) -> None:
        self.pages.setCurrentIndex(index)
        self.page_title.setText(title)
        if index == 1:
            self.backend.refresh_local()
        elif index == 2:
            self.backend.run("user-list")
        elif index == 3:
            self.backend.run("updates-check")
        elif index == 4:
            self.backend.run("logs")
        elif index == 5:
            self.backend.run("settings-get")
        elif index == 6:
            self.backend.run("setup-status")

    def _busy_changed(self, busy: bool) -> None:
        self.progress.setVisible(busy)
        for button in (
            self.refresh_button,
            self.thaw_button,
            self.freeze_button,
            self.reboot_button,
            self.health_button,
            self.create_button,
            self.verify_button,
            self.compare_button,
            self.snapshot_details_button,
            self.delete_button,
            self.rollback_button,
            self.export_button,
            self.import_button,
            self.logs_button,
            self.user_create_button,
            self.user_password_button,
            self.user_lock_button,
            self.user_autologin_button,
            self.user_delete_button,
            self.user_restore_button,
            self.user_refresh_button,
            self.update_check_button,
            self.update_apply_button,
            self.app_status_button,
            self.app_install_button,
            self.settings_save_button,
            self.settings_refresh_button,
            self.thaw_once_button,
            self.boot_frozen_button,
            self.boot_thawed_button,
            self.setup_preflight_button,
            self.setup_start_button,
            self.setup_finish_button,
        ):
            button.setDisabled(busy)
        self.statusBar().showMessage("Operation in progress…" if busy else "Ready")

    def _status_changed(self, status: dict[str, Any]) -> None:
        mode = str(status.get("running_mode", "unknown"))
        mode_labels = {
            "frozen": ("FROZEN", "#5865f2"),
            "thawed": ("THAWED — MAINTENANCE", "#b76e18"),
            "unknown": ("UNKNOWN", "#da373c"),
        }
        label, color = mode_labels.get(mode, mode_labels["unknown"])
        self.mode_badge.setText(label)
        self.mode_badge.setStyleSheet(
            f"padding: 7px 12px; border-radius: 10px; background: {color}; "
            "color: white; font-weight: 700;"
        )
        self.mode_card.value.setText(label)
        self.mode_card.detail.setText(
            f"Next boot: {str(status.get('scheduled_mode', 'unknown')).upper()}"
        )
        last = status.get("last_snapshot")
        if isinstance(last, dict):
            self.snapshot_card.value.setText(_date(str(last.get("created_at", ""))))
            self.snapshot_card.detail.setText(str(last.get("description", "")))
        else:
            self.snapshot_card.value.setText("None yet")
            self.snapshot_card.detail.setText(
                "Create a snapshot before the first Golden publication."
            )
        usage = shutil.disk_usage("/")
        self.disk_card.value.setText(f"{round(usage.used / usage.total * 100)}%")
        self.disk_card.detail.setText(f"{_human_bytes(usage.used)} / {_human_bytes(usage.total)}")
        ready = bool(status.get("golden_present")) and bool(status.get("active_present"))
        pending = bool(status.get("transaction_pending"))
        self.health_card.value.setText("Attention" if pending or not ready else "Ready")
        self.health_card.detail.setText(
            "An interrupted operation was detected."
            if pending
            else "Golden and Active verified."
            if ready
            else "Golden or Active is not ready yet."
        )
        count = int(status.get("snapshot_count", 0))
        self.count_card.value.setText(str(count))
        self.count_card.detail.setText("Managed by the automatic retention policy.")
        alerts = []
        if pending:
            alerts.append("An interrupted snapshot operation requires recovery.")
        attempts = int(status.get("boot_attempts", 0))
        if attempts:
            alerts.append(
                f"Unconfirmed boot attempt: {attempts}/{status.get('boot_failure_limit', 3)}"
            )
        if status.get("failed_golden_present"):
            alerts.append("Failed Golden retained for diagnosis after automatic rollback.")
        self.alert_label.setText("  •  ".join(alerts) if alerts else "No warnings.")

    def _snapshots_changed(self, snapshots: list[dict[str, Any]]) -> None:
        self.snapshot_table.setRowCount(len(snapshots))
        for row, snapshot in enumerate(snapshots):
            values = (
                _date(str(snapshot.get("created_at", ""))),
                str(snapshot.get("description", "")),
                str(snapshot.get("created_by", "")),
                _human_bytes(int(snapshot.get("apparent_size_bytes", 0))),
                str(snapshot.get("kernel", "")),
                str(snapshot.get("health", "unknown")),
                str(snapshot.get("rollback_count", 0)),
                "Yes" if snapshot.get("bootable") else "No",
                str(snapshot.get("btrfs_uuid", "")),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, snapshot.get("snapshot_id"))
                self.snapshot_table.setItem(row, column, item)
        self.snapshot_table.resizeColumnsToContents()

    def _logs_changed(self, logs: list[dict[str, Any]]) -> None:
        lines = []
        for entry in logs:
            context = entry.get("context", {})
            lines.append(
                f"{_date(str(entry.get('timestamp', '')))}  "
                f"{str(entry.get('level', '')).ljust(7)}  "
                f"{entry.get('action', '')}: {entry.get('message', '')}  "
                f"{context if context else ''}"
            )
        self.log_view.setPlainText("\n".join(lines))
        self.recent_log_view.setPlainText("\n".join(lines[-5:]))

    def _users_changed(self, users: list[dict[str, Any]]) -> None:
        self.user_table.setRowCount(len(users))
        for row, user in enumerate(users):
            values = (
                str(user.get("username", "")),
                str(user.get("display_name", "")),
                "Administrator" if user.get("administrator") else "Standard",
                ", ".join(str(group) for group in user.get("groups", [])),
                "Locked" if user.get("locked") else "Unlocked",
                "Enabled" if user.get("autologin") else "Disabled",
                str(user.get("home", "")),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, user)
                self.user_table.setItem(row, column, item)
        self.user_table.resizeColumnsToContents()

    def _selected_user(self) -> dict[str, Any] | None:
        row = self.user_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select a user", "Select a user from the table first.")
            return None
        item = self.user_table.item(row, 0)
        value = item.data(Qt.ItemDataRole.UserRole) if item else None
        return value if isinstance(value, dict) else None

    def _create_user(self) -> None:
        self.pending_user_create_check = True
        if not self.backend.run("applications-status"):
            self.pending_user_create_check = False

    def _show_create_user_dialog(self) -> None:
        dialog = UserDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        password = dialog.password.text()
        if password != dialog.password_confirm.text():
            QMessageBox.warning(self, "Password mismatch", "The passwords do not match.")
            return
        username = dialog.username.text().strip()
        display_name = dialog.display_name.text().strip()
        if not username or not display_name or not password:
            QMessageBox.warning(self, "Missing information", "All user fields are required.")
            return
        if re.fullmatch(r"[a-z][a-z0-9_-]{1,30}", username) is None:
            QMessageBox.warning(
                self,
                "Invalid username",
                "Use 2-31 lowercase letters, digits, underscores, or hyphens. "
                "The first character must be a letter.",
            )
            return
        if not self._employee_password_is_valid(password):
            QMessageBox.warning(
                self,
                "Invalid password",
                "The password must contain 4-256 characters and cannot contain a colon.",
            )
            return
        freeze_after_create = dialog.freeze_after_create.isChecked()
        summary = f"Create the standard user '{username}' and prepare all verified applications?"
        if freeze_after_create:
            summary += "\n\nGolden will then be published and the next boot scheduled as FROZEN."
        if (
            QMessageBox.question(self, "Create application-ready user", summary)
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.pending_user_freeze = freeze_after_create
        self.pending_autologin_user = username if dialog.autologin.isChecked() else None
        started = self.backend.run("user-create", username, display_name, secret=password)
        if not started:
            self.pending_user_freeze = False
            self.pending_autologin_user = None

    def _reset_user_password(self) -> None:
        user = self._selected_user()
        if user is None:
            return
        password, accepted = QInputDialog.getText(
            self,
            "Reset password",
            f"New password for {user['username']}:",
            QLineEdit.EchoMode.Password,
        )
        if not accepted or not password:
            return
        confirmation, accepted = QInputDialog.getText(
            self,
            "Confirm password",
            "Enter the new password again:",
            QLineEdit.EchoMode.Password,
        )
        if accepted and password == confirmation:
            self.backend.run("user-password", str(user["username"]), secret=password)
        elif accepted:
            QMessageBox.warning(self, "Password mismatch", "The passwords do not match.")

    def _toggle_user_lock(self) -> None:
        user = self._selected_user()
        if user is None:
            return
        if user.get("administrator"):
            QMessageBox.warning(
                self,
                "Protected administrator",
                "Administrator accounts cannot be locked from CachyFreeze.",
            )
            return
        action = "user-unlock" if user.get("locked") else "user-lock"
        verb = "unlocked" if user.get("locked") else "locked"
        if (
            QMessageBox.question(
                self, "Change account status", f"Should {user['username']} be {verb}?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.backend.run(action, str(user["username"]))

    def _toggle_autologin(self) -> None:
        user = self._selected_user()
        if user is None:
            return
        if user.get("administrator"):
            QMessageBox.warning(
                self,
                "Protected administrator",
                "Automatic login cannot be enabled for an administrator.",
            )
            return
        if user.get("autologin"):
            self.backend.run("user-autologin")
        else:
            self.backend.run("user-autologin", str(user["username"]))

    def _delete_user(self) -> None:
        user = self._selected_user()
        if user is None:
            return
        if user.get("administrator"):
            QMessageBox.warning(
                self,
                "Protected administrator",
                "Administrator accounts cannot be deleted from CachyFreeze.",
            )
            return
        if (
            QMessageBox.warning(
                self,
                "Delete user",
                f"A root-only recovery backup will be created before deleting "
                f"{user['username']} and its home directory. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.backend.run("user-delete", str(user["username"]))

    def _restore_user(self) -> None:
        backup_id, accepted = QInputDialog.getText(
            self,
            "Restore user backup",
            "Backup ID shown by the delete operation:",
        )
        if accepted and backup_id.strip():
            self.backend.run("user-restore", backup_id.strip())

    def _selected_snapshot_id(self) -> str | None:
        row = self.snapshot_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select a snapshot", "Select a snapshot first.")
            return None
        item = self.snapshot_table.item(row, 0)
        return str(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def _snapshot_details(self) -> None:
        snapshot_id = self._selected_snapshot_id()
        if snapshot_id is None:
            return
        snapshot = next(
            (item for item in self.backend.snapshots if item.get("snapshot_id") == snapshot_id),
            None,
        )
        if snapshot is None:
            return
        fields = (
            ("Identity", "snapshot_id"),
            ("Btrfs UUID", "btrfs_uuid"),
            ("Parent UUID", "parent_uuid"),
            ("Created", "created_at"),
            ("Kernel", "kernel"),
            ("Apparent size", "apparent_size_bytes"),
            ("Exclusive size", "exclusive_size_bytes"),
            ("Description", "description"),
            ("Created by", "created_by"),
            ("Frozen", "frozen"),
            ("Bootable", "bootable"),
            ("Metadata checksum", "checksum"),
            ("Rollback count", "rollback_count"),
            ("Creation duration (ms)", "creation_duration_ms"),
            ("Health", "health"),
            ("Kaynak", "source_subvolume"),
        )
        QMessageBox.information(
            self,
            "Snapshot metadata",
            "\n".join(f"{label}: {snapshot.get(key, '')}" for label, key in fields),
        )

    def _create_snapshot(self) -> None:
        description, accepted = QInputDialog.getText(
            self, "Create snapshot", "Description (required):"
        )
        if accepted and description.strip():
            self.backend.run("snapshot-create", description.strip())

    def _verify_snapshot(self) -> None:
        if snapshot_id := self._selected_snapshot_id():
            self.backend.run("snapshot-verify", snapshot_id)

    def _compare_snapshots(self) -> None:
        if len(self.backend.snapshots) < 2:
            QMessageBox.information(
                self, "Compare snapshots", "At least two snapshots are required."
            )
            return
        choices = [
            f"{snapshot['snapshot_id']} — {snapshot.get('description', '')}"
            for snapshot in self.backend.snapshots
        ]
        older, accepted = QInputDialog.getItem(
            self, "Older snapshot", "Comparison start:", choices, editable=False
        )
        if not accepted:
            return
        newer, accepted = QInputDialog.getItem(
            self, "Newer snapshot", "Comparison end:", choices, editable=False
        )
        if accepted:
            older_id = older.split(" — ", 1)[0]
            newer_id = newer.split(" — ", 1)[0]
            if older_id == newer_id:
                QMessageBox.warning(self, "Same snapshot", "Select two different snapshots.")
                return
            self.backend.run("snapshot-compare", older_id, newer_id)

    def _delete_snapshot(self) -> None:
        snapshot_id = self._selected_snapshot_id()
        if (
            snapshot_id
            and QMessageBox.warning(
                self,
                "Snapshot sil",
                "The selected snapshot will be permanently deleted. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.backend.run("snapshot-delete", snapshot_id)

    def _rollback_snapshot(self) -> None:
        snapshot_id = self._selected_snapshot_id()
        if (
            snapshot_id
            and QMessageBox.warning(
                self,
                "Roll back snapshot",
                "The selected snapshot will become the new Golden. After verification, "
                "the next boot will be FROZEN.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.backend.run("snapshot-rollback", snapshot_id)

    def _export_snapshot(self) -> None:
        if snapshot_id := self._selected_snapshot_id():
            self.backend.run("snapshot-export", snapshot_id)

    def _import_snapshot(self) -> None:
        filename, accepted = QInputDialog.getText(
            self,
            "Snapshot import",
            "Name of the .btrfs file in /var/lib/cachy-freeze/exports:",
        )
        if accepted and filename.strip():
            self.backend.run("snapshot-import", filename.strip())

    @staticmethod
    def _password_is_strong(password: str) -> bool:
        classes = sum(
            bool(re.search(pattern, password))
            for pattern in (r"[a-z]", r"[A-Z]", r"[0-9]", r"[^A-Za-z0-9]")
        )
        return (
            12 <= len(password) <= 256
            and classes >= 3
            and not any(character in password for character in ("\n", "\r", "\x00", ":"))
        )

    @staticmethod
    def _employee_password_is_valid(password: str) -> bool:
        return 4 <= len(password) <= 256 and not any(
            character in password for character in ("\n", "\r", "\x00", ":")
        )

    def _start_setup(self) -> None:
        if not self.setup_preflight_ok:
            QMessageBox.warning(
                self,
                "Preflight required",
                "Run system preflight successfully before installation.",
            )
            return
        backup_ready = self.setup_backup_check.isChecked()
        disposable_accepted = self.setup_disposable_check.isChecked()
        if backup_ready == disposable_accepted:
            QMessageBox.warning(
                self,
                "Recovery choice required",
                "Confirm recovery media and backup readiness, or accept all local data "
                "loss on this disposable test device.",
            )
            return
        if disposable_accepted:
            disposable_answer = QMessageBox.warning(
                self,
                "Disposable test device — data loss risk",
                "This device may fail to boot and require reformatting. Do you accept "
                "permanent loss of all local data without recovery media or backup?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if disposable_answer != QMessageBox.StandardButton.Yes:
                return
        answer = QMessageBox.warning(
            self,
            "Start installation",
            "Packages will be installed and Btrfs, initramfs, and GRUB configured. "
            "Do not interrupt power. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.setup_output.clear()
        self.backend.run("setup-install")

    def _finish_setup(self) -> None:
        password = self.setup_grub_password.text()
        if password != self.setup_grub_confirm.text():
            QMessageBox.warning(self, "Password error", "The GRUB passwords do not match.")
            return
        if not self._password_is_strong(password):
            QMessageBox.warning(
                self,
                "Weak GRUB password",
                "Set a password of 12-256 characters with at least three character "
                "classes. The fixed GRUB username is cachyadmin.",
            )
            return
        answer = QMessageBox.warning(
            self,
            "Publish Golden and enable FROZEN",
            "Existing managed-user templates will be refreshed, Golden published, and the "
            "next boot set to FROZEN. Do not power off during the operation.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self.backend.run("setup-freeze", secret=password):
            self.setup_grub_password.clear()
            self.setup_grub_confirm.clear()

    def _operation_output(self, action: str, output: str) -> None:
        if action.startswith("setup-") and output.rstrip():
            self.setup_output.appendPlainText(output.rstrip())

    def _confirm_thaw(self) -> None:
        if (
            QMessageBox.question(
                self,
                "Switch to THAWED",
                "Changes made after the next boot will persist. Continue?",
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.backend.run("thaw")

    def _confirm_thaw_once(self) -> None:
        if (
            QMessageBox.question(
                self,
                "Boot THAWED once",
                "Only the next boot will be THAWED; the following boot automatically "
                "returns to FROZEN. Continue?",
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.backend.run("thaw-once")

    def _confirm_update(self) -> None:
        if (
            QMessageBox.warning(
                self,
                "Update system",
                "This creates a rollback snapshot in THAWED, applies pacman updates, "
                "verifies them, and publishes a new Golden. Do not interrupt power. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.backend.run("updates-apply")

    def _confirm_application_install(self) -> None:
        if (
            QMessageBox.warning(
                self,
                "Install applications",
                "This runs only in THAWED, creates a rollback snapshot, verifies packages "
                "and MicroSIP, then publishes a new Golden. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.backend.run("applications-install")

    def _save_settings(self) -> None:
        theme = str(self.theme_combo.currentData())
        self._apply_theme(theme)
        self.backend.run(
            "settings-set",
            str(self.retention_spin.value()),
            str(self.auto_snapshot_check.isChecked()).lower(),
            str(self.auto_interval_spin.value()),
            str(self.update_checks_check.isChecked()).lower(),
            str(self.network_checks_check.isChecked()).lower(),
            str(self.boot_failure_spin.value()),
            str(self.log_retention_spin.value()),
            str(self.language_combo.currentData()),
            theme,
        )

    def _confirm_freeze(self) -> None:
        if (
            QMessageBox.warning(
                self,
                "Publish Golden and freeze",
                "The maintenance system will be archived as a snapshot and new "
                "Golden/Active subvolumes published atomically. Do not power off.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.backend.run("freeze")

    def _confirm_reboot(self) -> None:
        if (
            QMessageBox.question(self, "Reboot", "Reboot the computer now?")
            == QMessageBox.StandardButton.Yes
        ):
            self.backend.run("reboot")

    def _operation_finished(self, action: str, success: bool, message: str) -> None:
        self.statusBar().showMessage(message, 8000)
        if action == "applications-status" and not success:
            self.pending_user_create_check = False
        if action == "user-create" and not success:
            self.pending_autologin_user = None
            self.pending_user_freeze = False
        if action == "user-autologin" and not success:
            self.pending_autologin_user = None
            self.pending_user_freeze = False
        if not success and "iptal edildi" not in message.lower():
            QMessageBox.critical(self, "CachyFreeze Error", message)
        elif success and action == "setup-freeze":
            answer = QMessageBox.question(
                self,
                "Setup complete",
                f"{message}\n\nReboot now for the first FROZEN test?",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.backend.run("reboot")
            else:
                self.backend.run("setup-status")
        elif success and action in {
            "freeze",
            "thaw",
            "thaw-once",
            "snapshot-rollback",
            "updates-apply",
            "applications-install",
        }:
            answer = QMessageBox.question(
                self,
                "Operation complete",
                f"{message}\n\nReboot now to apply the change?",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.backend.run("reboot")
        if success and action == "setup-install":
            QMessageBox.information(
                self,
                "Installation complete",
                "CachyFreeze is installed in THAWED mode. You may enable FROZEN now or "
                "create users first; the two operations are independent.",
            )
            self.backend.run("setup-status")
        if success and action == "user-create":
            pending = self.pending_autologin_user
            self.pending_autologin_user = None
            if pending:
                self.backend.run("user-autologin", pending)
                return
            if self.pending_user_freeze:
                self.pending_user_freeze = False
                self.backend.run("freeze")
                return
        if success and action == "user-autologin" and self.pending_user_freeze:
            self.pending_user_freeze = False
            self.backend.run("freeze")
            return
        if success and action.startswith("user-") and action != "user-list":
            self.backend.run("user-list")

    def _result_ready(self, action: str, result: object) -> None:
        if not isinstance(result, dict):
            return
        if action == "setup-preflight":
            self.setup_preflight_ok = True
            self.setup_state_label.setText(
                "Preflight passed: the UEFI + Btrfs + GRUB layout is supported."
            )
            self.setup_output.appendPlainText(
                "Preflight passed\n"
                f"Root device: {result.get('root_device', '—')}\n"
                f"Root subvolume: {result.get('current_subvolume', '—')}\n"
                f"Firmware: {result.get('firmware', '—')} / "
                f"Filesystem: {result.get('filesystem', '—')}"
            )
        elif action == "setup-status":
            phase = str(result.get("phase", "unknown"))
            labels = {
                "ready": "Ready to install. Run preflight, confirm recovery, and install.",
                "partial": (
                    "An interrupted installation was detected. Preserve the log and rerun "
                    "installation after preflight."
                ),
                "installed": (
                    "CachyFreeze is installed in THAWED mode. User creation is optional; "
                    "FROZEN can be enabled at any time."
                ),
                "complete": "Setup is complete. The next boot is ready for FROZEN.",
            }
            employee = str(result.get("employee_user", ""))
            detail = labels.get(phase, "Setup status is unknown; inspect the logs.")
            if employee:
                detail += f" Managed user: {employee}."
            self.setup_state_label.setText(detail)
        elif action == "snapshot-compare":
            paths = result.get("changed_paths", [])
            preview = "\n".join(str(path) for path in paths[:30])
            if result.get("truncated"):
                preview += "\n…"
            QMessageBox.information(
                self,
                "Snapshot comparison",
                f"Changed paths: {result.get('changed_path_count', 0)}\n\n{preview}",
            )
        elif action == "snapshot-verify":
            healthy = bool(result.get("healthy"))
            errors = "\n".join(str(item) for item in result.get("errors", []))
            QMessageBox.information(
                self,
                "Snapshot verification",
                f"Status: {'Healthy' if healthy else 'Unhealthy'}\n"
                f"Metadata SHA-256: {result.get('metadata_checksum', '')}\n"
                f"Btrfs send SHA-256: {result.get('stream_sha256', '')}\n"
                + (f"\nErrors:\n{errors}" if errors else ""),
            )
        elif action == "health":
            healthy = bool(result.get("healthy"))
            self.health_card.value.setText("Ready" if healthy else "Error")
            self.health_card.detail.setText(
                "Btrfs counters and all snapshots verified."
                if healthy
                else "An unhealthy snapshot or Btrfs device error was found."
            )
            QMessageBox.information(
                self,
                "System health scan",
                "Healthy" if healthy else f"Attention required:\n{result}",
            )
        elif action == "updates-check":
            packages = [str(item) for item in result.get("packages", [])]
            count = int(result.get("count", 0))
            if not result.get("enabled", True):
                reason = result.get("reason")
                message = (
                    "Online checks are disabled in settings."
                    if reason == "network"
                    else "Update checks are disabled in settings."
                )
                self.update_view.setPlainText(message)
            else:
                self.update_view.setPlainText(
                    "\n".join(packages) if packages else "The system is up to date."
                )
            self.update_card.value.setText(str(count))
            self.update_card.detail.setText("pending packages")
        elif action in {"applications-status", "applications-install"}:
            applications = result.get("applications", [])
            lines = [
                f"{'✓' if item.get('installed') else '✗'}  {item.get('name', '')}"
                + (f"  {item.get('version')}" if item.get("version") else "")
                for item in applications
            ]
            self.update_view.setPlainText("\n".join(lines))
            if action == "applications-status" and self.pending_user_create_check:
                self.pending_user_create_check = False
                missing = [
                    str(item.get("name", "Unknown application"))
                    for item in applications
                    if not item.get("installed")
                ]
                if not result.get("all_installed") or missing:
                    if not missing:
                        missing.append("Application readiness could not be verified")
                    self._select_page(3, self.page_titles[3])
                    QMessageBox.warning(
                        self,
                        "Applications required",
                        "Install or repair the required applications before creating a "
                        "ready user.\n\nMissing or unhealthy:\n• " + "\n• ".join(missing),
                    )
                    return
                self._show_create_user_dialog()
        elif action in {"settings-get", "settings-set"}:
            self.retention_spin.setValue(int(result.get("retention_count", 20)))
            self.auto_snapshot_check.setChecked(bool(result.get("auto_snapshot_enabled")))
            self.auto_interval_spin.setValue(
                int(result.get("auto_snapshot_interval_minutes", 1440))
            )
            self.update_checks_check.setChecked(bool(result.get("update_checks_enabled", True)))
            self.network_checks_check.setChecked(bool(result.get("network_online_checks", True)))
            self.boot_failure_spin.setValue(int(result.get("boot_failure_limit", 3)))
            self.log_retention_spin.setValue(int(result.get("log_retention_lines", 5000)))
            language = self.language_combo.findData(str(result.get("language", "en")))
            if language >= 0:
                self.language_combo.setCurrentIndex(language)
            theme = str(result.get("theme", self.settings.value("theme", "dark")))
            theme_index = self.theme_combo.findData(theme)
            if theme_index >= 0:
                self.theme_combo.setCurrentIndex(theme_index)
                self._apply_theme(theme)
        elif action == "user-delete":
            QMessageBox.information(
                self,
                "User backup created",
                f"Restore ID: {result.get('backup_id', '')}",
            )

    def _toggle_theme(self) -> None:
        current = str(self.settings.value("theme", "dark"))
        self._apply_theme("light" if current == "dark" else "dark")

    def _apply_theme(self, theme: str) -> None:
        application = QApplication.instance()
        assert application is not None
        application.setStyleSheet(LIGHT_STYLE if theme == "light" else DARK_STYLE)
        self.settings.setValue("theme", theme)
