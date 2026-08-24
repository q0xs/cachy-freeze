#!/usr/bin/env bash
set -Eeuo pipefail

TEST_ROOT=$(mktemp -d /tmp/cachy-freeze-reset.XXXXXX)
readonly TEST_ROOT
readonly IMAGE=$TEST_ROOT/btrfs.img
readonly TOP=$TEST_ROOT/top
readonly CONFIG=$TEST_ROOT/initrd.conf
SCRIPT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/initcpio/cachy-freeze-reset
readonly SCRIPT
LOOP_DEVICE=

cleanup() {
  mountpoint -q "$TOP" && umount "$TOP" || true
  [[ -z $LOOP_DEVICE ]] || losetup -d "$LOOP_DEVICE"
  rm -rf --one-file-system "$TEST_ROOT"
}
fail() { printf 'TEST ERROR: %s\n' "$*" >&2; exit 1; }
run_reset() {
  CACHY_FREEZE_INITRD_CONFIG=$CONFIG \
    CACHY_FREEZE_TOP=$TEST_ROOT/reset-mount \
    "$SCRIPT"
}

(( EUID == 0 )) || fail "The disposable loopback test requires root."
for command in btrfs losetup mkfs.btrfs; do
  command -v "$command" >/dev/null || fail "Missing test command: $command"
done
trap cleanup EXIT

truncate -s 512M "$IMAGE"
LOOP_DEVICE=$(losetup --find --show "$IMAGE")
mkfs.btrfs -q -f "$LOOP_DEVICE"
mkdir -p "$TOP"
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
btrfs subvolume create "$TOP/@" >/dev/null
btrfs subvolume create "$TOP/@cachy-state" >/dev/null
mkdir -p "$TOP/@/boot"
touch "$TOP/@/boot/vmlinuz-linux-cachyos" "$TOP/@/boot/initramfs-linux-cachyos.img"
printf '%s\n' baseline-a >"$TOP/@/approved"
btrfs subvolume snapshot -r "$TOP/@" "$TOP/@golden" >/dev/null
umount "$TOP"

cat >"$CONFIG" <<EOF
ROOT_UUID=test-only
ROOT_DEVICE=$LOOP_DEVICE
GOLDEN_SUBVOL=@golden
GOLDEN_NEXT_SUBVOL=@golden.next
GOLDEN_PENDING_SUBVOL=@golden.pending
ACTIVE_SUBVOL=@active
ACTIVE_NEXT_SUBVOL=@active.next
ACTIVE_PENDING_SUBVOL=@active.pending
STATE_SUBVOL=@cachy-state
EOF

run_reset
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
[[ -f $TOP/@active/approved ]] || fail "The first FROZEN runtime is incomplete."
printf '%s\n' runtime-only >"$TOP/@active/unique-marker"
umount "$TOP"

run_reset
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
[[ ! -e $TOP/@active/unique-marker ]] || fail "FROZEN runtime data survived reset."
[[ -f $TOP/@active/approved ]] || fail "Golden content was not restored."
for forbidden in @active.next @active.pending @golden.next @golden.pending; do
  [[ ! -e $TOP/$forbidden ]] || fail "Transaction object remains: $forbidden"
done

# Simulate interruption after old Golden moved to its transaction-scoped
# pending name. Initramfs must roll back, not archive or promote the candidate.
printf '%s\n' candidate-b >"$TOP/@/approved"
btrfs subvolume snapshot -r "$TOP/@" "$TOP/@golden.next" >/dev/null
mv "$TOP/@golden" "$TOP/@golden.pending"
printf '%s\n' \
  '{"schema":2,"kind":"publish","phase":"prepared","baseline_id":"1234567890abcdef1234567890abcdef","source_subvolume":"@"}' \
  >"$TOP/@cachy-state/transaction.json"
umount "$TOP"

run_reset
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
[[ $(<"$TOP/@active/approved") == baseline-a ]] ||
  fail "Interrupted baseline was not rolled back safely."
[[ ! -e $TOP/@cachy-state/transaction.json ]] || fail "Transaction journal stayed active."
[[ -e $TOP/@cachy-state/transaction.initramfs-rolled-back.json ]] ||
  fail "The non-sensitive recovery record is missing."
for forbidden in \
  @active.next @active.pending @golden.next @golden.pending \
  @active.previous @golden.previous @cachy-snapshots; do
  [[ ! -e $TOP/$forbidden ]] || fail "Historical data-bearing object exists: $forbidden"
done

printf '%s\n' "Btrfs reset and no-history integration tests passed."
