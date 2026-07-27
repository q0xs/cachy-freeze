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

grep -q -- "--id 'cachyos-current'" "$OUTPUT" ||
  fail "Tek GRUB girişi eksik."
[[ $(grep -c '^menuentry ' "$OUTPUT") -eq 1 ]] ||
  fail "Tam olarak bir kurumsal GRUB girişi üretilmedi."
grep -q 'set cachy_title="FROZEN"' "$OUTPUT" ||
  fail "Frozen başlığı eksik."
grep -q 'set cachy_title="THAWED"' "$OUTPUT" ||
  fail "Thawed başlığı eksik."
grep -q 'set cachy_subvol="@active"' "$OUTPUT" ||
  fail "Frozen kök seçimi yanlış."
grep -q 'set cachy_subvol="@"' "$OUTPUT" ||
  fail "Thawed kök seçimi yanlış."
grep -q 'set cachy_freeze_arg="cachy.freeze=1"' "$OUTPUT" ||
  fail "Frozen kernel parametresi yanlış."
grep -q 'set cachy_freeze_arg="cachy.freeze=0"' "$OUTPUT" ||
  fail "Thawed kernel parametresi yanlış."
grep -Fq 'linux /$cachy_subvol/boot/vmlinuz-linux-cachyos ' "$OUTPUT" ||
  fail "Kernel dinamik alt birimden yüklenmiyor."
grep -Fq 'if [ "${cachy_mode}" = "thawed" ]; then' "$OUTPUT" ||
  fail "Thawed yetkilendirme koşulu eksik."
grep -q '^[[:space:]]*authenticate$' "$OUTPUT" ||
  fail "Thawed GRUB parola denetimi eksik."
grep -q "^menuentry .*--unrestricted" "$OUTPUT" ||
  fail "Frozen girişinin parolasız seçimi eksik."

grub-script-check "$OUTPUT"
printf '%s\n' "GRUB üretim ve sözdizimi testi başarılı."
