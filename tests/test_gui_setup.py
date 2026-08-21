from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cachy_freeze_gui.backend import BackendClient  # noqa: E402
from cachy_freeze_gui.widgets import QMessageBox as LocalizedQMessageBox  # noqa: E402
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
        self.assertEqual(self.window.setup_user_button.text(), "Create a user now")
        self.assertEqual(self.window.setup_grub_button.text(), "Save GRUB password")
        self.assertEqual(self.window.setup_finish_button.text(), "Finish and enable FROZEN")
        self.assertFalse(hasattr(self.window, "setup_backup_check"))
        self.assertFalse(hasattr(self.window, "setup_disposable_check"))
        self.assertEqual(self.window.setup_grub_username.text(), "cachyadmin")
        self.assertTrue(
            self.window.setup_grub_username.textInteractionFlags()
            & Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.assertTrue(self.window._password_is_strong("Correct-Horse-42"))
        self.assertFalse(self.window._password_is_strong("short"))
        self.assertFalse(self.window._password_is_strong("Colon:Password42"))

    def test_question_dialog_defaults_to_safe_yes_no_buttons(self) -> None:
        with patch.object(
            LocalizedQMessageBox,
            "_show",
            return_value=QMessageBox.StandardButton.No,
        ) as show:
            result = LocalizedQMessageBox.question(self.window, "Continue?", "Proceed?")

        self.assertEqual(result, QMessageBox.StandardButton.No)
        buttons = show.call_args.args[4]
        default_button = show.call_args.args[5]
        self.assertTrue(buttons & QMessageBox.StandardButton.Yes)
        self.assertTrue(buttons & QMessageBox.StandardButton.No)
        self.assertEqual(default_button, QMessageBox.StandardButton.No)

    def test_helper_does_not_require_a_managed_user_to_freeze(self) -> None:
        helper = (Path(__file__).parents[1] / "app/cachy-freeze-manager-helper").read_text()
        freeze_case = helper.split("setup-freeze)", 1)[1].split(";;", 1)[0]
        self.assertNotIn("/etc/cachy-employee.conf", freeze_case)
        self.assertIn("finalize request", freeze_case)

    def test_regular_freeze_requires_grub_protection(self) -> None:
        helper = (Path(__file__).parents[1] / "app/cachy-freeze-manager-helper").read_text()
        freeze_case = helper.split("  freeze)", 1)[1].split(";;", 1)[0]
        self.assertIn("/etc/cachy-freeze-grub-auth.conf", freeze_case)

    def test_regular_gui_freeze_queues_logout_aware_finalization(self) -> None:
        with patch(
            "cachy_freeze_gui.window.QMessageBox.warning",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window._confirm_freeze()

        self.backend.run.assert_called_once_with("freeze-prepare")

    def test_successful_finalization_request_starts_normal_logout(self) -> None:
        with (
            patch("cachy_freeze_gui.window.QMessageBox.information"),
            patch(
                "cachy_freeze_gui.window.QProcess.startDetached",
                return_value=(True, 1234),
            ) as start_detached,
        ):
            self.window._operation_finished("freeze-prepare", True, "queued")

        start_detached.assert_called_once_with(
            "/usr/local/bin/cachyfreeze-finish-session",
            [],
        )

    def test_provision_requires_preflight(self) -> None:
        with patch("cachy_freeze_gui.window.QMessageBox.warning") as warning:
            self.window._start_setup()

        warning.assert_called_once()
        self.backend.run.assert_not_called()

    def test_install_is_independent_from_user_creation(self) -> None:
        self.window.setup_preflight_ok = True

        with patch(
            "cachy_freeze_gui.window.QMessageBox.warning",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window._start_setup()

        self.backend.run.assert_called_once_with("setup-install")

    def test_install_completion_directs_operator_to_the_optional_user_step(self) -> None:
        with patch("cachy_freeze_gui.window.QMessageBox.information") as information:
            self.window._operation_finished("setup-install", True, "installed")

        message = information.call_args.args[2]
        self.assertIn("step 3", message)
        self.assertIn("step 4", message)

    def test_install_requires_one_clear_safety_confirmation(self) -> None:
        self.window.setup_preflight_ok = True

        with patch(
            "cachy_freeze_gui.window.QMessageBox.warning",
            return_value=QMessageBox.StandardButton.Cancel,
        ) as warning:
            self.window._start_setup()

        warning.assert_called_once()
        self.assertIn("recovery", warning.call_args.args[2])
        self.backend.run.assert_not_called()

    def test_grub_password_is_a_separate_secret_channel_step(self) -> None:
        self.window.setup_installed = True
        self.window.setup_grub_password.setText("Correct-Horse-42")
        self.window.setup_grub_confirm.setText("Correct-Horse-42")

        self.window._save_setup_grub_password()

        self.backend.run.assert_called_once_with("setup-grub-password", secret="Correct-Horse-42")
        self.assertEqual(self.window.setup_grub_password.text(), "")
        self.assertEqual(self.window.setup_grub_confirm.text(), "")

    def test_finish_freezes_only_after_the_grub_step(self) -> None:
        self.window.setup_grub_protected = True

        with patch(
            "cachy_freeze_gui.window.QMessageBox.warning",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window._finish_setup()

        self.backend.run.assert_called_once_with("health")
        self.assertTrue(self.window.pending_setup_finish_check)

        with patch("cachy_freeze_gui.window.QMessageBox.information"):
            self.window._result_ready("health", {"healthy": True, "freeze_ready": True})

        self.assertEqual(
            [call.args[0] for call in self.backend.run.call_args_list],
            ["health", "setup-freeze"],
        )

    def test_setup_user_step_is_optional_and_uses_the_simple_user_flow(self) -> None:
        self.window.setup_installed = True
        self.window.running_mode = "thawed"
        self.window._start_setup_user()

        self.backend.run.assert_called_once_with("applications-status")

    def test_setup_controls_follow_the_five_step_order(self) -> None:
        self.window._status_changed({"running_mode": "unknown", "current_subvolume": "@"})
        self.window._apply_setup_controls()

        self.assertEqual(self.window.running_mode, "thawed")
        self.assertFalse(self.window.setup_start_button.isEnabled())
        self.assertFalse(self.window.setup_user_button.isEnabled())
        self.assertFalse(self.window.setup_grub_button.isEnabled())
        self.assertFalse(self.window.setup_finish_button.isEnabled())

        self.window._result_ready(
            "setup-preflight",
            {
                "root_device": "/dev/sda2",
                "current_subvolume": "@",
                "firmware": "UEFI",
                "filesystem": "btrfs",
            },
        )
        self.assertTrue(self.window.setup_start_button.isEnabled())

        self.window.setup_installed = True
        self.window._apply_setup_controls()
        self.assertFalse(self.window.setup_start_button.isEnabled())
        self.assertTrue(self.window.setup_user_button.isEnabled())
        self.assertTrue(self.window.setup_grub_button.isEnabled())
        self.assertFalse(self.window.setup_finish_button.isEnabled())

        self.window.setup_grub_protected = True
        self.window._apply_setup_controls()
        self.assertFalse(self.window.setup_grub_button.isEnabled())
        self.assertTrue(self.window.setup_finish_button.isEnabled())

    def test_failed_final_check_never_enables_frozen(self) -> None:
        self.window.pending_setup_finish_check = True

        with patch("cachy_freeze_gui.window.QMessageBox.warning") as warning:
            self.window._result_ready("health", {"healthy": False, "freeze_ready": False})

        warning.assert_called_once()
        self.backend.run.assert_not_called()

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
        self.assertEqual(dialog.windowTitle(), "Create user")
        self.assertEqual(dialog.username.placeholderText(), "wrw21166")
        self.assertFalse(hasattr(dialog, "freeze_after_create"))
        self.assertIn("administrator", dialog.layout().itemAt(0).widget().text())
        dialog.close()

    def test_users_page_exposes_application_install_before_user_creation(self) -> None:
        self.assertEqual(self.window.user_app_install_button.text(), "Prepare applications")
        self.assertEqual(self.window.user_create_button.text(), "Create user")

    def test_ready_user_creation_checks_applications_before_showing_dialog(self) -> None:
        with patch("cachy_freeze_gui.window.UserDialog") as dialog:
            self.window._create_user()

        self.backend.run.assert_called_once_with("applications-status")
        self.assertTrue(self.window.pending_user_create_check)
        dialog.assert_not_called()

    def test_missing_applications_keep_ready_user_on_users_workflow(self) -> None:
        self.window.pending_user_create_check = True
        self.window.pages.setCurrentIndex(2)

        with (
            patch(
                "cachy_freeze_gui.window.QMessageBox.question",
                return_value=QMessageBox.StandardButton.Cancel,
            ) as question,
            patch.object(self.window, "_show_create_user_dialog") as show_dialog,
        ):
            self.window._result_ready(
                "applications-status",
                {
                    "all_installed": False,
                    "applications": [
                        {"name": "Wine", "installed": False},
                        {"name": "Archive extractor", "installed": True},
                    ],
                },
            )

        self.assertFalse(self.window.pending_user_create_check)
        self.assertEqual(self.window.pages.currentIndex(), 2)
        self.assertIn("Wine", question.call_args.args[2])
        show_dialog.assert_not_called()

    def test_missing_applications_can_be_prepared_from_create_user(self) -> None:
        self.window.pending_user_create_check = True
        with patch(
            "cachy_freeze_gui.window.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window._result_ready(
                "applications-status",
                {"all_installed": False, "applications": [{"name": "Wine", "installed": False}]},
            )

        self.assertTrue(self.window.pending_user_create_after_install)
        self.backend.run.assert_called_once_with("applications-install")

    def test_ready_applications_continue_to_user_dialog(self) -> None:
        self.window.pending_user_create_check = True

        with patch.object(self.window, "_show_create_user_dialog") as show_dialog:
            self.window._result_ready(
                "applications-status",
                {
                    "all_installed": True,
                    "applications": [{"name": "Wine", "installed": True}],
                },
            )

        self.assertFalse(self.window.pending_user_create_check)
        show_dialog.assert_called_once_with()

    def test_frozen_mode_disables_maintenance_writes_and_explains_how_to_continue(self) -> None:
        self.window._status_changed({"running_mode": "frozen"})

        self.assertFalse(self.window.user_create_button.isEnabled())
        self.assertFalse(self.window.freeze_button.isEnabled())
        self.assertTrue(self.window.thaw_button.isEnabled())
        self.assertIn("THAWED", self.window.alert_label.text())

    def test_failed_application_check_cancels_pending_user_creation(self) -> None:
        self.window.pending_user_create_check = True

        with patch("cachy_freeze_gui.window.QMessageBox.critical"):
            self.window._operation_finished("applications-status", False, "failed")

        self.assertFalse(self.window.pending_user_create_check)

    def test_application_install_continues_to_user_step_without_reboot(self) -> None:
        with patch("cachy_freeze_gui.window.QMessageBox.information") as information:
            self.window._operation_finished("applications-install", True, "installed")

        self.backend.run.assert_not_called()
        self.assertIn("create a user", information.call_args.args[2])

    def test_application_preparation_returns_to_the_create_user_form(self) -> None:
        self.window.pending_user_create_after_install = True
        with patch.object(self.window, "_show_create_user_dialog") as show_dialog:
            self.window._operation_finished("applications-install", True, "installed")

        self.assertFalse(self.window.pending_user_create_after_install)
        show_dialog.assert_called_once_with()

    def test_successful_user_creation_never_schedules_frozen(self) -> None:
        with patch("cachy_freeze_gui.window.QMessageBox.information") as information:
            self.window._operation_finished("user-create", True, "created")

        self.backend.run.assert_called_once_with("user-list")
        self.assertNotIn("freeze", [call.args[0] for call in self.backend.run.call_args_list])
        self.assertIn("boot mode was not changed", information.call_args.args[2])

    def test_login_selection_after_creation_never_chains_freeze(self) -> None:
        self.window.pending_autologin_user = "person_01"

        self.window._operation_finished("user-create", True, "created")
        self.backend.run.assert_called_once_with("user-autologin", "person_01")
        self.assertIsNone(self.window.pending_autologin_user)

        self.backend.run.reset_mock()
        with patch("cachy_freeze_gui.window.QMessageBox.information"):
            self.window._operation_finished("user-autologin", True, "enabled")
        self.backend.run.assert_called_once_with("user-list")
        self.assertNotIn("freeze", [call.args[0] for call in self.backend.run.call_args_list])

    def test_login_selection_failure_clears_pending_user(self) -> None:
        self.window.pending_autologin_user = "person_01"

        with patch("cachy_freeze_gui.window.QMessageBox.critical"):
            self.window._operation_finished("user-autologin", False, "failed")

        self.assertIsNone(self.window.pending_autologin_user)
        self.backend.run.assert_called_once_with("logs")

    def test_administrator_mutations_are_blocked_in_user_page(self) -> None:
        self.window._users_changed(
            [
                {
                    "username": "localadm",
                    "display_name": "Administrator",
                    "administrator": True,
                    "groups": ["localadm", "wheel"],
                    "locked": False,
                    "login_default": False,
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
