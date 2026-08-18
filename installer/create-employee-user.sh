#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly PROJECT_ROOT
readonly ADMIN_USER=localadm
# shellcheck source=lib/common.sh
source "$PROJECT_ROOT/installer/lib/common.sh"

require_root
require_maintenance

id "$ADMIN_USER" >/dev/null 2>&1 ||
  die "Expected administrator account not found: $ADMIN_USER"
id -nG "$ADMIN_USER" | grep -Eq '(^| )wheel( |$)' ||
  die "$ADMIN_USER is not in the wheel group; administrator status could not be verified."
[[ $(passwd -S "$ADMIN_USER" | awk '{print $2}') == P ]] ||
  die "$ADMIN_USER does not have an active password."

if [[ ${CACHY_SETUP_NONINTERACTIVE:-0} == 1 ]]; then
  IFS= read -r employee_user || die "Username was not received from the GUI channel."
  IFS= read -r employee_full_name || die "Display name was not received from the GUI channel."
  IFS= read -r employee_password || die "Password was not received from the GUI channel."
  employee_password_again=$employee_password
else
  [[ -r /dev/tty && -w /dev/tty ]] ||
    die "An interactive terminal is required to enter user details."
  printf '%s\n' \
    "Standard account details" \
    "The username may contain lowercase letters, digits, _ and -." >/dev/tty
  read -r -p "Username (example: employee01): " employee_user </dev/tty
fi
employee_user=${employee_user,,}
[[ $employee_user =~ ^[a-z][a-z0-9_-]{2,31}$ ]] ||
  die "Invalid username: $employee_user"
[[ $employee_user != "$ADMIN_USER" ]] ||
  die "The standard user and administrator cannot have the same username."
if id "$employee_user" >/dev/null 2>&1; then
  employee_uid=$(id -u "$employee_user")
  (( employee_uid >= 1000 && employee_uid < 65534 )) ||
    die "The existing account is not a standard local user: $employee_user"
fi

if [[ ${CACHY_SETUP_NONINTERACTIVE:-0} != 1 ]]; then
  read -r -p "Display name: " employee_full_name </dev/tty
