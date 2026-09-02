#!/usr/bin/env bash

# shellcheck disable=SC1091
source "$CWS_PROJECT_ROOT/workstation/assets/microsip-source.conf"
readonly MICROSIP_VERSION MICROSIP_URL MICROSIP_ARCHIVE_SHA256 MICROSIP_EXE_SHA256
readonly CWS_MICROSIP_SYSTEM_ROOT=/opt/cachy-workstation/microsip
readonly CWS_MICROSIP_ARCHIVE=$CWS_MICROSIP_SYSTEM_ROOT/MicroSIP-$MICROSIP_VERSION.zip
readonly CWS_MICROSIP_WRAPPER=/usr/local/bin/cachy-workstation-microsip

validate_microsip_archive() {
  local archive=$1 entry executable_count=0 inspection_dir executable archive_listing
  [[ -f $archive && ! -L $archive ]] || {
    fail "MicroSIP archive is missing or unsafe."
    return 1
  }
  [[ $(stat -c %s "$archive") -ge 1048576 && $(stat -c %s "$archive") -le 104857600 ]] || {
    fail "MicroSIP archive size is outside the accepted range."
    return 1
  }
  [[ $(sha256sum "$archive" | awk '{print $1}') == "$MICROSIP_ARCHIVE_SHA256" ]] || {
    fail "MicroSIP archive checksum does not match the reviewed release."
    return 1
  }
  file --brief "$archive" | grep -q '^Zip archive data' || {
    fail "MicroSIP download is not a ZIP archive."
    return 1
  }

  archive_listing=$(bsdtar -tf "$archive") || {
    fail "MicroSIP ZIP directory could not be read."
    return 1
  }
  while IFS= read -r entry; do
    [[ -n $entry ]] || continue
    [[ $entry != /* && $entry != \\* && $entry != *\\* ]] || {
      fail "MicroSIP ZIP contains an absolute or backslash path: $entry"
      return 1
    }
    [[ /$entry/ != */../* && /$entry/ != */./* ]] || {
      fail "MicroSIP ZIP contains a traversal path: $entry"
      return 1
    }
    if [[ ${entry,,} == microsip.exe ]]; then
      (( executable_count += 1 ))
    fi
  done <<<"$archive_listing"
  (( executable_count == 1 )) || {
    fail "MicroSIP ZIP must contain exactly one root MicroSIP.exe."
    return 1
  }

  inspection_dir=$(mktemp -d /tmp/cachy-workstation-microsip-check.XXXXXXXX)
  bsdtar --no-same-owner -xf "$archive" -C "$inspection_dir" || {
    rm -rf --one-file-system "$inspection_dir"
    fail "MicroSIP archive could not be safely extracted."
    return 1
  }
  executable=$inspection_dir/MicroSIP.exe
  [[ -f $executable && ! -L $executable ]] || {
    rm -rf --one-file-system "$inspection_dir"
    fail "MicroSIP.exe is missing after extraction."
    return 1
  }
  if [[ $(sha256sum "$executable" | awk '{print $1}') != "$MICROSIP_EXE_SHA256" ]] ||
    ! file --brief "$executable" |
      grep -Eq '^PE32 executable.*GUI.*Intel (80386|i386)'; then
    rm -rf --one-file-system "$inspection_dir"
    fail "MicroSIP.exe does not match the reviewed 32-bit Windows executable."
    return 1
  fi
  rm -rf --one-file-system "$inspection_dir"
}

install_verified_microsip_archive() {
  local candidate
  install -d -o root -g root -m 0755 "$CWS_MICROSIP_SYSTEM_ROOT"

  if [[ -f $CWS_MICROSIP_ARCHIVE ]] &&
    [[ $(sha256sum "$CWS_MICROSIP_ARCHIVE" | awk '{print $1}') == "$MICROSIP_ARCHIVE_SHA256" ]]; then
    validate_microsip_archive "$CWS_MICROSIP_ARCHIVE" || return 1
    success "Reviewed MicroSIP $MICROSIP_VERSION archive already present"
    return 0
  fi

  candidate="$CWS_MICROSIP_ARCHIVE.candidate.$$"
  info "Downloading MicroSIP $MICROSIP_VERSION from the official HTTPS source"
  download_https "$MICROSIP_URL" "$candidate" || return 1
  if ! validate_microsip_archive "$candidate"; then
    rm -f -- "$candidate"
    return 1
  fi
  install -o root -g root -m 0644 "$candidate" "$CWS_MICROSIP_ARCHIVE"
  rm -f -- "$candidate"
  success "Verified MicroSIP archive installed"
}

initialize_microsip_prefix() {
  local prefix=$1 wineboot_rc
  [[ -d $prefix && ! -L $prefix ]] || {
    fail "MicroSIP Wine prefix path is unsafe."
    return 1
  }
  if [[ -s $prefix/system.reg ]]; then
    success "Existing MicroSIP Wine prefix preserved"
    return 0
  fi

  info "Initializing a user-owned Wine prefix for $TARGET_USER"
  set +e
  run_as_target timeout --signal=TERM --kill-after=15s 180s \
    env \
    WINEPREFIX="$prefix" \
    WINEARCH=win64 \
    WINEDEBUG=-all \
    xvfb-run -a -s '-screen 0 1024x768x24' wineboot -u
  wineboot_rc=$?
  set -e
  run_as_target env WINEPREFIX="$prefix" wineserver -k >/dev/null 2>&1 || true
  [[ -s $prefix/system.reg ]] || {
    fail "Wine prefix initialization failed (wineboot exit: $wineboot_rc)."
    return 1
  }
  if (( wineboot_rc != 0 )); then
    warn "wineboot exited with $wineboot_rc after creating a valid prefix; continuing."
  fi
  success "MicroSIP Wine prefix initialized"
}

install_microsip_for_target() {
  local prefix application_dir installed_executable
  prefix=$TARGET_HOME/.local/share/wineprefixes/microsip
  application_dir=$prefix/drive_c/Program\ Files/MicroSIP
  installed_executable=$application_dir/MicroSIP.exe

  verify_wine_runtime || return 1
  install_verified_microsip_archive || return 1

  ensure_target_directory "$TARGET_HOME/.local" 0755 || return 1
  ensure_target_directory "$TARGET_HOME/.local/share" 0755 || return 1
  ensure_target_directory "$TARGET_HOME/.local/share/wineprefixes" 0700 || return 1
  ensure_target_directory "$prefix" 0700 || return 1
  repair_target_tree_ownership "$prefix" || return 1
  initialize_microsip_prefix "$prefix" || return 1

  ensure_target_directory "$application_dir" 0755 || return 1
  run_as_target unzip -oq "$CWS_MICROSIP_ARCHIVE" -d "$application_dir" || {
    fail "MicroSIP portable files could not be installed in the user prefix."
    return 1
  }
  [[ -f $installed_executable && ! -L $installed_executable ]] || {
    fail "Installed MicroSIP executable is missing or unsafe."
    return 1
  }
  run_as_target chmod 0755 "$installed_executable" || {
    fail "MicroSIP executable permissions could not be set."
    return 1
  }
  repair_target_tree_ownership "$prefix" || return 1

  [[ $(sha256sum "$installed_executable" | awk '{print $1}') == "$MICROSIP_EXE_SHA256" ]] || {
    fail "Installed MicroSIP executable failed checksum verification."
    return 1
  }
  if find "$prefix" -xdev ! -uid "$TARGET_UID" -print -quit | grep -q .; then
    fail "MicroSIP prefix contains files not owned by $TARGET_USER."
    return 1
  fi
  success "MicroSIP $MICROSIP_VERSION installed for $TARGET_USER"
}

install_microsip_wrapper() {
  install -o root -g root -m 0755 \
    "$CWS_PROJECT_ROOT/workstation/assets/cachy-workstation-microsip" \
    "$CWS_MICROSIP_WRAPPER"
}

install_user_launchers() {
  local asset_dir app_menu desktop launcher_stage slug friendly source_file staged_source menu_file desktop_file
  asset_dir=$CWS_PROJECT_ROOT/workstation/assets/desktop
  app_menu=$TARGET_HOME/.local/share/applications
  desktop=$TARGET_DESKTOP
  launcher_stage=$(mktemp -d /run/cachy-workstation-launchers.XXXXXXXX) || return 1
  chmod 0755 "$launcher_stage"
  trap 'rm -rf --one-file-system "$launcher_stage"' RETURN

  install_microsip_wrapper || return 1
  ensure_target_directory "$TARGET_HOME/.config" 0755 || return 1
  ensure_target_directory "$TARGET_HOME/.local" 0755 || return 1
  ensure_target_directory "$TARGET_HOME/.local/share" 0755 || return 1
  ensure_target_directory "$app_menu" 0755 || return 1
  ensure_target_directory "$desktop" 0755 || return 1

  while IFS='|' read -r slug friendly; do
    source_file=$asset_dir/$slug.desktop
    staged_source=$launcher_stage/$slug.desktop
    menu_file=$app_menu/cachy-workstation-$slug.desktop
    desktop_file=$desktop/$friendly.desktop
    [[ -f $source_file ]] || {
      fail "Launcher template is missing: $slug"
      return 1
    }
    install -o root -g root -m 0644 "$source_file" "$staged_source" || {
      fail "Launcher template could not be staged: $friendly"
      return 1
    }
    run_as_target install -m 0755 "$staged_source" "$menu_file" || {
      fail "Application-menu launcher could not be installed: $friendly"
      return 1
    }
    run_as_target install -m 0755 "$staged_source" "$desktop_file" || {
      fail "Desktop launcher could not be installed: $friendly"
      return 1
    }
    desktop-file-validate "$menu_file" "$desktop_file" || {
      fail "Launcher validation failed: $friendly"
      return 1
    }
    log_event OK "launcher installed name=$friendly owner=$TARGET_USER"
  done <<'EOF'
google-chrome|Google Chrome
libreoffice|LibreOffice
anydesk|AnyDesk
zoiper|Zoiper
microsip|MicroSIP
EOF

  # KDE authorizes launchers outside standard application directories by their
  # executable bit. Both copies are mode 0755 and owned by the target user.
  run_as_target update-desktop-database "$app_menu" >/dev/null 2>&1 ||
    warn "Application menu cache could not be refreshed; Plasma will refresh it on login."
  success "Application-menu entries and KDE desktop shortcuts installed"
}
