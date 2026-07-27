#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

(( EUID == 0 )) || {
  printf 'Su sekilde calistir: sudo %s\n' "$0" >&2
  exit 1
}

pacman -S --needed --noconfirm \
  btrfs-progs \
  grub \
  mkinitcpio \
  polkit \
  python-pyqt6

bash "$INSTALLER_DIR/01-DEEPFREEZE-KUR.sh"
bash "$INSTALLER_DIR/06-GOLDEN-YAYINLA.sh"

printf '%s\n' \
  "Cachy Freeze Yoneticisi kuruldu." \
  "Uygulama menusunde 'Cachy Freeze Yoneticisi' adiyla bulabilirsiniz." \
  "Sistem simdilik Eritilmis (Bakim) modunda birakildi." \
  "Hazir oldugunuzda uygulamadan Dondur secenegini kullanin."
