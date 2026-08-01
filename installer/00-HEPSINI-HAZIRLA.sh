#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly PROJECT_ROOT=$(cd -- "$INSTALLER_DIR/.." && pwd)
readonly LOG=/var/log/cachyos-workstation-install.log

(( EUID == 0 )) || {
  printf 'Su sekilde calistir:\n  sudo %s\n' "$0" >&2
  exit 1
}

if [[ ${CACHY_SETUP_NONINTERACTIVE:-0} == 1 ]]; then
  IFS= read -r setup_employee_user || exit 2
  IFS= read -r setup_employee_name || exit 2
  IFS= read -r setup_employee_password || exit 2
fi

exec > >(tee -a "$LOG") 2>&1
trap 'rc=$?; printf "HATA: Kurulum satir %s civarinda durdu (kod: %s). Log: %s\n" "$LINENO" "$rc" "$LOG" >&2' ERR
printf 'Kurulum basladi: %s\n' "$(date --iso-8601=seconds)"

# Uzun uygulama indirmelerinden önce disk ve açılış düzenini doğrula.
CACHY_FREEZE_CONFIG="$PROJECT_ROOT/deepfreeze/etc/cachy-freeze.conf" \
  bash "$PROJECT_ROOT/deepfreeze/bin/cachy-freeze" preflight

bash "$INSTALLER_DIR/02-UYGULAMALARI-KUR.sh"
if [[ ${CACHY_SETUP_NONINTERACTIVE:-0} == 1 ]]; then
  printf '%s\n%s\n%s\n' \
    "$setup_employee_user" "$setup_employee_name" "$setup_employee_password" |
    CACHY_SETUP_NONINTERACTIVE=1 \
      bash "$INSTALLER_DIR/03-CALISAN-KULLANICI-OLUSTUR.sh"
  unset setup_employee_password
else
  bash "$INSTALLER_DIR/03-CALISAN-KULLANICI-OLUSTUR.sh"
fi
bash "$INSTALLER_DIR/01-DEEPFREEZE-KUR.sh"
bash "$INSTALLER_DIR/06-GOLDEN-YAYINLA.sh"

printf '%s\n' \
  "Tum hazirliklar tamamlandi." \
  "Sistem guvenlik icin Maintenance modunda birakildi." \
  "Canli kontrollerden sonra Kurulum sayfasindan tamamlayip FROZEN yapin." \
  "Log: $LOG"
