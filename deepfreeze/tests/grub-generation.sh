#!/usr/bin/env bash
set -Eeuo pipefail

readonly ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly OUTPUT=$(mktemp /tmp/cachy-freeze-grub.XXXXXX.cfg)
readonly BOOT_DIR=$(mktemp -d /tmp/cachy-freeze-boot.XXXXXX)

cleanup() {
  rm -f "$OUTPUT"
  rm -rf --one-file-system "$BOOT_DIR"
}

fail() {
  printf 'TEST HATASI: %s\n' "$*" >&2
  exit 1
}

trap cleanup EXIT

touch \
  "$BOOT_DIR/vmlinuz-linux-cachyos" \
  "$BOOT_DIR/initramfs-linux-cachyos.img" \
  "$BOOT_DIR/intel-ucode.img"

CACHY_FREEZE_CONFIG="$ROOT/etc/cachy-freeze.conf" \
  CACHY_FREEZE_BOOT_DIR="$BOOT_DIR" \
  "$ROOT/grub/40_cachy_freeze" >"$OUTPUT"

for id in \
  cachyos-frozen \
  cachyos-maintenance; do
  grep -q -- "--id '$id'" "$OUTPUT" || fail "GRUB girişi eksik: $id"
done

[[ $(grep -c '^menuentry ' "$OUTPUT") -eq 2 ]] ||
  fail "Tam olarak iki kurumsal GRUB girişi üretilmedi."
grep -q 'rootflags=subvol=@active cachy.freeze=1' "$OUTPUT" ||
  fail "Frozen kök parametresi yanlış."
grep -q 'linux /@active/boot/vmlinuz-linux-cachyos ' "$OUTPUT" ||
  fail "Frozen kernel active alt biriminden yüklenmiyor."
grep -q "menuentry 'CachyOS Kurumsal - Frozen'.*--unrestricted" "$OUTPUT" ||
  fail "Frozen girişi parolasız değil."
grep -q 'rootflags=subvol=@ cachy.freeze=0' "$OUTPUT" ||
  fail "Maintenance kök parametresi yanlış."
grep -q 'linux /@/boot/vmlinuz-linux-cachyos ' "$OUTPUT" ||
  fail "Maintenance kernel @ alt biriminden yüklenmiyor."
if grep -q "menuentry 'CachyOS Kurumsal - Maintenance'.*--unrestricted" "$OUTPUT"; then
  fail "Maintenance girişi yanlışlıkla parolasız."
fi

grub-script-check "$OUTPUT"
printf '%s\n' "GRUB üretim ve sözdizimi testi başarılı."
