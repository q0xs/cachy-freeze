from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cachy_freeze_gui.backend import BackendClient  # noqa: E402
from cachy_freeze_gui.window import MainWindow  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402


class SetupGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.backend = BackendClient()
        self.backend.refresh_local = Mock()
        self.backend.run = Mock(return_value=True)
        self.window = MainWindow(self.backend)

    def tearDown(self) -> None:
        self.window.close()
        self.application.processEvents()

    def test_setup_page_contract_and_password_policy(self) -> None:
        self.assertEqual(self.window.pages.count(), 7)
        self.assertEqual(self.window.setup_username.placeholderText(), "ornek_kullanici")
        self.assertTrue(self.window._password_is_strong("Correct-Horse-42"))
        self.assertFalse(self.window._password_is_strong("short"))
        self.assertFalse(self.window._password_is_strong("Colon:Password42"))

    def test_provision_requires_preflight(self) -> None:
        with patch("cachy_freeze_gui.window.QMessageBox.warning") as warning:
            self.window._start_setup()

        warning.assert_called_once()
        self.backend.run.assert_not_called()

    def test_provision_sends_secret_only_through_secret_channel(self) -> None:
        self.window.setup_preflight_ok = True
        self.window.setup_backup_check.setChecked(True)
        self.window.setup_username.setText("qa_user")
        self.window.setup_display_name.setText("QA User")
        self.window.setup_password.setText("Correct-Horse-42")
        self.window.setup_password_confirm.setText("Correct-Horse-42")

        with patch(
            "cachy_freeze_gui.window.QMessageBox.warning",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window._start_setup()

        self.backend.run.assert_called_once_with(
            "setup-provision",
            "qa_user",
            "QA User",
            secret="Correct-Horse-42",
        )
        self.assertEqual(self.window.setup_password.text(), "")
        self.assertEqual(self.window.setup_password_confirm.text(), "")

    def test_finalize_requires_all_live_checks(self) -> None:
        self.window.setup_grub_password.setText("Correct-Horse-42")
        self.window.setup_grub_confirm.setText("Correct-Horse-42")

        with patch("cachy_freeze_gui.window.QMessageBox.warning") as warning:
            self.window._finish_setup()

        warning.assert_called_once()
        self.backend.run.assert_not_called()

    def test_finalize_sends_grub_secret_and_clears_fields(self) -> None:
        self.window.setup_apps_check.setChecked(True)
        self.window.setup_audio_check.setChecked(True)
        self.window.setup_admin_check.setChecked(True)
        self.window.setup_grub_password.setText("Correct-Horse-42")
        self.window.setup_grub_confirm.setText("Correct-Horse-42")

        with patch(
            "cachy_freeze_gui.window.QMessageBox.warning",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window._finish_setup()

        self.backend.run.assert_called_once_with("setup-finalize", secret="Correct-Horse-42")
        self.assertEqual(self.window.setup_grub_password.text(), "")
        self.assertEqual(self.window.setup_grub_confirm.text(), "")

    def test_successful_preflight_unlocks_setup_flow(self) -> None:
        self.window._result_ready(
            "setup-preflight",
            {
                "root_device": "/dev/sda2",
                "current_subvolume": "@",
                "firmware": "UEFI",
                "filesystem": "btrfs",
            },
        )

        self.assertTrue(self.window.setup_preflight_ok)
        self.assertIn("/dev/sda2", self.window.setup_output.toPlainText())
        self.assertIn("UEFI", self.window.setup_state_label.text())


if __name__ == "__main__":
    unittest.main()
