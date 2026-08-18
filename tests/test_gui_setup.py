from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cachy_freeze_gui.backend import BackendClient  # noqa: E402
from cachy_freeze_gui.window import MainWindow, UserDialog  # noqa: E402
from PyQt6.QtCore import Qt  # noqa: E402
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
        self.assertEqual(self.window.setup_start_button.text(), "Install CachyFreeze")
        self.assertEqual(self.window.setup_grub_username.text(), "cachyadmin")
        self.assertTrue(
            self.window.setup_grub_username.textInteractionFlags()
            & Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.assertTrue(self.window._password_is_strong("Correct-Horse-42"))
        self.assertFalse(self.window._password_is_strong("short"))
        self.assertFalse(self.window._password_is_strong("Colon:Password42"))

    def test_helper_does_not_require_a_managed_user_to_freeze(self) -> None:
        helper = (Path(__file__).parents[1] / "app/cachy-freeze-manager-helper").read_text()
        freeze_case = helper.split("setup-freeze)", 1)[1].split(";;", 1)[0]
        self.assertNotIn("/etc/cachy-employee.conf", freeze_case)
        self.assertIn("finalize-setup.sh", freeze_case)

    def test_regular_freeze_requires_grub_protection(self) -> None:
        helper = (Path(__file__).parents[1] / "app/cachy-freeze-manager-helper").read_text()
        freeze_case = helper.split("  freeze)", 1)[1].split(";;", 1)[0]
        self.assertIn("/etc/cachy-freeze-grub-auth.conf", freeze_case)

    def test_provision_requires_preflight(self) -> None:
        with patch("cachy_freeze_gui.window.QMessageBox.warning") as warning:
            self.window._start_setup()

        warning.assert_called_once()
        self.backend.run.assert_not_called()

    def test_install_is_independent_from_user_creation(self) -> None:
        self.window.setup_preflight_ok = True
        self.window.setup_backup_check.setChecked(True)

        with patch(
            "cachy_freeze_gui.window.QMessageBox.warning",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window._start_setup()

        self.backend.run.assert_called_once_with("setup-install")

    def test_disposable_device_requires_explicit_data_loss_confirmation(self) -> None:
        self.window.setup_preflight_ok = True
        self.window.setup_disposable_check.setChecked(True)

        with patch(
            "cachy_freeze_gui.window.QMessageBox.warning",
            return_value=QMessageBox.StandardButton.Cancel,
        ) as warning:
            self.window._start_setup()

        warning.assert_called_once()
        self.assertIn("data loss", warning.call_args.args[1])
        self.backend.run.assert_not_called()

    def test_disposable_device_can_provision_after_two_confirmations(self) -> None:
        self.window.setup_preflight_ok = True
        self.window.setup_disposable_check.setChecked(True)

        with patch(
            "cachy_freeze_gui.window.QMessageBox.warning",
            side_effect=[QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.Yes],
        ):
            self.window._start_setup()

        self.backend.run.assert_called_once_with("setup-install")

    def test_freeze_is_independent_and_uses_secret_channel(self) -> None:
        self.window.setup_grub_password.setText("Correct-Horse-42")
        self.window.setup_grub_confirm.setText("Correct-Horse-42")

        with patch(
            "cachy_freeze_gui.window.QMessageBox.warning",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window._finish_setup()

        self.backend.run.assert_called_once_with("setup-freeze", secret="Correct-Horse-42")
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

    def test_ready_user_dialog_matches_username_contract(self) -> None:
        dialog = UserDialog(self.window)
        self.assertEqual(dialog.username.placeholderText(), "wrw21166")
        self.assertTrue(dialog.freeze_after_create.isChecked())
        self.assertIn("non-administrator", dialog.layout().itemAt(0).widget().text())
        dialog.close()

    def test_successful_user_creation_can_schedule_frozen_without_reboot(self) -> None:
        self.window.pending_user_freeze = True
        self.window._operation_finished("user-create", True, "created")

        self.backend.run.assert_called_once_with("freeze")
        self.assertFalse(self.window.pending_user_freeze)
        self.assertNotIn(
            "reboot",
            [call.args[0] for call in self.backend.run.call_args_list],
        )

    def test_autologin_then_freeze_sequence_uses_only_in_memory_state(self) -> None:
        self.window.pending_autologin_user = "person_01"
        self.window.pending_user_freeze = True

        self.window._operation_finished("user-create", True, "created")
        self.backend.run.assert_called_once_with("user-autologin", "person_01")
        self.assertIsNone(self.window.pending_autologin_user)

        self.backend.run.reset_mock()
        self.window._operation_finished("user-autologin", True, "enabled")
        self.backend.run.assert_called_once_with("freeze")
        self.assertFalse(self.window.pending_user_freeze)

    def test_autologin_failure_cancels_pending_freeze(self) -> None:
        self.window.pending_autologin_user = "person_01"
        self.window.pending_user_freeze = True

        with patch("cachy_freeze_gui.window.QMessageBox.critical"):
            self.window._operation_finished("user-autologin", False, "failed")

        self.assertIsNone(self.window.pending_autologin_user)
        self.assertFalse(self.window.pending_user_freeze)
        self.backend.run.assert_not_called()

    def test_administrator_mutations_are_blocked_in_user_page(self) -> None:
        self.window._users_changed(
            [
                {
                    "username": "localadm",
                    "display_name": "Administrator",
                    "administrator": True,
                    "groups": ["localadm", "wheel"],
                    "locked": False,
                    "autologin": False,
                    "home": "/home/localadm",
                }
            ]
        )
        self.window.user_table.selectRow(0)

        with patch("cachy_freeze_gui.window.QMessageBox.warning") as warning:
            self.window._toggle_user_lock()
            self.window._toggle_autologin()
            self.window._delete_user()

        self.assertEqual(warning.call_count, 3)
        self.backend.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
