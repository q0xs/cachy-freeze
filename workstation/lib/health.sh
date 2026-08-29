#!/usr/bin/env bash

HEALTH_FAILURES=0

health_pass() {
  printf '  %-56s PASS\n' "$1"
  log_event PASS "health: $1"
}

health_fail() {
  printf '  %-56s FAIL\n' "$1"
  log_event FAIL "health: $1"
  (( HEALTH_FAILURES += 1 ))
}

health_assert() {
  local label=$1
  shift
  if "$@" >/dev/null 2>&1; then
    health_pass "$label"
  else
    health_fail "$label"
  fi
}

check_user_record() {
  local account
  account=$(getent passwd "$TARGET_USER") || return 1
  [[ $(getent passwd "$TARGET_USER" | wc -l) -eq 1 ]] || return 1
  [[ $(cut -d: -f3 <<<"$account") == "$TARGET_UID" ]] || return 1
  [[ $(cut -d: -f4 <<<"$account") == "$TARGET_GID" ]] || return 1
  [[ $(cut -d: -f6 <<<"$account") == "$TARGET_HOME" ]]
}

check_no_admin_access() {
  ! user_has_admin_access
}

check_reviewed_package_version() {
  local package_name=$1 recipe_root installed_version epoch pkgver pkgrel expected_version
  recipe_root=$CWS_PROJECT_ROOT/workstation/vendor/aur/$package_name
  installed_version=$(pacman -Q "$package_name" 2>/dev/null | awk '{print $2}') || return 1
  epoch=$(awk -F ' = ' '$1 == "\tepoch" { print $2; exit }' "$recipe_root/.SRCINFO")
  pkgver=$(awk -F ' = ' '$1 == "\tpkgver" { print $2; exit }' "$recipe_root/.SRCINFO")
  pkgrel=$(awk -F ' = ' '$1 == "\tpkgrel" { print $2; exit }' "$recipe_root/.SRCINFO")
  [[ -n $installed_version && -n $pkgver && -n $pkgrel ]] || return 1
  expected_version=${epoch:+$epoch:}$pkgver-$pkgrel
  (( $(vercmp "$installed_version" "$expected_version") >= 0 ))
}

check_chrome() {
  check_reviewed_package_version google-chrome && [[ -x /usr/bin/google-chrome-stable ]]
}

check_libreoffice() {
  pacman -Q libreoffice-fresh >/dev/null 2>&1 && [[ -x /usr/bin/libreoffice ]]
}

check_anydesk() {
  check_reviewed_package_version anydesk-bin &&
    [[ -x /usr/bin/anydesk ]] &&
    systemctl is-enabled --quiet anydesk.service &&
    systemctl is-active --quiet anydesk.service
}

check_zoiper() {
  check_reviewed_package_version zoiper-bin && [[ -x /usr/bin/zoiper ]]
}

check_wine_dependencies() {
  local package_name
  pacman -Q wine >/dev/null 2>&1 && [[ -x /usr/bin/wine ]] || return 1
  for package_name in "${CWS_WINE32_PACKAGES[@]}"; do
    pacman -Q "$package_name" >/dev/null 2>&1 || return 1
  done
}

check_desktop_runtime() {
  local package_name
  for package_name in \
    networkmanager pipewire pipewire-audio pipewire-pulse wireplumber v4l-utils plasma-workspace; do
    pacman -Q "$package_name" >/dev/null 2>&1 || return 1
  done
  command -v nmcli >/dev/null 2>&1 || return 1
  systemctl is-active --quiet NetworkManager.service
}

check_microsip_archive() {
  [[ -f $CWS_MICROSIP_ARCHIVE && ! -L $CWS_MICROSIP_ARCHIVE ]] || return 1
  [[ $(sha256sum "$CWS_MICROSIP_ARCHIVE" | awk '{print $1}') == "$MICROSIP_ARCHIVE_SHA256" ]]
}

