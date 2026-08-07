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
  printf 'TEST ERROR: %s\n' "$*" >&2
  exit 1
}

assert_file() {
  [[ -f $1 ]] || fail "File not found: $1"
}

run_reset() {
  CACHY_FREEZE_INITRD_CONFIG=$CONFIG \
    CACHY_FREEZE_TOP=$TEST_ROOT/reset-mount \
    "$SCRIPT"
}

(( EUID == 0 )) || fail "Entegrasyon testi root gerektirir."
command -v mkfs.btrfs >/dev/null || fail "mkfs.btrfs was not found."
trap cleanup EXIT

truncate -s 512M "$IMAGE"
LOOP_DEVICE=$(losetup --find --show "$IMAGE")
mkfs.btrfs -q -f "$LOOP_DEVICE"
mkdir -p "$TOP"
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"

btrfs subvolume create "$TOP/@maintenance" >/dev/null
btrfs subvolume create "$TOP/@cachy-state" >/dev/null
printf '%s\n' golden-v1 >"$TOP/@maintenance/version"
btrfs subvolume snapshot -r "$TOP/@maintenance" "$TOP/@golden" >/dev/null
umount "$TOP"

cat >"$CONFIG" <<EOF
ROOT_UUID=test-only
ROOT_DEVICE=$LOOP_DEVICE
MAINTENANCE_SUBVOL=@maintenance
GOLDEN_SUBVOL=@golden
GOLDEN_PREVIOUS_SUBVOL=@golden.previous
GOLDEN_NEXT_SUBVOL=@golden.next
GOLDEN_PENDING_SUBVOL=@golden.previous.pending
FAILED_GOLDEN_SUBVOL=@golden.failed
ACTIVE_SUBVOL=@active
PREVIOUS_SUBVOL=@active.previous
NEXT_SUBVOL=@active.next
ACTIVE_PENDING_SUBVOL=@active.previous.pending
STATE_SUBVOL=@cachy-state
BOOT_FAILURE_LIMIT=3
EOF

# First frozen boot.
run_reset
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
assert_file "$TOP/@active/version"
printf '0\n' >"$TOP/@cachy-state/boot-attempts"
printf '%s\n' user-change >"$TOP/@active/unwanted"
umount "$TOP"

# A normal reboot must remove changes made to active.
run_reset
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
[[ ! -e $TOP/@active/unwanted ]] || fail "The user change was not reset."
assert_file "$TOP/@active/version"

printf '0\n' >"$TOP/@cachy-state/boot-attempts"

# Simulate a power loss after Golden moved aside but before the candidate was
# promoted. At initramfs time, subvolume names must be enough for recovery.
printf '%s\n' golden-v2 >"$TOP/@maintenance/version"
btrfs subvolume snapshot -r "$TOP/@maintenance" "$TOP/@golden.next" >/dev/null
mv "$TOP/@golden" "$TOP/@golden.previous.pending"
printf '%s\n' '{"schema":1,"kind":"publish","phase":"prepared"}' \
  >"$TOP/@cachy-state/transaction.json"
umount "$TOP"

run_reset
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
[[ $(<"$TOP/@active/version") == golden-v2 ]] ||
  fail "Power-loss recovery did not publish the Golden candidate."
printf '0\n' >"$TOP/@cachy-state/boot-attempts"
[[ ! -e $TOP/@cachy-state/transaction.json ]] ||
  fail "Initramfs recovered transaction journal is still active."
[[ -s $TOP/@cachy-state/transaction.initramfs-recovered.json ]] ||
  fail "Recovered transaction journal was not preserved for diagnostics."
for transient in @golden.next @golden.previous.pending @active.next @active.previous.pending; do
  [[ ! -e $TOP/$transient ]] || fail "Transient subvolume was not cleaned: $transient"
done

# Simulate a power loss between active->previous and next->active.
btrfs subvolume delete "$TOP/@active.previous" >/dev/null
btrfs subvolume snapshot "$TOP/@golden" "$TOP/@active.next" >/dev/null
mv "$TOP/@active" "$TOP/@active.previous"
umount "$TOP"

run_reset
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
assert_file "$TOP/@active/version"
[[ $(<"$TOP/@active/version") == golden-v2 ]] ||
  fail "Recovered Active was created from the wrong Golden version."

# Three consecutive unconfirmed boots automatically restore the previous
# known-good Golden before the root filesystem is mounted.
printf '2\n' >"$TOP/@cachy-state/boot-attempts"
umount "$TOP"
run_reset
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
[[ $(<"$TOP/@active/version") == golden-v1 ]] ||
  fail "Automatic failed-boot rollback did not restore the previous Golden."
[[ $(<"$TOP/@golden.failed/version") == golden-v2 ]] ||
  fail "Failed Golden was not preserved for diagnostics."
[[ $(<"$TOP/@cachy-state/recovery-event") == automatic-rollback ]] ||
  fail "Automatic recovery event was not persisted."

printf '%s\n' "Btrfs integration tests passed."
