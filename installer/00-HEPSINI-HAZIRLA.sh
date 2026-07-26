#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly PROJECT_ROOT=$(cd -- "$INSTALLER_DIR/.." && pwd)
readonly LOG=/var/log/cachyos-workstation-install.log

(( EUID == 0 )) || {
  printf 'Su sekilde calistir:\n  sudo %s\n' "$0" >&2
  exit 1
}

exec > >(tee -a "$LOG") 2>&1
trap 'rc=$?; printf "HATA: Kurulum satir %s civarinda durdu (kod: %s). Log: %s\n" "$LINENO" "$rc" "$LOG" >&2' ERR
printf 'Kurulum basladi: %s\n' "$(date --iso-8601=seconds)"

# Uzun uygulama indirmelerinden önce disk ve açılış düzenini doğrula.
CACHY_FREEZE_CONFIG="$PROJECT_ROOT/deepfreeze/etc/cachy-freeze.conf" \
  bash "$PROJECT_ROOT/deepfreeze/bin/cachy-freeze" preflight

bash "$INSTALLER_DIR/02-UYGULAMALARI-KUR.sh"
bash "$INSTALLER_DIR/03-CALISAN-KULLANICI-OLUSTUR.sh"
bash "$INSTALLER_DIR/01-DEEPFREEZE-KUR.sh"
bash "$INSTALLER_DIR/06-GOLDEN-YAYINLA.sh"

printf '%s\n' \
  "Tum hazirliklar tamamlandi." \
  "Sistem guvenlik icin Maintenance modunda birakildi." \
  "Fiziksel boot testi icin 04-DONDUR.sh daha sonra calistirilmalidir." \
  "Log: $LOG"
