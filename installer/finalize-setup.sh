#!/usr/bin/env bash
set -Eeuo pipefail

INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly INSTALLER_DIR
readonly LOG=/var/log/cachyos-workstation-install.log
# shellcheck source=lib/common.sh
source "$INSTALLER_DIR/lib/common.sh"

require_root
require_maintenance

if [[ ${CACHY_SETUP_NONINTERACTIVE:-0} == 1 ]]; then
  IFS= read -r grub_password || die "GRUB password was not received from the secure GUI channel."
else
  [[ -r /dev/tty && -w /dev/tty ]] ||
    die "An interactive terminal is required to enable FROZEN mode."
  cat >/dev/tty <<'EOF'
This independent step:
  1. Sets the GRUB maintenance password.
  2. Refreshes templates for accounts that are currently managed.
  3. Publishes the current maintenance system as Golden.
  4. Schedules the next boot as FROZEN.
EOF
  read -r -p "Continue? [y/N]: " confirmed </dev/tty
  [[ ${confirmed,,} == y ]] || die "Operation cancelled; the system was not changed."
fi

exec > >(tee -a "$LOG") 2>&1
activation_error() {
  local rc=$?
  printf "ERROR: FROZEN activation stopped near line %s (code: %s). Log: %s\n" \
    "$LINENO" "$rc" "$LOG" >&2
}
trap activation_error ERR
printf 'FROZEN activation started: %s\n' "$(date --iso-8601=seconds)"

if [[ ${CACHY_SETUP_NONINTERACTIVE:-0} == 1 ]]; then
  printf '%s\n' "$grub_password" |
    CACHY_SETUP_NONINTERACTIVE=1 \
      bash "$INSTALLER_DIR/configure-grub-password.sh"
  unset grub_password
else
  bash "$INSTALLER_DIR/configure-grub-password.sh"
fi
bash "$INSTALLER_DIR/refresh-user-templates.sh"
bash "$INSTALLER_DIR/publish-golden.sh"
bash "$INSTALLER_DIR/set-frozen-mode.sh"

printf '%s\n' \
  "FROZEN activation completed safely." \
  "The next boot will be FROZEN." \
  "Reboot from the management app when ready."
