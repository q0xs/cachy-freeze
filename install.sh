#!/usr/bin/env bash
set -Eeuo pipefail

readonly REPOSITORY_URL=https://github.com/q0xs/cachy-freeze.git
readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)

if (( EUID != 0 )); then
  if [[ -r $SCRIPT_DIR/installer/install-cachyfreeze.sh ]]; then
    exec sudo /usr/bin/bash "$SCRIPT_DIR/install.sh" "$@"
  fi
  printf '%s\n' \
    "Run the remote installer with administrator privileges:" \
    "  curl -fsSL https://raw.githubusercontent.com/q0xs/cachy-freeze/main/install.sh | sudo bash" >&2
  exit 1
fi

command -v pacman >/dev/null 2>&1 || {
  printf '%s\n' "CachyFreeze supports Arch Linux/CachyOS systems with pacman." >&2
  exit 1
}

if [[ -r $SCRIPT_DIR/installer/install-cachyfreeze.sh ]]; then
  exec /usr/bin/bash "$SCRIPT_DIR/installer/install-cachyfreeze.sh"
fi

pacman -S --needed --noconfirm git
install_root=$(mktemp -d /tmp/cachyfreeze-install.XXXXXX)
cleanup() {
  rm -rf --one-file-system "$install_root"
}
trap cleanup EXIT
git clone --depth 1 --branch main --single-branch "$REPOSITORY_URL" "$install_root/repository"
/usr/bin/bash "$install_root/repository/installer/install-cachyfreeze.sh"
