#!/usr/bin/env bash
set -Eeuo pipefail

readonly ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly OUTPUT=$(mktemp /tmp/cachy-freeze-grub.XXXXXX.cfg)
readonly BOOT_DIR=$(mktemp -d /tmp/cachy-freeze-boot.XXXXXX)
readonly FAKE_BIN=$(mktemp -d /tmp/cachy-freeze-bin.XXXXXX)

cleanup() {
  rm -f "$OUTPUT"
  rm -rf --one-file-system "$BOOT_DIR"
  rm -rf --one-file-system "$FAKE_BIN"
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

cat >"$FAKE_BIN/findmnt" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' '11111111-2222-3333-4444-555555555555'
EOF
chmod 0755 "$FAKE_BIN/findmnt"

PATH="$FAKE_BIN:$PATH" \
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
grep -Fq 'if [ "${cachy_effective_mode}" = "thawed" ]; then' "$OUTPUT" ||
  fail "Thawed yetkilendirme koşulu eksik."
grep -q '^[[:space:]]*authenticate$' "$OUTPUT" ||
  fail "Thawed GRUB parola denetimi eksik."
grep -Fq 'set cachy_effective_mode="thawed"' "$OUTPUT" ||
  fail "One-time Thawed mode is not selected."
grep -q "^menuentry .*--unrestricted" "$OUTPUT" ||
  fail "Frozen girişinin parolasız seçimi eksik."

grub-script-check "$OUTPUT"
printf '%s\n' "GRUB üretim ve sözdizimi testi başarılı."
