#!/usr/bin/env bash
set -Eeuo pipefail

INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly INSTALLER_DIR
PROJECT_ROOT=$(cd -- "$INSTALLER_DIR/.." && pwd)
readonly PROJECT_ROOT
# shellcheck source=lib/common.sh
source "$INSTALLER_DIR/lib/common.sh"

require_root
require_maintenance

readonly CONFIG=/etc/cachy-employee.conf
readonly ADMIN_CONFIG=/etc/cachy-frozen-admin.conf
if [[ ! -r $ADMIN_CONFIG ]]; then
  printf '%s\n' 'ADMIN_USER=localadm' >"$ADMIN_CONFIG"
  chmod 0600 "$ADMIN_CONFIG"
fi
# Configuration files are created by root and are not writable by users.
# shellcheck disable=SC1090
source "$ADMIN_CONFIG"

[[ ${ADMIN_USER:-} =~ ^[a-z][a-z0-9_-]{2,31}$ ]] ||
  die "Invalid administrator account configuration."
id "$ADMIN_USER" >/dev/null 2>&1 ||
  die "Administrator account not found: $ADMIN_USER"

managed_users=("$ADMIN_USER")
if [[ -r $CONFIG ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG"
  [[ ${EMPLOYEE_USER:-} =~ ^[a-z][a-z0-9_-]{2,31}$ ]] ||
    die "Invalid optional managed-user configuration."
  id "$EMPLOYEE_USER" >/dev/null 2>&1 ||
    die "Configured managed user not found: $EMPLOYEE_USER"
  managed_users+=("$EMPLOYEE_USER")
fi

# Install the current reset and administrator-restriction services.
install -m 0755 \
  "$PROJECT_ROOT/user/files/cachy-employee-reset" \
  /usr/local/sbin/cachy-employee-reset
install -m 0644 \
  "$PROJECT_ROOT/user/files/cachy-employee-reset.service" \
  /etc/systemd/system/cachy-employee-reset.service
install -m 0755 \
  "$PROJECT_ROOT/user/files/cachy-frozen-admin-restrict" \
  /usr/local/sbin/cachy-frozen-admin-restrict
install -m 0644 \
  "$PROJECT_ROOT/user/files/cachy-frozen-admin-restrict.service" \
  /etc/systemd/system/cachy-frozen-admin-restrict.service

# Do not carry a legacy nologin shell into Golden.
usermod --shell /bin/bash "$ADMIN_USER"
systemctl daemon-reload
systemctl enable cachy-employee-reset.service
systemctl enable cachy-frozen-admin-restrict.service

# Stop optional managed-user sessions while their templates are copied.
if [[ -n ${EMPLOYEE_USER:-} ]]; then
  loginctl terminate-user "$EMPLOYEE_USER" 2>/dev/null || true
fi

template_root=/var/lib/cachy-user-template
install -d -m 0700 "$template_root"
for user in "${managed_users[@]}"; do
  user_home=$(getent passwd "$user" | cut -d: -f6)
  [[ -n $user_home && -d $user_home ]] ||
    die "Home directory not found: $user"
  template="$template_root/$user"
  next_template="$template_root/$user.next"
  previous_template="$template_root/$user.previous"

  rm -rf --one-file-system "$next_template"
  cp -a "$user_home" "$next_template"
  rm -rf --one-file-system "$previous_template"
  [[ ! -e $template ]] || mv "$template" "$previous_template"
  mv "$next_template" "$template"

  printf '%s\n' \
    "User home template updated: $user" \
    "Previous template retained for recovery: $previous_template"
done
