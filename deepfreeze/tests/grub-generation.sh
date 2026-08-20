#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly ROOT
OUTPUT=$(mktemp /tmp/cachy-freeze-grub.XXXXXX.cfg)
readonly OUTPUT
BOOT_DIR=$(mktemp -d /tmp/cachy-freeze-boot.XXXXXX)
readonly BOOT_DIR
FAKE_BIN=$(mktemp -d /tmp/cachy-freeze-bin.XXXXXX)
readonly FAKE_BIN

cleanup() {
  rm -f "$OUTPUT"
  rm -rf --one-file-system "$BOOT_DIR"
  rm -rf --one-file-system "$FAKE_BIN"
}

fail() {
  printf 'TEST ERROR: %s\n' "$*" >&2
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
  fail "The managed GRUB entry is missing."
[[ $(grep -c '^menuentry ' "$OUTPUT") -eq 1 ]] ||
  fail "Exactly one managed GRUB entry was not generated."
grep -q 'set cachy_title="FROZEN"' "$OUTPUT" ||
  fail "The FROZEN title is missing."
grep -q 'set cachy_title="THAWED"' "$OUTPUT" ||
  fail "The THAWED title is missing."
grep -q 'set cachy_subvol="@active"' "$OUTPUT" ||
  fail "The FROZEN root selection is incorrect."
grep -q 'set cachy_subvol="@"' "$OUTPUT" ||
  fail "The THAWED root selection is incorrect."
grep -q 'set cachy_freeze_arg="cachy.freeze=1"' "$OUTPUT" ||
  fail "The FROZEN kernel argument is incorrect."
grep -q 'set cachy_freeze_arg="cachy.freeze=0"' "$OUTPUT" ||
  fail "The THAWED kernel argument is incorrect."
grep -Fq 'linux /$cachy_subvol/boot/vmlinuz-linux-cachyos ' "$OUTPUT" ||
  fail "The kernel is not loaded from the dynamic subvolume."
grep -Fq 'if [ "${cachy_effective_mode}" = "thawed" ]; then' "$OUTPUT" ||
  fail "The THAWED authorization condition is missing."
grep -q '^[[:space:]]*if authenticate; then$' "$OUTPUT" ||
  fail "The THAWED GRUB password check is missing."
grep -q 'set cachy_boot_authorized="false"' "$OUTPUT" ||
  fail "The GRUB authorization guard does not fail closed."
grep -q 'if \[ "\${cachy_boot_authorized}" = "true" \]; then' "$OUTPUT" ||
  fail "Kernel loading is not guarded by successful authentication."
grep -Fq 'set cachy_effective_mode="thawed"' "$OUTPUT" ||
  fail "One-time Thawed mode is not selected."
grep -q "^menuentry .*--unrestricted" "$OUTPUT" ||
  fail "Passwordless selection of the FROZEN entry is missing."

grub-script-check "$OUTPUT"
printf '%s\n' "GRUB generation and syntax tests passed."
