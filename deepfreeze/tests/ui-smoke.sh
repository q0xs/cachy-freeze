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
assert window.pages.count() == 7
assert window.snapshot_table.columnCount() == 9
assert window.user_table.columnCount() == 6
assert window.update_apply_button.text()
assert window.settings_save_button.text()
assert window.setup_preflight_button.text()
assert window.setup_start_button.text()
assert window.setup_finish_button.text()
assert window._password_is_strong("Correct-Horse-42")
assert not window._password_is_strong("short")
window.close()
application.quit()
PY

set +e
launcher_log="$TEST_ROOT/setup-launcher.log"
QT_QPA_PLATFORM=offscreen \
XDG_CONFIG_HOME="$TEST_ROOT/config-launcher" \
PYTHONPATH="$PROJECT_ROOT/src:$PROJECT_ROOT/app" \
  timeout 2s python -m cachy_freeze_gui.main \
    --setup-source "$PROJECT_ROOT" >"$launcher_log" 2>&1
launcher_rc=$?
set -e
[[ $launcher_rc -eq 124 ]] || {
  printf 'Setup launcher did not remain in the event loop (code: %s).\n' \
    "$launcher_rc" >&2
  sed -n '1,120p' "$launcher_log" >&2
  exit 1
}

printf '%s\n' "Qt offscreen UI smoke test passed."
