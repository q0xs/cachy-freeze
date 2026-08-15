#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)

if (( EUID != 0 )); then
  exec sudo /usr/bin/bash "$SCRIPT_DIR/install.sh" "$@"
fi

command -v pacman >/dev/null 2>&1 || {
  printf '%s\n' "CachyFreeze supports Arch Linux/CachyOS systems with pacman." >&2
  exit 1
}

[[ -r $SCRIPT_DIR/installer/install-cachyfreeze.sh ]] || {
  printf '%s\n' \
    "The complete CachyFreeze repository is required." \
    "Clone https://github.com/q0xs/cachy-freeze.git and run sudo ./install.sh from it." >&2
  exit 1
}

exec /usr/bin/bash "$SCRIPT_DIR/installer/install-cachyfreeze.sh"
