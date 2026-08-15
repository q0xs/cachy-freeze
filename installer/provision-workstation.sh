#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly PROJECT_ROOT=$(cd -- "$INSTALLER_DIR/.." && pwd)
readonly LOG=/var/log/cachyos-workstation-install.log

(( EUID == 0 )) || {
  printf 'Run as root:\n  sudo %s\n' "$0" >&2
  exit 1
}

if [[ ${CACHY_SETUP_NONINTERACTIVE:-0} == 1 ]]; then
  IFS= read -r setup_employee_user || exit 2
  IFS= read -r setup_employee_name || exit 2
  IFS= read -r setup_employee_password || exit 2
fi

exec > >(tee -a "$LOG") 2>&1
trap 'rc=$?; printf "ERROR: Installation stopped near line %s (code: %s). Log: %s\n" "$LINENO" "$rc" "$LOG" >&2' ERR
printf 'Installation started: %s\n' "$(date --iso-8601=seconds)"

# Validate disk and boot layout before long application downloads.
CACHY_FREEZE_CONFIG="$PROJECT_ROOT/deepfreeze/etc/cachy-freeze.conf" \
  bash "$PROJECT_ROOT/deepfreeze/bin/cachy-freeze" preflight

bash "$INSTALLER_DIR/install-applications.sh"
if [[ ${CACHY_SETUP_NONINTERACTIVE:-0} == 1 ]]; then
  printf '%s\n%s\n%s\n' \
    "$setup_employee_user" "$setup_employee_name" "$setup_employee_password" |
    CACHY_SETUP_NONINTERACTIVE=1 \
      bash "$INSTALLER_DIR/create-employee-user.sh"
  unset setup_employee_password
else
  bash "$INSTALLER_DIR/create-employee-user.sh"
fi
bash "$INSTALLER_DIR/install-freeze-engine.sh"
bash "$INSTALLER_DIR/publish-golden.sh"

printf '%s\n' \
  "All preparation steps are complete." \
  "The system was left in THAWED maintenance mode for safety." \
  "After live checks, use the Setup page to enable FROZEN mode." \
  "Log: $LOG"
