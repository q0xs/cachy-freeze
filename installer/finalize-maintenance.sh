#!/usr/bin/env bash
set -Eeuo pipefail

INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly INSTALLER_DIR
# shellcheck source=lib/common.sh
source "$INSTALLER_DIR/lib/common.sh"

require_root
require_maintenance

[[ -r /dev/tty && -w /dev/tty ]] ||
  die "An interactive terminal is required to finish maintenance."

printf '%s\n' \
  "This publishes the current maintenance system as Golden" \
  "and schedules the next boot as FROZEN." >/dev/tty
read -r -p "Are the maintenance checks complete? [y/N]: " confirmed </dev/tty
[[ ${confirmed,,} == y ]] || die "Operation cancelled; the system was not changed."

bash "$INSTALLER_DIR/refresh-user-templates.sh"
bash "$INSTALLER_DIR/publish-golden.sh"
bash "$INSTALLER_DIR/set-frozen-mode.sh"

printf '%s\n' \
  "Maintenance changes were published to Golden." \
  "The next boot will be FROZEN." \
  "Reboot manually when ready: sudo reboot"
