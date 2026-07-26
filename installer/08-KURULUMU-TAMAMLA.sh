#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly PROJECT_ROOT=$(cd -- "$INSTALLER_DIR/.." && pwd)
# shellcheck source=lib/common.sh
source "$INSTALLER_DIR/lib/common.sh"

require_root
require_maintenance

[[ -r /dev/tty && -w /dev/tty ]] ||
  die "Kurulumu tamamlamak icin etkilesimli terminal gerekli."

cat >/dev/tty <<'EOF'
Bu son adim sirasiyla:
  1. GRUB Maintenance parolasini ayarlar.
  2. Mevcut Maintenance sistemini Golden olarak yayinlar.
  3. Sonraki acilisi Frozen olarak ayarlar.

Devam etmeden once calisan hesabinda Chrome, Slack, AnyDesk, LibreOffice,
MicroSIP ve Zoiper uygulamalarini kontrol etmis olmalisiniz.
EOF

read -r -p "Kontroller tamamlandi mi? [e/H]: " confirmed </dev/tty
[[ ${confirmed,,} == e ]] || die "Islem iptal edildi; sistem degistirilmedi."

bash "$INSTALLER_DIR/07-GRUB-MAINTENANCE-SIFRE-KOY.sh"
bash "$INSTALLER_DIR/10-CALISAN-SABLONUNU-GUNCELLE.sh"
bash "$INSTALLER_DIR/06-GOLDEN-YAYINLA.sh"
bash "$INSTALLER_DIR/04-DONDUR.sh"

printf '%s\n' \
  "Kurulum guvenli sirayla tamamlandi." \
  "Sonraki acilis Frozen olacak." \
  "Hazir oldugunuzda elle yeniden baslatin: sudo reboot" \
  "USB'yi ilk Frozen testi bitene kadar cikarmayin."
