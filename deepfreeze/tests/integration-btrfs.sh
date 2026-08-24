#!/usr/bin/env bash
set -Eeuo pipefail

TEST_ROOT=$(mktemp -d /tmp/cachy-freeze-reset.XXXXXX)
readonly TEST_ROOT
readonly IMAGE=$TEST_ROOT/btrfs.img
readonly TOP=$TEST_ROOT/top
readonly CONFIG=$TEST_ROOT/initrd.conf
readonly BOOT_ID_FILE=$TEST_ROOT/boot-id
readonly ACTIVE_MOUNT=$TEST_ROOT/active-mount
SCRIPT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/initcpio/cachy-freeze-reset
readonly SCRIPT
LOOP_DEVICE=

cleanup() {
  mountpoint -q "$ACTIVE_MOUNT" && umount "$ACTIVE_MOUNT" || true
  mountpoint -q "$TOP" && umount "$TOP" || true
  [[ -z $LOOP_DEVICE ]] || losetup -d "$LOOP_DEVICE"
  rm -rf --one-file-system "$TEST_ROOT"
}
fail() { printf 'TEST ERROR: %s\n' "$*" >&2; exit 1; }
run_reset() {
  CACHY_FREEZE_INITRD_CONFIG=$CONFIG \
    CACHY_FREEZE_TOP=$TEST_ROOT/reset-mount \
    CACHY_FREEZE_BOOT_ID_FILE=$BOOT_ID_FILE \
    "$SCRIPT"
}

set_boot_id() {
  printf '%s\n' "$1" >"$BOOT_ID_FILE"
}

(( EUID == 0 )) || fail "The disposable loopback test requires root."
for command in btrfs grub-editenv losetup mkfs.btrfs; do
  command -v "$command" >/dev/null || fail "Missing test command: $command"
done
trap cleanup EXIT

truncate -s 512M "$IMAGE"
LOOP_DEVICE=$(losetup --find --show "$IMAGE")
mkfs.btrfs -q -f "$LOOP_DEVICE"
mkdir -p "$TOP" "$ACTIVE_MOUNT"
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
btrfs subvolume create "$TOP/@" >/dev/null
btrfs subvolume create "$TOP/@cachy-state" >/dev/null
mkdir -p "$TOP/@/boot/grub" "$TOP/@/etc" "$TOP/@/sbin" "$TOP/@/usr/lib/systemd"
touch "$TOP/@/boot/vmlinuz-linux-cachyos" "$TOP/@/boot/initramfs-linux-cachyos.img"
grub-editenv "$TOP/@/boot/grub/grubenv" create
grub-editenv "$TOP/@/boot/grub/grubenv" set \
  cachy_mode=frozen \
  saved_entry=cachyos-current \
  cachy_recovery=0
printf '%s\n' 'ID=cachyos' >"$TOP/@/etc/os-release"
printf '%s\n' '#!/bin/sh' >"$TOP/@/usr/lib/systemd/systemd"
chmod 0755 "$TOP/@/usr/lib/systemd/systemd"
ln -s ../usr/lib/systemd/systemd "$TOP/@/sbin/init"
printf '%s\n' baseline-a >"$TOP/@/approved"
btrfs subvolume snapshot -r "$TOP/@" "$TOP/@golden" >/dev/null
umount "$TOP"

cat >"$CONFIG" <<EOF
ROOT_UUID=test-only
ROOT_DEVICE=$LOOP_DEVICE
MAINTENANCE_SUBVOL=@
GOLDEN_SUBVOL=@golden
GOLDEN_NEXT_SUBVOL=@golden.next
GOLDEN_PENDING_SUBVOL=@golden.pending
ACTIVE_SUBVOL=@active
ACTIVE_NEXT_SUBVOL=@active.next
ACTIVE_PENDING_SUBVOL=@active.pending
CAPTURE_SUBVOL=@cachy-capture
STATE_SUBVOL=@cachy-state
EOF

set_boot_id 11111111-2222-3333-4444-555555555555
run_reset
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
[[ -f $TOP/@active/approved ]] || fail "The first FROZEN runtime is incomplete."
printf '%s\n' runtime-only >"$TOP/@active/unique-marker"
btrfs subvolume create "$TOP/@active/runtime-nested" >/dev/null
printf '%s\n' nested-runtime-only >"$TOP/@active/runtime-nested/unique-marker"
umount "$TOP"

# A duplicate service start in the same boot must be a no-op. This is the rc5
# physical regression: the old service could delete an already-mounted root.
run_reset
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
[[ -f $TOP/@active/unique-marker ]] ||
  fail "A duplicate reset in the same boot replaced the live runtime."
[[ -d $TOP/@active/runtime-nested ]] ||
  fail "A duplicate reset in the same boot deleted nested runtime state."
umount "$TOP"

# Even with a new boot id, refuse to delete @active while any mount references
# it. The old runtime remains intact until the unsafe mount is gone.
mount -o subvol=@active "$LOOP_DEVICE" "$ACTIVE_MOUNT"
set_boot_id 22222222-3333-4444-5555-666666666666
if run_reset; then
  fail "The reset unexpectedly deleted a mounted disposable runtime."
fi
[[ -f $ACTIVE_MOUNT/unique-marker ]] ||
  fail "Mounted FROZEN runtime data changed during the refused reset."
umount "$ACTIVE_MOUNT"
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
grep -qx 'cachy_mode=thawed' <(grub-editenv "$TOP/@/boot/grub/grubenv" list) ||
  fail "A failed FROZEN reset did not schedule protected THAWED recovery."
umount "$TOP"

run_reset
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
[[ ! -e $TOP/@active/unique-marker ]] || fail "FROZEN runtime data survived reset."
[[ ! -e $TOP/@active/runtime-nested ]] || fail "Nested FROZEN runtime data survived reset."
[[ -f $TOP/@active/approved ]] || fail "Golden content was not restored."
for forbidden in \
  @active.next @active.pending @golden.next @golden.pending @cachy-capture; do
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

set_boot_id 33333333-4444-5555-6666-777777777777
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
