#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly PROJECT_ROOT=$(cd -- "$INSTALLER_DIR/.." && pwd)
readonly LOG=/var/log/cachyos-workstation-install.log
# shellcheck source=lib/common.sh
source "$INSTALLER_DIR/lib/common.sh"

require_root
require_maintenance

if [[ ${CACHY_SETUP_NONINTERACTIVE:-0} == 1 ]]; then
  IFS= read -r grub_password || die "GRUB parolasi GUI kanalindan alinamadi."
else
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
fi

exec > >(tee -a "$LOG") 2>&1
trap 'rc=$?; printf "HATA: Tamamlama satir %s civarinda durdu (kod: %s). Log: %s\n" "$LINENO" "$rc" "$LOG" >&2' ERR
printf 'Kurulum tamamlama basladi: %s\n' "$(date --iso-8601=seconds)"

if [[ ${CACHY_SETUP_NONINTERACTIVE:-0} == 1 ]]; then
  printf '%s\n' "$grub_password" |
    CACHY_SETUP_NONINTERACTIVE=1 \
      bash "$INSTALLER_DIR/configure-grub-password.sh"
  unset grub_password
else
  bash "$INSTALLER_DIR/configure-grub-password.sh"
fi
bash "$INSTALLER_DIR/refresh-user-templates.sh"
bash "$INSTALLER_DIR/publish-golden.sh"
bash "$INSTALLER_DIR/set-frozen-mode.sh"

printf '%s\n' \
  "Kurulum guvenli sirayla tamamlandi." \
  "Sonraki acilis Frozen olacak." \
  "Hazir oldugunuzda elle yeniden baslatin: sudo reboot" \
  "USB'yi ilk Frozen testi bitene kadar cikarmayin."
