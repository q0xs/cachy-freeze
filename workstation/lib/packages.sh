#!/usr/bin/env bash

readonly CWS_AUR_BUILD_USER=cachyworkbuild
readonly CWS_AUR_CACHE=/var/cache/cachy-workstation/aur

readonly -a CWS_BASE_PACKAGES=(
  base-devel
  ca-certificates
  cmake
  curl
  desktop-file-utils
  extra-cmake-modules
  file
  git
  kidletime
  kconfig
  libarchive
  libreoffice-fresh
  python
  qt6-base
  qt6-wayland
  rsync
  unzip
  wine
  wine-gecko
  wine-mono
  xdg-user-dirs
  xorg-server-xvfb
)

readonly -a CWS_APP_RUNTIME_PACKAGES=(
  alsa-lib
  cairo
  fakeroot
  gdk-pixbuf2
  glib2
  gnome-themes-extra
  gtk3
  libcups
  libglvnd
  libnotify
  libpulse
  libx11
  libxdamage
  libxext
  libxfixes
  libxi
  libxkbfile
  libxrandr
  libxrender
  libxss
  libxtst
  lsb-release
  minizip
  networkmanager
  nss
  pango
  pipewire
  pipewire-audio
  pipewire-pulse
  polkit
  ttf-liberation
  v4l-utils
  wireplumber
  xdg-utils
)

readonly -a CWS_WINE32_PACKAGES=(
  lib32-alsa-lib
  lib32-fontconfig
  lib32-freetype2
  lib32-gnutls
  lib32-libglvnd
  lib32-libpulse
  lib32-libx11
  lib32-libxcb
  lib32-libxcomposite
  lib32-libxext
  lib32-libxinerama
  lib32-libxrandr
  lib32-libxrender
  lib32-mesa
)

install_base_packages() {
  info "Refreshing CachyOS package databases and reconciling official dependencies"
  run_logged pacman -Syu --needed --noconfirm \
    "${CWS_BASE_PACKAGES[@]}" \
    "${CWS_APP_RUNTIME_PACKAGES[@]}" \
    "${CWS_WINE32_PACKAGES[@]}" || {
    fail "The official package transaction failed."
    return 1
  }

  local package_name
  for package_name in "${CWS_BASE_PACKAGES[@]}" "${CWS_WINE32_PACKAGES[@]}"; do
    pacman -Q "$package_name" >/dev/null 2>&1 || {
      fail "Required package is still missing: $package_name"
      return 1
    }
  done
  success "Official dependencies and Wine 32-bit runtime libraries are installed"
}

ensure_aur_build_user() {
  local account build_uid build_gid build_home build_shell group_id
  if ! id "$CWS_AUR_BUILD_USER" >/dev/null 2>&1; then
    useradd \
      --system \
      --user-group \
      --create-home \
      --home-dir "/var/lib/$CWS_AUR_BUILD_USER" \
      --shell /usr/bin/nologin \
      "$CWS_AUR_BUILD_USER" || {
      fail "Could not create the isolated AUR build account."
      return 1
    }
  fi

  account=$(getent passwd "$CWS_AUR_BUILD_USER") || {
    fail "The isolated AUR build account cannot be resolved."
    return 1
  }
  [[ $(getent passwd "$CWS_AUR_BUILD_USER" | wc -l) -eq 1 ]] || {
    fail "The AUR build account resolves to multiple records."
    return 1
  }
  IFS=: read -r _ _ build_uid build_gid _ build_home build_shell <<<"$account"
  [[ $build_uid =~ ^[0-9]+$ && $build_gid =~ ^[0-9]+$ && $build_uid -lt 1000 && \
    $build_gid -gt 0 && $build_home == "/var/lib/$CWS_AUR_BUILD_USER" && \
    $build_shell == /usr/bin/nologin ]] || {
    fail "The AUR build account does not match the isolated system-account contract."
    return 1
  }
  [[ -d $build_home && ! -L $build_home && \
    $(stat -c '%u:%g' "$build_home") == "$build_uid:$build_gid" ]] || {
    fail "The AUR build account home is missing, linked, or incorrectly owned."
    return 1
  }
  while IFS= read -r group_id; do
    [[ $group_id != 0 ]] || {
      fail "The AUR build account belongs to a privileged group."
      return 1
    }
  done < <(id -G "$CWS_AUR_BUILD_USER" | tr ' ' '\n')
  [[ $(id -u "$CWS_AUR_BUILD_USER") == "$build_uid" ]] || {
    fail "The AUR build account identity changed during validation."
    return 1
  }
}

