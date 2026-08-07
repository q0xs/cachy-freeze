#!/usr/bin/env bash

die() {
  printf 'HATA: %s\n' "$*" >&2
  exit 1
}

require_root() {
  (( EUID == 0 )) || die "Bu betik sudo ile calistirilmalidir."
}

require_maintenance() {
  local source options
  source=$(findmnt -n -o SOURCE /)
  [[ $source == *'[/@]' ]] ||
    die "Bu islem yalnizca Maintenance modunda yapilir. Once set-thawed-mode.sh ve reboot."
  options=$(findmnt -n -o OPTIONS /)
  [[ ,$options, == *,rw,* ]] ||
    die "Maintenance koku salt-okunur bagli. Sistemi degistirmeden once @ kokunu yazilabilir ac."
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
  (( ${#packages[@]} > 0 )) || die "AUR paket dosyasi olusmadi: $package"
  pacman -U --noconfirm --needed "${packages[@]}"

  pacman -Q "$package" >/dev/null 2>&1 ||
    die "AUR paketi kurulamadi: $package"
}

download_https() {
  local url=$1 destination=$2
  [[ $url == https://* ]] || die "Yalnizca HTTPS indirmeye izin verilir: $url"
  [[ $destination == /* ]] || die "Indirme hedefi mutlak yol olmali: $destination"
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
    die "Indirme basarisiz: $url"
  fi
  [[ -s $temporary ]] || {
    rm -f -- "$temporary"
    die "Indirilen dosya bos: $url"
  }
  mv -f -- "$temporary" "$destination"
}

validate_zip_paths() {
  local archive=$1 entry
  while IFS= read -r entry; do
    [[ -n $entry ]] || continue
    [[ $entry != /* && $entry != \\* ]] ||
      die "ZIP mutlak yol iceriyor: $entry"
    [[ /$entry/ != */../* && /$entry/ != */./* ]] ||
      die "ZIP guvensiz yol iceriyor: $entry"
    [[ $entry != *\\* ]] || die "ZIP ters egik cizgili yol iceriyor: $entry"
  done < <(unzip -Z1 "$archive")
}
