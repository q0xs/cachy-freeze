#!/usr/bin/env bash

readonly CWS_LOGIN_SDDM_CONFIG_DIR=/etc/sddm.conf.d
readonly CWS_LOGIN_SDDM_CONFIG=$CWS_LOGIN_SDDM_CONFIG_DIR/90-cachy-workstation-login.conf
readonly CWS_LOGIN_SDDM_STATE_DIR=/var/lib/sddm
readonly CWS_LOGIN_SDDM_STATE=$CWS_LOGIN_SDDM_STATE_DIR/state.conf
readonly CWS_LOGIN_PLASMA_CONFIG=/etc/plasmalogin.conf
readonly CWS_LOGIN_SESSION_FILE=plasma.desktop

login_session_path() {
  if [[ -f /usr/share/wayland-sessions/$CWS_LOGIN_SESSION_FILE ]]; then
    printf '/usr/share/wayland-sessions/%s\n' "$CWS_LOGIN_SESSION_FILE"
  elif [[ -f /usr/share/xsessions/$CWS_LOGIN_SESSION_FILE ]]; then
    printf '/usr/share/xsessions/%s\n' "$CWS_LOGIN_SESSION_FILE"
  else
    fail "The KDE Plasma session file was not found: $CWS_LOGIN_SESSION_FILE"
    return 1
  fi
}

active_display_manager_unit() {
  local target
  target=$(readlink -f /etc/systemd/system/display-manager.service 2>/dev/null || true)
  case ${target##*/} in
    plasmalogin.service)
      printf '%s\n' plasmalogin
      ;;
    sddm.service)
      printf '%s\n' sddm
      ;;
    *)
      if systemctl is-enabled --quiet plasmalogin.service 2>/dev/null; then
        printf '%s\n' plasmalogin
      elif systemctl is-enabled --quiet sddm.service 2>/dev/null; then
        printf '%s\n' sddm
      else
        return 1
      fi
      ;;
  esac
}

write_ini_value() {
  local file=$1 group=$2 key=$3 value=$4 temporary
  temporary=$(mktemp /tmp/cachy-workstation-ini.XXXXXXXX)
  awk -v wanted_group="$group" -v wanted_key="$key" -v wanted_value="$value" '
    BEGIN {
      current = ""
      group_seen = 0
      key_written = 0
    }
    /^\[/ {
      if (current == wanted_group && key_written == 0) {
        print wanted_key "=" wanted_value
        key_written = 1
      }
      current = substr($0, 2, length($0) - 2)
      if (current == wanted_group) {
        group_seen = 1
      }
      print
      next
    }
    current == wanted_group && $0 ~ "^[[:space:]]*" wanted_key "[[:space:]]*=" {
      if (key_written == 0) {
        print wanted_key "=" wanted_value
        key_written = 1
      }
      next
    }
    { print }
    END {
      if (group_seen == 0) {
        print "[" wanted_group "]"
      }
      if (key_written == 0) {
        print wanted_key "=" wanted_value
      }
    }
  ' "$file" >"$temporary"
  install -o root -g root -m 0644 "$temporary" "$file"
  rm -f -- "$temporary"
}

set_sddm_state_owner() {
  if getent passwd sddm >/dev/null 2>&1 && getent group sddm >/dev/null 2>&1; then
    chown sddm:sddm "$CWS_LOGIN_SDDM_STATE"
  else
    chown root:root "$CWS_LOGIN_SDDM_STATE"
  fi
  chmod 0644 "$CWS_LOGIN_SDDM_STATE"
}

ensure_ini_file() {
  local file=$1 parent
  parent=${file%/*}
  install -d -o root -g root -m 0755 "$parent"
  if [[ ! -e $file ]]; then
    install -o root -g root -m 0644 /dev/null "$file"
  fi
  [[ -f $file && ! -L $file ]] || {
    fail "Login manager configuration path is unsafe: $file"
    return 1
  }
}

configure_sddm_default_user() {
  local session_path
  session_path=$(login_session_path) || return 1
  ensure_ini_file "$CWS_LOGIN_SDDM_CONFIG" || return 1
  write_ini_value "$CWS_LOGIN_SDDM_CONFIG" Users RememberLastUser true
  write_ini_value "$CWS_LOGIN_SDDM_CONFIG" Users RememberLastSession true
  write_ini_value "$CWS_LOGIN_SDDM_CONFIG" Autologin User ""
  write_ini_value "$CWS_LOGIN_SDDM_CONFIG" Autologin Session ""

  install -d -o sddm -g sddm -m 0755 "$CWS_LOGIN_SDDM_STATE_DIR" 2>/dev/null ||
    install -d -o root -g root -m 0755 "$CWS_LOGIN_SDDM_STATE_DIR"
  if [[ ! -e $CWS_LOGIN_SDDM_STATE ]]; then
    install -o root -g root -m 0644 /dev/null "$CWS_LOGIN_SDDM_STATE"
  fi
  [[ -f $CWS_LOGIN_SDDM_STATE && ! -L $CWS_LOGIN_SDDM_STATE ]] || {
    fail "SDDM state path is unsafe: $CWS_LOGIN_SDDM_STATE"
    return 1
  }
  write_ini_value "$CWS_LOGIN_SDDM_STATE" Last User "$TARGET_USER"
  write_ini_value "$CWS_LOGIN_SDDM_STATE" Last Session "$session_path"
  set_sddm_state_owner
}

configure_plasmalogin_default_user() {
  ensure_ini_file "$CWS_LOGIN_PLASMA_CONFIG" || return 1
  write_ini_value "$CWS_LOGIN_PLASMA_CONFIG" Greeter PreselectedUser "$TARGET_USER"
  write_ini_value "$CWS_LOGIN_PLASMA_CONFIG" Greeter PreselectedSession "$CWS_LOGIN_SESSION_FILE"
  write_ini_value "$CWS_LOGIN_PLASMA_CONFIG" Autologin User ""
}

configure_login_screen_default_user() {
  local display_manager
  display_manager=$(active_display_manager_unit) || {
    fail "No supported KDE login manager was found."
    return 1
  }
  case $display_manager in
    plasmalogin)
      configure_plasmalogin_default_user || return 1
      ;;
    sddm)
      configure_sddm_default_user || return 1
      ;;
    *)
      fail "Unsupported KDE login manager: $display_manager"
      return 1
      ;;
  esac
  success "Login screen preselects $TARGET_USER without automatic login"
}
