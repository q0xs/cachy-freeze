#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

(( EUID == 0 )) || {
  printf 'Run as root: sudo %s\n' "$0" >&2
  exit 1
}

pacman -S --needed --noconfirm \
  btrfs-progs \
  grub \
  mkinitcpio \
  polkit \
  python-pyqt6

bash "$INSTALLER_DIR/install-freeze-engine.sh"
bash "$INSTALLER_DIR/publish-golden.sh"

printf '%s\n' \
  "CachyFreeze was installed successfully." \
  "Open 'CachyFreeze Management Center' from the application menu." \
  "The system remains in THAWED maintenance mode." \
  "Create users whenever needed, independently from enabling FROZEN mode."
