#!/usr/bin/env bash
set -Eeuo pipefail

readonly TEST_ROOT=$(mktemp -d /tmp/cachy-freeze-test.XXXXXX)
readonly IMAGE=$TEST_ROOT/btrfs.img
readonly TOP=$TEST_ROOT/top
readonly CONFIG=$TEST_ROOT/initrd.conf
readonly SCRIPT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/initcpio/cachy-freeze-reset
LOOP_DEVICE=

cleanup() {
  if mountpoint -q "$TOP"; then
    umount "$TOP"
  fi
  if [[ -n $LOOP_DEVICE ]]; then
    losetup -d "$LOOP_DEVICE"
  fi
  rm -rf --one-file-system "$TEST_ROOT"
}

fail() {
  printf 'TEST HATASI: %s\n' "$*" >&2
  exit 1
}

assert_file() {
  [[ -f $1 ]] || fail "Dosya bulunamadı: $1"
}

run_reset() {
  CACHY_FREEZE_INITRD_CONFIG=$CONFIG \
    CACHY_FREEZE_TOP=$TEST_ROOT/reset-mount \
    "$SCRIPT"
}

(( EUID == 0 )) || fail "Entegrasyon testi root gerektirir."
command -v mkfs.btrfs >/dev/null || fail "mkfs.btrfs bulunamadı."
trap cleanup EXIT

truncate -s 512M "$IMAGE"
LOOP_DEVICE=$(losetup --find --show "$IMAGE")
mkfs.btrfs -q -f "$LOOP_DEVICE"
mkdir -p "$TOP"
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"

btrfs subvolume create "$TOP/@maintenance" >/dev/null
printf '%s\n' golden-v1 >"$TOP/@maintenance/version"
btrfs subvolume snapshot -r "$TOP/@maintenance" "$TOP/@golden" >/dev/null
umount "$TOP"

cat >"$CONFIG" <<EOF
ROOT_UUID=test-only
ROOT_DEVICE=$LOOP_DEVICE
MAINTENANCE_SUBVOL=@maintenance
GOLDEN_SUBVOL=@golden
ACTIVE_SUBVOL=@active
PREVIOUS_SUBVOL=@active.previous
NEXT_SUBVOL=@active.next
EOF

# First frozen boot.
run_reset
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
assert_file "$TOP/@active/version"
printf '%s\n' user-change >"$TOP/@active/unwanted"
umount "$TOP"

# A normal reboot must remove changes made to active.
run_reset
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
[[ ! -e $TOP/@active/unwanted ]] || fail "Kullanıcı değişikliği sıfırlanmadı."
assert_file "$TOP/@active/version"

# Simulate a power loss between active->previous and next->active.
btrfs subvolume delete "$TOP/@active.previous" >/dev/null
btrfs subvolume snapshot "$TOP/@golden" "$TOP/@active.next" >/dev/null
mv "$TOP/@active" "$TOP/@active.previous"
umount "$TOP"

run_reset
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
assert_file "$TOP/@active/version"
[[ $(<"$TOP/@active/version") == golden-v1 ]] ||
  fail "Kurtarılan active yanlış golden sürümünde."

printf '%s\n' "Btrfs entegrasyon testleri başarılı."
