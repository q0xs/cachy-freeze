#!/usr/bin/env bash

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_root() {
  (( EUID == 0 )) || die "This script must run as root."
}

require_maintenance() {
  local source options
  source=$(findmnt -n -o SOURCE /)
  [[ $source == *'[/@]' ]] ||
    die "This operation is allowed only in THAWED maintenance mode."
  options=$(findmnt -n -o OPTIONS /)
  [[ ,$options, == *,rw,* ]] ||
    die "The maintenance root is mounted read-only."
}

aur_install() {
  local package=$1
  pacman -Q "$package" >/dev/null 2>&1 && return 0

  if ! id goldenbuild >/dev/null 2>&1; then
    useradd --system --create-home --home-dir /var/lib/goldenbuild \
      --shell /usr/bin/nologin goldenbuild
  fi

  local build_dir="/var/lib/goldenbuild/$package"
  rm -rf --one-file-system "$build_dir"
  install -d -o goldenbuild -g goldenbuild -m 0750 "$build_dir"

  local vendored="${PROJECT_ROOT:-}/vendor/aur/$package"
  if [[ -r $vendored/PKGBUILD ]]; then
    cp -a "$vendored/." "$build_dir/"
    chown -R goldenbuild:goldenbuild "$build_dir"
  else
    runuser -u goldenbuild -- \
      git clone --depth 1 "https://aur.archlinux.org/$package.git" "$build_dir"
  fi

  (
    cd "$build_dir"
    runuser -u goldenbuild -- \
      env MAKEFLAGS="-j$(nproc)" makepkg --noconfirm --cleanbuild
  )

  local packages=()
  mapfile -t packages < <(
    find "$build_dir" -maxdepth 1 -type f -name '*.pkg.tar.zst' -print
  )
  (( ${#packages[@]} > 0 )) || die "No AUR package was built: $package"
  pacman -U --noconfirm --needed "${packages[@]}"

  pacman -Q "$package" >/dev/null 2>&1 ||
    die "The AUR package could not be installed: $package"
}

download_https() {
  local url=$1 destination=$2
  [[ $url == https://* ]] || die "Only HTTPS downloads are allowed: $url"
  [[ $destination == /* ]] || die "The download destination must be absolute: $destination"
  local temporary="${destination}.download.$$"
  rm -f -- "$temporary"
  if ! curl \
    --fail \
    --location \
    --proto '=https' \
    --tlsv1.2 \
    --retry 5 \
    --retry-all-errors \
    --retry-delay 2 \
    --connect-timeout 20 \
    --max-time 600 \
    --output "$temporary" \
    "$url"; then
    rm -f -- "$temporary"
    die "Download failed: $url"
  fi
  [[ -s $temporary ]] || {
    rm -f -- "$temporary"
    die "The downloaded file is empty: $url"
  }
  mv -f -- "$temporary" "$destination"
}

validate_zip_paths() {
  local archive=$1 entry
  while IFS= read -r entry; do
    [[ -n $entry ]] || continue
    [[ $entry != /* && $entry != \\* ]] ||
      die "ZIP contains an absolute path: $entry"
    [[ /$entry/ != */../* && /$entry/ != */./* ]] ||
      die "ZIP contains an unsafe path: $entry"
    [[ $entry != *\\* ]] || die "ZIP contains a backslash path: $entry"
  done < <(unzip -Z1 "$archive")
}
