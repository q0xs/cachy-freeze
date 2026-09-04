#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
readonly PROJECT_ROOT
TEST_ROOT=$(mktemp -d /tmp/cachy-freeze-ui.XXXXXX)
readonly TEST_ROOT
trap 'rm -rf --one-file-system "$TEST_ROOT"' EXIT

QT_QPA_PLATFORM=offscreen \
XDG_CONFIG_HOME="$TEST_ROOT/config" \
PYTHONPATH="$PROJECT_ROOT/src:$PROJECT_ROOT/app" \
python - <<'PY'
from pathlib import Path
from unittest.mock import Mock

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QPushButton, QScrollArea

from cachy_freeze_gui.backend import BackendClient
from cachy_freeze_gui.window import MainWindow

application = QApplication([])


def assert_button_content_fits(button):
    assert button.height() >= button.sizeHint().height()
    assert button.width() >= button.minimumWidth()

backend = BackendClient()
backend.refresh_local = Mock()
backend.run = Mock(return_value=True)
window = MainWindow(backend)
assert window.freeze_button.text() == "FREEZE COMPUTER"
assert window.thaw_button.text() == "THAW COMPUTER"
assert not hasattr(window, "pages")
assert not hasattr(window, "snapshot_table")
window._status_changed(
    {
        "verified": True,
        "running_mode": "frozen",
        "scheduled_mode": "frozen",
        "reboot_required": False,
    }
)
assert window.mode_label.text() == "FROZEN"
assert window.thaw_button.isEnabled()
assert not window.freeze_button.isEnabled()
window.resize(420, 420)
window.show()
application.processEvents()
assert isinstance(window.centralWidget(), QScrollArea)
assert window.centralWidget().widgetResizable()
assert window.centralWidget().horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
for button in window.findChildren(QPushButton):
    if button.isVisible():
        assert_button_content_fits(button)
window.close()

installer_backend = BackendClient(setup_root=Path("."))
installer_backend.refresh_local = Mock()
installer_backend.run = Mock(return_value=True)
installer = MainWindow(installer_backend)
assert installer.install_button.text() == "INSTALL CACHYFREEZE"
assert not hasattr(installer, "freeze_button")
assert installer._strong_password("Correct-Horse-42")
assert not installer._strong_password("short")
installer.resize(420, 420)
installer.show()
application.processEvents()
assert isinstance(installer.centralWidget(), QScrollArea)
assert installer.centralWidget().widgetResizable()
assert installer.centralWidget().horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
for button in installer.findChildren(QPushButton):
    if button.isVisible():
        assert_button_content_fits(button)
installer.close()
application.quit()
PY

printf '%s\n' "Qt offscreen UI smoke test passed."