check_microsip_prefix() {
  local prefix executable
  prefix=$TARGET_HOME/.local/share/wineprefixes/microsip
  executable=$prefix/drive_c/Program\ Files/MicroSIP/MicroSIP.exe
  validate_target_managed_path "$prefix" "MicroSIP prefix" || return 1
  [[ -d $prefix && ! -L $prefix && -s $prefix/system.reg && -f $executable && \
    ! -L $executable ]] || return 1
  [[ $(sha256sum "$executable" | awk '{print $1}') == "$MICROSIP_EXE_SHA256" ]] || return 1
  [[ $(stat -c %u "$prefix") == "$TARGET_UID" ]] || return 1
  ! find "$prefix" -xdev ! -uid "$TARGET_UID" -print -quit | grep -q .
}

check_microsip_wrapper() {
  [[ -x $CWS_MICROSIP_WRAPPER && ! -L $CWS_MICROSIP_WRAPPER ]] || return 1
  [[ $(stat -c '%u:%g:%a' "$CWS_MICROSIP_WRAPPER") == 0:0:755 ]] || return 1
  cmp -s \
    "$CWS_PROJECT_ROOT/workstation/assets/cachy-workstation-microsip" \
    "$CWS_MICROSIP_WRAPPER"
}

check_launcher_set() {
  local slug friendly template menu_file desktop_file installed_file
  validate_target_managed_path \
    "$TARGET_HOME/.local/share/applications" "Application-menu directory" || return 1
  validate_target_managed_path "$TARGET_DESKTOP" "XDG desktop directory" || return 1
  while IFS='|' read -r slug friendly; do
    template=$CWS_PROJECT_ROOT/workstation/assets/desktop/$slug.desktop
    menu_file=$TARGET_HOME/.local/share/applications/cachy-workstation-$slug.desktop
    desktop_file=$TARGET_DESKTOP/$friendly.desktop
    for installed_file in "$menu_file" "$desktop_file"; do
      [[ -f $installed_file && ! -L $installed_file && -x $installed_file ]] || return 1
      [[ $(stat -c '%u:%g:%a' "$installed_file") == "$TARGET_UID:$TARGET_GID:755" ]] ||
        return 1
      cmp -s "$template" "$installed_file" || return 1
      desktop-file-validate "$installed_file" >/dev/null 2>&1 || return 1
    done
  done <<'EOF'
google-chrome|Google Chrome
libreoffice|LibreOffice
anydesk|AnyDesk
zoiper|Zoiper
microsip|MicroSIP
EOF
}

