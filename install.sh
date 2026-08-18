#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)
readonly SCRIPT_DIR

if (( EUID != 0 )); then
  if [[ -t 0 && -t 1 ]]; then
    exec sudo /usr/bin/bash "$SCRIPT_DIR/install.sh" "$@"
  fi
  command -v pkexec >/dev/null 2>&1 || {
    printf '%s\n' \
      "A graphical PolicyKit agent is required when installing without a terminal." >&2
    exit 1
  }
  exec pkexec /usr/bin/bash "$SCRIPT_DIR/install.sh" "$@"
fi

command -v pacman >/dev/null 2>&1 || {
  printf '%s\n' "CachyFreeze supports Arch Linux/CachyOS systems with pacman." >&2
  exit 1
}

[[ -r $SCRIPT_DIR/installer/install-cachyfreeze.sh ]] || {
  printf '%s\n' \
    "The complete CachyFreeze repository is required." \
    "Download and extract the complete GitHub ZIP, then open cachyfreeze-setup.desktop." >&2
  exit 1
}

exec /usr/bin/bash "$SCRIPT_DIR/installer/install-cachyfreeze.sh"