fi
[[ -n ${employee_full_name//[[:space:]]/} ]] ||
  die "Display name cannot be empty."
[[ $employee_full_name != *:* && $employee_full_name != *$'\n'* ]] ||
  die "Display name cannot contain ':'."

while [[ ${CACHY_SETUP_NONINTERACTIVE:-0} != 1 ]]; do
  read -r -s -p "Account password: " employee_password </dev/tty
  printf '\n' >/dev/tty
  read -r -s -p "Repeat password: " employee_password_again </dev/tty
  printf '\n' >/dev/tty
  [[ -n $employee_password ]] || {
    printf 'Password cannot be empty.\n' >/dev/tty
    continue
  }
  [[ $employee_password != *:* ]] || {
    printf "Password cannot contain ':'.\n" >/dev/tty
    continue
  }
  [[ $employee_password == "$employee_password_again" ]] || {
    printf 'Passwords do not match; try again.\n' >/dev/tty
    continue
  }
  break
done
(( ${#employee_password} >= 4 && ${#employee_password} <= 256 )) &&
  [[ $employee_password == "$employee_password_again" ]] ||
  die "The account password is empty or does not match its confirmation."
[[ $employee_password != *:* && $employee_password != *$'\n'* && \
  $employee_password != *$'\r'* ]] ||
  die "The account password contains an unsupported character."

for command in wine unzip rsync google-chrome-stable slack libreoffice zoiper \
  anydesk; do
  command -v "$command" >/dev/null ||
    die "Run install-applications.sh first. Missing command: $command"
done

if ! id "$employee_user" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash \
    --comment "$employee_full_name" "$employee_user"
else
  usermod --comment "$employee_full_name" "$employee_user"
fi
printf '%s:%s\n' "$employee_user" "$employee_password" | chpasswd
unset employee_password employee_password_again

home=$(getent passwd "$employee_user" | cut -d: -f6)
install -d -o "$employee_user" -g "$employee_user" -m 0755 \
  "$home/Desktop" "$home/.config" "$home/.local" "$home/.local/share"
install -d -o "$employee_user" -g "$employee_user" -m 0755 \
  "$home/.local/share/applications" "$home/.local/share/company-wine"
install -o "$employee_user" -g "$employee_user" -m 0644 \
  "$PROJECT_ROOT/user/files/kdeglobals" "$home/.config/kdeglobals"
install -o "$employee_user" -g "$employee_user" -m 0644 \
  "$PROJECT_ROOT/user/files/plasmarc" "$home/.config/plasmarc"

for desktop in "$PROJECT_ROOT"/user/desktop/*.desktop; do
  install -o "$employee_user" -g "$employee_user" -m 0555 \
    "$desktop" "$home/Desktop/${desktop##*/}"
done

prefix="$home/.local/share/company-wine/microsip"
install -d -o "$employee_user" -g "$employee_user" -m 0700 "$prefix"
set +e
timeout --signal=TERM --kill-after=10s 120s \
  runuser -u "$employee_user" -- \
  env WINEPREFIX="$prefix" WINEARCH=win64 WINEDEBUG=-all xvfb-run -a wineboot -u
wineboot_rc=$?
set -e
runuser -u "$employee_user" -- \
  env WINEPREFIX="$prefix" wineserver -k >/dev/null 2>&1 || true
if (( wineboot_rc != 0 && wineboot_rc != 124 )); then
  die "MicroSIP Wine prefix initialization failed (code: $wineboot_rc)."
fi
[[ -s $prefix/system.reg ]] || die "The MicroSIP Wine prefix was not created."
microsip_target="$prefix/drive_c/Program Files/MicroSIP"
microsip_stage=$(mktemp -d)
trap 'rm -rf --one-file-system "$microsip_stage"' EXIT
unzip -q "/opt/company/microsip/$(</opt/company/microsip/CURRENT)" \
  -d "$microsip_stage"
microsip_exe=$(
  find "$microsip_stage" -type f -iname 'microsip.exe' -print -quit
)
[[ -n $microsip_exe ]] ||
  die "No executable was found in the MicroSIP archive."
install -d -o "$employee_user" -g "$employee_user" -m 0755 \
  "$microsip_target"
rsync -a --delete "${microsip_exe%/*}/" "$microsip_target/"
microsip_installed_exe=$(
  find "$microsip_target" -maxdepth 1 -type f -iname 'microsip.exe' \
    -print -quit
)
[[ -n $microsip_installed_exe ]] ||
  die "MicroSIP could not be installed into the target directory."
if [[ $microsip_installed_exe != "$microsip_target/microsip.exe" ]]; then
  mv "$microsip_installed_exe" "$microsip_target/microsip.exe"
fi
chown -R "$employee_user:$employee_user" "$microsip_target"
chmod 0755 "$microsip_target/microsip.exe"
rm -rf --one-file-system "$microsip_stage"
trap - EXIT

# File existence alone is not a successful application install. Launch the
# portable binary in an isolated display and accept either a clean exit or a
# process that remains healthy until the smoke-test timeout.
microsip_smoke_log=$(mktemp /tmp/cachy-microsip-smoke.XXXXXX.log)
set +e
timeout --signal=TERM --kill-after=5s 15s \
  runuser -u "$employee_user" -- \
  env WINEPREFIX="$prefix" WINEARCH=win64 WINEDEBUG=-all \
  xvfb-run -a wine "$microsip_target/microsip.exe" /minimized \
  >"$microsip_smoke_log" 2>&1
microsip_smoke_rc=$?
set -e
runuser -u "$employee_user" -- \
  env WINEPREFIX="$prefix" wineserver -k >/dev/null 2>&1 || true
if (( microsip_smoke_rc != 0 && microsip_smoke_rc != 124 )); then
  sed -n '1,120p' "$microsip_smoke_log" >&2
  rm -f -- "$microsip_smoke_log"
  die "The MicroSIP Wine smoke test failed (code: $microsip_smoke_rc)."
fi
rm -f -- "$microsip_smoke_log"
[[ -s $prefix/system.reg ]] || die "The MicroSIP Wine prefix could not be verified."

cat >"$home/.config/mimeapps.list" <<'EOF'
[Default Applications]
x-scheme-handler/http=google-chrome.desktop
x-scheme-handler/https=google-chrome.desktop
text/html=google-chrome.desktop

[Added Associations]
x-scheme-handler/http=google-chrome.desktop;
x-scheme-handler/https=google-chrome.desktop;
text/html=google-chrome.desktop;
EOF
chown "$employee_user:$employee_user" "$home/.config/mimeapps.list"
chmod 0644 "$home/.config/mimeapps.list"

install -m 0755 \
  "$PROJECT_ROOT/user/files/company-microsip" \
  /usr/local/bin/company-microsip
install -m 0755 \
  "$PROJECT_ROOT/user/files/cachyfreeze-finish-session" \
  /usr/local/bin/cachyfreeze-finish-session
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

cat >/etc/cachy-employee.conf <<EOF
EMPLOYEE_USER=$employee_user
EOF
chmod 0600 /etc/cachy-employee.conf

cat >/etc/cachy-frozen-admin.conf <<EOF
ADMIN_USER=$ADMIN_USER
EOF
chmod 0600 /etc/cachy-frozen-admin.conf

template_root=/var/lib/cachy-user-template
rm -rf --one-file-system \
  "${template_root:?}/${employee_user:?}" \
  "${template_root:?}/${ADMIN_USER:?}"
install -d -m 0700 "$template_root"
cp -a "$home" "$template_root/$employee_user"
admin_home=$(getent passwd "$ADMIN_USER" | cut -d: -f6)
[[ -n $admin_home && -d $admin_home ]] ||
  die "Administrator home directory not found."
cp -a "$admin_home" "$template_root/$ADMIN_USER"
systemctl daemon-reload
systemctl enable cachy-employee-reset.service
systemctl enable cachy-frozen-admin-restrict.service
systemctl is-enabled --quiet cachy-employee-reset.service ||
  die "The managed-user reset service could not be enabled."
systemctl is-enabled --quiet cachy-frozen-admin-restrict.service ||
  die "The FROZEN administrator restriction service could not be enabled."

printf '%s\n' \
  "Standard account ready: $employee_user ($employee_full_name)" \
  "$ADMIN_USER will be hidden from the FROZEN graphical login screen." \
  "All managed accounts return to their clean templates in FROZEN mode." \
  "The account's CachyOS group membership and privileges were not changed." \
  "The password was set to the value entered during setup."