ini_value() {
  local file_name=$1 group=$2 key=$3
  awk -F= -v wanted_group="$group" -v wanted_key="$key" '
    /^\[/ {
      current = substr($0, 2, length($0) - 2)
      next
    }
    current == wanted_group && $1 == wanted_key {
      sub(/^[^=]*=/, "")
      print
      exit
    }
  ' "$file_name"
}

check_kde_lock_config() {
  local config_file=$TARGET_HOME/.config/kscreenlockerrc
  [[ -f $config_file && ! -L $config_file ]] || return 1
  [[ $(stat -c '%u:%g' "$config_file") == "$TARGET_UID:$TARGET_GID" ]] || return 1
  [[ $(ini_value "$config_file" Daemon Autolock) == true ]] || return 1
  [[ $(ini_value "$config_file" Daemon Timeout) == 60 ]] || return 1
  [[ $(ini_value "$config_file" Daemon LockGrace) == 0 ]] || return 1
  [[ $(ini_value "$config_file" Daemon LockOnResume) == true ]]
}

check_idle_policy_config() {
  [[ -f $CWS_IDLE_CONFIG && ! -L $CWS_IDLE_CONFIG ]] || return 1
  [[ $(stat -c '%u:%g:%a' "$CWS_IDLE_CONFIG") == 0:0:600 ]] || return 1
  grep -Fxq "TARGET_USER=$TARGET_USER" "$CWS_IDLE_CONFIG" || return 1
  grep -Fxq "TARGET_UID=$TARGET_UID" "$CWS_IDLE_CONFIG" || return 1
  grep -Fxq "TARGET_GID=$TARGET_GID" "$CWS_IDLE_CONFIG" || return 1
  grep -Fxq "TARGET_HOME=$TARGET_HOME" "$CWS_IDLE_CONFIG" || return 1
  grep -Fxq "LOCK_SECONDS=$CWS_LOCK_SECONDS" "$CWS_IDLE_CONFIG" || return 1
  grep -Fxq "SHUTDOWN_SECONDS=$CWS_SHUTDOWN_SECONDS" "$CWS_IDLE_CONFIG" || return 1
  [[ $(wc -l <"$CWS_IDLE_CONFIG") -eq 6 ]] || return 1
  "$CWS_IDLE_SUPERVISOR" --check-config "$CWS_IDLE_CONFIG" >/dev/null
}

check_idle_binaries() {
  [[ -x $CWS_IDLE_AGENT && -x $CWS_IDLE_SUPERVISOR ]] || return 1
  [[ $(stat -c '%u:%g:%a' "$CWS_IDLE_AGENT") == 0:0:755 ]] || return 1
  [[ $(stat -c '%u:%g:%a' "$CWS_IDLE_SUPERVISOR") == 0:0:755 ]] || return 1
  cmp -s "$CWS_PROJECT_ROOT/workstation/idle/idle-supervisor.py" "$CWS_IDLE_SUPERVISOR"
}

check_idle_service() {
  [[ -f $CWS_IDLE_UNIT && ! -L $CWS_IDLE_UNIT ]] || return 1
  cmp -s \
    "$CWS_PROJECT_ROOT/workstation/systemd/cachy-workstation-idle.service" \
    "$CWS_IDLE_UNIT" || return 1
  systemctl is-enabled --quiet cachy-workstation-idle.service || return 1
  systemctl is-active --quiet cachy-workstation-idle.service
}

check_sleep_inhibitor() {
  systemd-inhibit --list --no-pager --no-legend | grep -Fq CachyWorkstation
}

check_setup_log() {
  [[ -f $CWS_LOG_FILE && ! -L $CWS_LOG_FILE ]] || return 1
  [[ $(stat -c '%u:%g:%a' "$CWS_LOG_FILE") == 0:0:640 ]]
}

run_health_check() {
  HEALTH_FAILURES=0
  printf '\n========================================\n'
  printf ' CachyWorkstation Health Check\n'
  printf ' User: %s\n' "$TARGET_USER"
  printf '========================================\n'

  health_assert "User record and home directory match" check_user_record
  health_assert "User has no sudo/admin-equivalent access" check_no_admin_access
  health_assert "Google Chrome package and executable" check_chrome
  health_assert "LibreOffice package and executable" check_libreoffice
  health_assert "AnyDesk package, enabled service, running service" check_anydesk
  health_assert "Zoiper package and executable" check_zoiper
  health_assert "Wine and required checked 32-bit libraries" check_wine_dependencies
  health_assert "KDE network, audio, video, and VoIP runtime" check_desktop_runtime
  health_assert "Reviewed official MicroSIP archive checksum" check_microsip_archive
  health_assert "MicroSIP prefix, executable, and recursive ownership" check_microsip_prefix
  health_assert "Root-owned MicroSIP launcher wrapper" check_microsip_wrapper
  health_assert "Five menu entries and five owned desktop shortcuts" check_launcher_set
  health_assert "KDE 60-minute password lock configuration" check_kde_lock_config
  health_assert "Root-owned 60/120-minute idle policy configuration" check_idle_policy_config
  health_assert "Root-owned KDE idle agent and supervisor" check_idle_binaries
  health_assert "Idle shutdown service enabled and running" check_idle_service
  health_assert "System sleep inhibitor preserves idle timeline" check_sleep_inhibitor
  health_assert "Secure provisioning log" check_setup_log

  printf '%s\n' '----------------------------------------'
  if (( HEALTH_FAILURES == 0 )); then
    printf ' OVERALL: PASS\n'
    printf ' Ready for freeze: YES\n'
    printf '========================================\n'
    log_event PASS "health check complete; ready for freeze"
    return 0
  fi
  printf ' OVERALL: FAIL (%d failed checks)\n' "$HEALTH_FAILURES"
  printf ' Ready for freeze: NO\n'
  printf '========================================\n'
  log_event FAIL "health check complete; failures=$HEALTH_FAILURES"
  return 1
}
