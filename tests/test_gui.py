from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from cachy_freeze_gui.backend import BackendClient
    from cachy_freeze_gui.window import MainWindow
    from PyQt6.QtWidgets import QApplication, QMessageBox

    HAS_QT = True
except ModuleNotFoundError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PyQt6 is not installed")
class MinimalGuiTests(unittest.TestCase):
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

    def test_normal_ui_exposes_only_two_mode_actions(self) -> None:
        self.assertEqual(self.window.freeze_button.text(), "FREEZE COMPUTER")
        self.assertEqual(self.window.thaw_button.text(), "THAW COMPUTER")
        for removed in ("pages", "snapshot_table", "user_create_button", "health_button"):
            self.assertFalse(hasattr(self.window, removed))

    def test_verified_state_controls_available_action(self) -> None:
        self.window._status_changed(
            {
                "verified": True,
                "running_mode": "thawed",
                "scheduled_mode": "thawed",
                "reboot_required": False,
            }
        )
        self.assertTrue(self.window.freeze_button.isEnabled())
        self.assertFalse(self.window.thaw_button.isEnabled())
        self.assertEqual(self.window.mode_label.text(), "THAWED")

    def test_known_unverified_mode_is_still_visible(self) -> None:
        self.window._status_changed(
            {
                "verified": False,
                "running_mode": "frozen",
                "scheduled_mode": "unknown",
                "reboot_required": False,
            }
        )
        self.assertEqual(self.window.mode_label.text(), "FROZEN")
        self.assertFalse(self.window.freeze_button.isEnabled())
        self.assertFalse(self.window.thaw_button.isEnabled())

    def test_pending_mode_is_distinct_and_blocks_duplicate_transition(self) -> None:
        self.window._status_changed(
            {
                "verified": True,
                "running_mode": "thawed",
                "scheduled_mode": "frozen",
                "reboot_required": True,
            }
        )
        self.assertEqual(self.window.next_mode_label.text(), "Next Boot: FROZEN")
        self.assertFalse(self.window.freeze_button.isEnabled())
        self.assertFalse(self.window.thaw_button.isEnabled())
        self.assertFalse(self.window.reboot_button.isHidden())

    def test_freeze_requires_safe_confirmation(self) -> None:
        with patch(
            "cachy_freeze_gui.window.QMessageBox.warning",
            return_value=QMessageBox.StandardButton.Cancel,
        ):
            self.window._freeze()
        self.backend.run.assert_called_once_with("status")

    def test_mode_change_never_reboots_automatically(self) -> None:
        with patch("cachy_freeze_gui.window.QMessageBox.information"):
            self.window._operation_finished("freeze", True, "ready")
        actions = [call.args[0] for call in self.backend.run.call_args_list]
        self.assertNotIn("reboot", actions)
        self.assertFalse(self.window.reboot_button.isHidden())


@unittest.skipUnless(HAS_QT, "PyQt6 is not installed")
class InstallerGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_installer_is_one_page_and_requires_secret_channel(self) -> None:
        backend = BackendClient(setup_root=__import__("pathlib").Path("."))
        backend.refresh_local = Mock()
        backend.run = Mock(return_value=True)
        window = MainWindow(backend)
        self.addCleanup(window.close)
        self.assertTrue(hasattr(window, "install_button"))
        self.assertTrue(hasattr(window, "workstation_install_button"))
        self.assertTrue(hasattr(window, "workstation_check_button"))
        self.assertFalse(hasattr(window, "freeze_button"))
        layout = window.centralWidget().layout()
        self.assertLess(
            layout.indexOf(window.workstation_check_button), layout.indexOf(window.password)
        )
        self.assertLess(
            layout.indexOf(window.workstation_check_button), layout.indexOf(window.install_button)
        )
        self.assertTrue(window._strong_password("Correct-Horse-42"))
        self.assertFalse(window._strong_password("short"))

    def test_installer_can_launch_workstation_check_for_target_user(self) -> None:
        backend = BackendClient(setup_root=__import__("pathlib").Path("."))
        backend.refresh_local = Mock()
        backend.run = Mock(return_value=True)
        window = MainWindow(backend)
        self.addCleanup(window.close)
        self.assertFalse(window.install_button.isEnabled())
        window.workstation_user.setText("wrw1166")
        window._check_workstation()
        backend.run.assert_called_once_with("setup-workstation-check", secret="wrw1166")

    def test_installer_blocks_freeze_until_workstation_check_passes(self) -> None:
        backend = BackendClient(setup_root=__import__("pathlib").Path("."))
        backend.refresh_local = Mock()
        backend.run = Mock(return_value=True)
        window = MainWindow(backend)
        self.addCleanup(window.close)
        window.workstation_user.setText("wrw1166")
        window.password.setText("Correct-Horse-42")
        window.password_confirm.setText("Correct-Horse-42")
        self.assertFalse(window.install_button.isEnabled())
        with patch("cachy_freeze_gui.window.QMessageBox.warning") as warning:
            window._install()
        self.assertEqual(warning.call_args.args[1], "Workstation check required")
        backend.run.assert_not_called()

        with patch("cachy_freeze_gui.window.QMessageBox.information"):
            window._operation_finished(
                "setup-workstation-check", True, "CachyWorkstation health check passed."
            )
        self.assertTrue(window.install_button.isEnabled())

    def test_workstation_output_is_visible_in_gui(self) -> None:
        backend = BackendClient(setup_root=__import__("pathlib").Path("."))
        backend.refresh_local = Mock()
        backend.run = Mock(return_value=True)
        window = MainWindow(backend)
        self.addCleanup(window.close)
        window._operation_output("setup-workstation-check", " OVERALL: PASS\n")
        window._operation_output("setup-workstation-check", " Ready for freeze: YES\n")
        self.assertIn("OVERALL: PASS", window.workstation_report.toPlainText())
        self.assertIn("Ready for freeze: YES", window.workstation_report.toPlainText())


if __name__ == "__main__":
    unittest.main()