run_as_aur_builder() {
  runuser -u "$CWS_AUR_BUILD_USER" -- \
    env -i \
    HOME="/var/lib/$CWS_AUR_BUILD_USER" \
    USER="$CWS_AUR_BUILD_USER" \
    LOGNAME="$CWS_AUR_BUILD_USER" \
    PATH=/usr/local/bin:/usr/bin:/usr/sbin \
    "$@"
}

validate_vendored_recipe() {
  local package_name=$1 recipe_root revision_file expected_revision
  recipe_root=$CWS_PROJECT_ROOT/workstation/vendor/aur/$package_name
  revision_file=$CWS_PROJECT_ROOT/workstation/vendor/aur/AUR-REVISIONS.txt

  [[ -f $recipe_root/PKGBUILD && -f $recipe_root/.SRCINFO ]] || {
    fail "Reviewed AUR recipe is incomplete: $package_name"
    return 1
  }
  [[ -f $revision_file ]] || {
    fail "AUR revision manifest is missing."
    return 1
  }
  expected_revision=$(awk -v package="$package_name" '$1 == package { print $2 }' "$revision_file")
  [[ $expected_revision =~ ^[0-9a-f]{40}$ ]] || {
    fail "Reviewed AUR revision is invalid: $package_name"
    return 1
  }
  if find "$recipe_root" -xdev -type f -perm /002 -print -quit | grep -q .; then
    fail "AUR recipe contains a world-writable file: $package_name"
    return 1
  fi
}

install_aur_recipe_dependencies() {
  local package_name=$1
  case $package_name in
    gtk2)
      run_logged pacman -S --needed --noconfirm \
        glib2-devel gobject-introspection gtk-doc || {
        fail "Could not install GTK 2 fallback build dependencies."
        return 1
      }
      ;;
  esac
  return 0
}

