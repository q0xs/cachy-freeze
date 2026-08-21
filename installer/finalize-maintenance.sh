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
  "This queues Golden publication after all managed users log out" \
  "and schedules FROZEN only after a quiescent template capture." >/dev/tty
read -r -p "Are the maintenance checks complete? [y/N]: " confirmed </dev/tty
[[ ${confirmed,,} == y ]] || die "Operation cancelled; the system was not changed."

request_uid=${SUDO_UID:-}
[[ $request_uid =~ ^[0-9]+$ && $request_uid -gt 0 ]] ||
  die "Run this command through sudo from the desktop user that will log out."
request_user=$(getent passwd "$request_uid" | cut -d: -f1)
[[ $request_user =~ ^[a-z_][a-z0-9_-]{0,30}$ ]] ||
  die "The requesting desktop account is invalid."
/usr/local/sbin/cachy-freeze finalize request "$request_user" --uid "$request_uid"

printf '%s\n' \
  "Maintenance finalization is waiting for managed sessions to close." \
  "Log out now. The computer will reboot automatically only after finalization succeeds."
