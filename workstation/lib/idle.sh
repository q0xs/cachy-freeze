#!/usr/bin/env bash

readonly CWS_IDLE_CONFIG_DIR=/etc/cachy-workstation
readonly CWS_IDLE_CONFIG=$CWS_IDLE_CONFIG_DIR/workstation.conf
readonly CWS_IDLE_INSTALL_DIR=/usr/lib/cachy-workstation
readonly CWS_IDLE_AGENT=$CWS_IDLE_INSTALL_DIR/cachy-workstation-idle-agent
readonly CWS_IDLE_SUPERVISOR=$CWS_IDLE_INSTALL_DIR/idle-supervisor
readonly CWS_IDLE_UNIT=/etc/systemd/system/cachy-workstation-idle.service
readonly CWS_LOCK_SECONDS=3600
readonly CWS_SHUTDOWN_SECONDS=7200

configure_kde_screen_lock() {
  local config_dir=$TARGET_HOME/.config
  ensure_target_directory "$config_dir" 0755 || return 1
  run_as_target kwriteconfig6 \
    --file kscreenlockerrc --group Daemon --key Autolock --type bool true || {
    fail "Could not enable KDE automatic screen locking."
    return 1
  }
  run_as_target kwriteconfig6 \
    --file kscreenlockerrc --group Daemon --key Timeout 60 || {
    fail "Could not set the KDE lock timeout."
    return 1
  }
  run_as_target kwriteconfig6 \
    --file kscreenlockerrc --group Daemon --key LockGrace 0 || {
    fail "Could not require the password immediately."
    return 1
  }
  run_as_target kwriteconfig6 \
    --file kscreenlockerrc --group Daemon --key LockOnResume --type bool true || {
    fail "Could not enable locking after resume."
    return 1
  }
  [[ $(stat -c '%u:%g' "$config_dir/kscreenlockerrc") == "$TARGET_UID:$TARGET_GID" ]] || {
    fail "KDE screen-lock configuration has the wrong owner."
    return 1
  }
  success "KDE screen lock configured for 60 minutes"
}

install_idle_policy_config() {
  local temporary
  install -d -o root -g root -m 0755 "$CWS_IDLE_CONFIG_DIR"
  temporary=$(mktemp /tmp/cachy-workstation-policy.XXXXXXXX)
  {
    printf 'TARGET_USER=%s\n' "$TARGET_USER"
    printf 'TARGET_UID=%s\n' "$TARGET_UID"
    printf 'TARGET_GID=%s\n' "$TARGET_GID"
    printf 'TARGET_HOME=%s\n' "$TARGET_HOME"
    printf 'LOCK_SECONDS=%s\n' "$CWS_LOCK_SECONDS"
    printf 'SHUTDOWN_SECONDS=%s\n' "$CWS_SHUTDOWN_SECONDS"
  } >"$temporary"
  chmod 0600 "$temporary"
  install -o root -g root -m 0600 "$temporary" "$CWS_IDLE_CONFIG"
  rm -f -- "$temporary"
}

build_idle_agent() {
  local source_dir build_dir
  source_dir=$CWS_PROJECT_ROOT/workstation/idle
  build_dir=/var/cache/cachy-workstation/idle-agent-build
  install -d -o root -g root -m 0755 /var/cache/cachy-workstation
  rm -rf --one-file-system "$build_dir"
  install -d -o root -g root -m 0755 "$build_dir"
  run_logged cmake \
    -S "$source_dir" \
    -B "$build_dir" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON || {
    fail "CMake could not configure the KDE idle agent."
    return 1
  }
  run_logged cmake --build "$build_dir" --parallel "$(nproc)" || {
    fail "KDE idle agent compilation failed."
    return 1
  }
  [[ -x $build_dir/cachy-workstation-idle-agent ]] || {
    fail "Compiled KDE idle agent is missing."
    return 1
  }

  install -d -o root -g root -m 0755 "$CWS_IDLE_INSTALL_DIR"
  install -o root -g root -m 0755 "$build_dir/cachy-workstation-idle-agent" "$CWS_IDLE_AGENT"
  install -o root -g root -m 0755 \
    "$source_dir/idle-supervisor.py" "$CWS_IDLE_SUPERVISOR"
}

install_idle_service() {
  local unit_source=$CWS_PROJECT_ROOT/workstation/systemd/cachy-workstation-idle.service
  install -o root -g root -m 0644 "$unit_source" "$CWS_IDLE_UNIT"
  systemd-analyze verify "$CWS_IDLE_UNIT" || {
    fail "Idle policy systemd unit is invalid."
    return 1
  }
  systemctl daemon-reload || {
    fail "systemd daemon-reload failed."
    return 1
  }
  systemctl enable cachy-workstation-idle.service || {
    fail "Idle policy service could not be enabled."
    return 1
  }
  systemctl restart cachy-workstation-idle.service || {
    fail "Idle policy service could not be started."
    return 1
  }
  systemctl is-active --quiet cachy-workstation-idle.service ||
    fail "Idle policy service is not active."
}

install_idle_policy() {
  configure_kde_screen_lock || return 1
  install_idle_policy_config || return 1
  build_idle_agent || return 1
  install_idle_service || return 1
  success "60-minute lock / 120-minute system poweroff policy is active"
}