build_and_install_aur_package() {
  local package_name=$1 recipe_root build_dir package_file
  local -a package_files=()
  recipe_root=$CWS_PROJECT_ROOT/workstation/vendor/aur/$package_name
  build_dir=$CWS_AUR_CACHE/$package_name

  ensure_aur_build_user || return 1
  validate_vendored_recipe "$package_name" || return 1
  install_aur_recipe_dependencies "$package_name" || return 1
  install -d -o root -g root -m 0755 "$CWS_AUR_CACHE"
  [[ $build_dir == "$CWS_AUR_CACHE/"* ]] || {
    fail "Unsafe AUR build path."
    return 1
  }
  rm -rf --one-file-system "$build_dir"
  install -d -o "$CWS_AUR_BUILD_USER" -g "$CWS_AUR_BUILD_USER" -m 0750 "$build_dir"
  cp -a -- "$recipe_root/." "$build_dir/"
  chown -R "$CWS_AUR_BUILD_USER:$CWS_AUR_BUILD_USER" "$build_dir"

  info "Validating reviewed AUR metadata: $package_name"
  if ! diff -u "$recipe_root/.SRCINFO" <(
    cd "$build_dir"
    run_as_aur_builder makepkg --printsrcinfo
  ); then
    fail "PKGBUILD and .SRCINFO differ for $package_name."
    return 1
  fi

  info "Building reviewed AUR package as $CWS_AUR_BUILD_USER: $package_name"
  (
    cd "$build_dir"
    run_logged run_as_aur_builder \
      env MAKEFLAGS="-j$(nproc)" makepkg --noconfirm --cleanbuild --clean
  ) || {
    fail "AUR build failed: $package_name"
    return 1
  }

  while IFS= read -r -d '' package_file; do
    package_files+=("$package_file")
  done < <(find "$build_dir" -maxdepth 1 -type f -name '*.pkg.tar.zst' -print0)
  (( ${#package_files[@]} > 0 )) || {
    fail "AUR build produced no installable package: $package_name"
    return 1
  }

  run_logged pacman -U --noconfirm "${package_files[@]}" || {
    fail "Could not install the built package: $package_name"
    return 1
  }
  pacman -Q "$package_name" >/dev/null 2>&1 ||
    fail "Package verification failed after installation: $package_name"
}

ensure_package() {
  local package_name=$1 installed_version expected_version recipe_root epoch pkgver pkgrel
  local package_healthy=false
  recipe_root=$CWS_PROJECT_ROOT/workstation/vendor/aur/$package_name
  if pacman -Q "$package_name" >/dev/null 2>&1; then
    installed_version=$(pacman -Q "$package_name" | awk '{print $2}')
    if pacman -Qk "$package_name" >/dev/null 2>&1; then
      package_healthy=true
    else
      warn "$package_name has missing packaged files and will be reinstalled"
    fi

    if [[ $package_healthy == true && -f $recipe_root/.SRCINFO ]]; then
      epoch=$(awk -F ' = ' '$1 == "\tepoch" { print $2; exit }' "$recipe_root/.SRCINFO")
      pkgver=$(awk -F ' = ' '$1 == "\tpkgver" { print $2; exit }' "$recipe_root/.SRCINFO")
      pkgrel=$(awk -F ' = ' '$1 == "\tpkgrel" { print $2; exit }' "$recipe_root/.SRCINFO")
      expected_version=${epoch:+$epoch:}$pkgver-$pkgrel
      if (( $(vercmp "$installed_version" "$expected_version") < 0 )); then
        package_healthy=false
        info "$package_name $installed_version is older than reviewed $expected_version"
      fi
    fi

    if [[ $package_healthy == true ]]; then
      success "$package_name already installed ($installed_version)"
      return 0
    fi
  fi

  if pacman -Si "$package_name" >/dev/null 2>&1; then
    info "Installing signed repository package: $package_name"
    run_logged pacman -S --noconfirm "$package_name" || {
      fail "Repository package installation failed: $package_name"
      return 1
    }
  else
    build_and_install_aur_package "$package_name" || return 1
  fi

  success "$package_name installed ($(pacman -Q "$package_name" | awk '{print $2}'))"
}

install_chrome() {
  ensure_package google-chrome || return 1
  command -v google-chrome-stable >/dev/null 2>&1 ||
    fail "Google Chrome executable was not installed."
}

install_libreoffice() {
  ensure_package libreoffice-fresh || return 1
  command -v libreoffice >/dev/null 2>&1 || fail "LibreOffice executable was not installed."
}

install_anydesk() {
  ensure_package anydesk-bin || return 1
  command -v anydesk >/dev/null 2>&1 || fail "AnyDesk executable was not installed."
  systemctl enable --now anydesk.service || {
    fail "AnyDesk service could not be enabled."
    return 1
  }
  systemctl is-active --quiet anydesk.service || fail "AnyDesk service is not active."
}

install_zoiper() {
  ensure_package gtk2 || return 1
  ensure_package zoiper-bin || return 1
  command -v zoiper >/dev/null 2>&1 || fail "Zoiper executable was not installed."
}

verify_wine_runtime() {
  local package_name
  pacman -Q wine >/dev/null 2>&1 || {
    fail "Wine is not installed."
    return 1
  }
  command -v wine >/dev/null 2>&1 || {
    fail "Wine executable is missing."
    return 1
  }
  for package_name in "${CWS_WINE32_PACKAGES[@]}"; do
    pacman -Q "$package_name" >/dev/null 2>&1 || {
      fail "Wine 32-bit runtime dependency is missing: $package_name"
      return 1
    }
  done
  success "Wine and checked 32-bit runtime dependencies are available"
}
