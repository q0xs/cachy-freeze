#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
readonly TEST_ROOT=$(mktemp -d /tmp/cachy-freeze-ui.XXXXXX)
trap 'rm -rf --one-file-system "$TEST_ROOT"' EXIT

QT_QPA_PLATFORM=offscreen \
XDG_CONFIG_HOME="$TEST_ROOT/config" \
PYTHONPATH="$PROJECT_ROOT/src:$PROJECT_ROOT/app" \
python - <<'PY'
from PyQt6.QtWidgets import QApplication

from cachy_freeze_gui.backend import BackendClient
from cachy_freeze_gui.window import MainWindow

application = QApplication([])
window = MainWindow(BackendClient())
assert window.pages.count() == 6
assert window.snapshot_table.columnCount() == 9
assert window.user_table.columnCount() == 6
assert window.update_apply_button.text()
assert window.settings_save_button.text()
window.close()
application.quit()
PY

printf '%s\n' "Qt offscreen UI smoke testi başarılı."
