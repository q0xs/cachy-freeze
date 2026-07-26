#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib/common.sh
source "$INSTALLER_DIR/lib/common.sh"

require_root
require_maintenance

[[ -r /dev/tty && -w /dev/tty ]] ||
  die "Bakimi tamamlamak icin etkilesimli terminal gerekli."

printf '%s\n' \
  "Bu islem mevcut Maintenance sistemini Golden olarak yayinlayacak" \
  "ve sonraki acilisi Frozen yapacak." >/dev/tty
read -r -p "Bakim kontrolleri tamamlandi mi? [e/H]: " confirmed </dev/tty
[[ ${confirmed,,} == e ]] || die "Islem iptal edildi; sistem degistirilmedi."

bash "$INSTALLER_DIR/10-CALISAN-SABLONUNU-GUNCELLE.sh"
bash "$INSTALLER_DIR/06-GOLDEN-YAYINLA.sh"
bash "$INSTALLER_DIR/04-DONDUR.sh"

printf '%s\n' \
  "Bakim degisiklikleri Golden'a aktarildi." \
  "Sonraki acilis Frozen olacak." \
  "Hazir oldugunuzda elle yeniden baslatin: sudo reboot"
