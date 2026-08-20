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
  2. Queues safe finalization after the requesting user logs out.
  3. Refreshes managed templates only after sessions and processes stop.
  4. Publishes Golden and schedules the next boot as FROZEN.
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

request_uid=${PKEXEC_UID:-${SUDO_UID:-}}
[[ $request_uid =~ ^[0-9]+$ && $request_uid -gt 0 ]] ||
  die "Run this activation from the desktop user through PolicyKit or sudo."
request_user=$(getent passwd "$request_uid" | cut -d: -f1)
[[ $request_user =~ ^[a-z_][a-z0-9_-]{0,30}$ ]] ||
  die "The requesting desktop account is invalid."
/usr/local/sbin/cachy-freeze finalize request "$request_user" --uid "$request_uid"

printf '%s\n' \
  "FROZEN activation was queued safely." \
  "Save your work and log out; Golden will be published only after all managed sessions stop." \
  "Do not reboot until finalization status reports complete."
