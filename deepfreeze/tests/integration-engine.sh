#!/usr/bin/env bash
set -Eeuo pipefail

TEST_ROOT=$(mktemp -d /tmp/cachy-freeze-engine.XXXXXX)
readonly TEST_ROOT
readonly IMAGE=$TEST_ROOT/btrfs.img
readonly TOP=$TEST_ROOT/top
readonly STATE=$TEST_ROOT/state
readonly CONFIG=$TEST_ROOT/cachy-freeze.conf
PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
readonly PROJECT_ROOT
LOOP_DEVICE=

cleanup() {
  mountpoint -q "$TOP" && umount "$TOP" || true
  [[ -z $LOOP_DEVICE ]] || losetup -d "$LOOP_DEVICE"
  rm -rf --one-file-system "$TEST_ROOT"
}
fail() { printf 'TEST ERROR: %s\n' "$*" >&2; exit 1; }
run_backend() {
  PYTHONPATH=$PROJECT_ROOT/src \
    PYTHONNOUSERSITE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
  CACHY_FREEZE_CONFIG=$CONFIG \
    CACHY_FREEZE_ROOT_SUBVOLUME=${TEST_RUNNING_SUBVOL:-@} \
    /usr/bin/python -s -m cachy_freeze.cli "$@"
}

(( EUID == 0 )) || fail "The disposable loopback test requires root."
for command in btrfs blkid chattr grub-editenv losetup mkfs.btrfs python; do
  command -v "$command" >/dev/null || fail "Missing test command: $command"
done
trap cleanup EXIT

truncate -s 1G "$IMAGE"
LOOP_DEVICE=$(losetup --find --show "$IMAGE")
mkfs.btrfs -q -f "$LOOP_DEVICE"
mkdir -p "$TOP" "$STATE"
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
btrfs subvolume create "$TOP/@" >/dev/null
mkdir -p "$TOP/@/boot/grub" "$TOP/@/etc" "$TOP/@/sbin" "$TOP/@/usr/lib/systemd"
touch "$TOP/@/boot/vmlinuz-linux-cachyos" "$TOP/@/boot/initramfs-linux-cachyos.img"
printf '%s\n' 'ID=cachyos' >"$TOP/@/etc/os-release"
printf '%s\n' '#!/bin/sh' >"$TOP/@/usr/lib/systemd/systemd"
chmod 0755 "$TOP/@/usr/lib/systemd/systemd"
ln -s ../usr/lib/systemd/systemd "$TOP/@/sbin/init"
printf "%s\n" "menuentry test --id 'cachyos-current' {" "}" \
  >"$TOP/@/boot/grub/grub.cfg"
grub-editenv "$TOP/@/boot/grub/grubenv" create
grub-editenv "$TOP/@/boot/grub/grubenv" set \
  cachy_mode=thawed \
  saved_entry=cachyos-current \
  cachy_recovery=0
printf '%s\n' maintained-a >"$TOP/@/approved"
mkdir -p "$TOP/@/var/lib"
btrfs subvolume create "$TOP/@/.snapshots" >/dev/null
btrfs subvolume create "$TOP/@/var/lib/machines" >/dev/null
btrfs subvolume create "$TOP/@/var/lib/portables" >/dev/null
printf '%s\n' historical-third-party-data >"$TOP/@/.snapshots/old-marker"
touch "$TOP/@/var/lib/machines/approved-marker"
chattr +C "$TOP/@/var/lib/machines/approved-marker"
printf '%s\n' approved-machine-data >"$TOP/@/var/lib/machines/approved-marker"

cat >"$CONFIG" <<EOF
STATE_DIR=$STATE
STATE_SUBVOL=@cachy-state
TOP_MOUNT=$TOP
MAINTENANCE_SUBVOL=@
GOLDEN_SUBVOL=@golden
GOLDEN_NEXT_SUBVOL=@golden.next
GOLDEN_PENDING_SUBVOL=@golden.pending
ACTIVE_SUBVOL=@active
ACTIVE_NEXT_SUBVOL=@active.next
ACTIVE_PENDING_SUBVOL=@active.pending
CAPTURE_SUBVOL=@cachy-capture
LEGACY_SNAPSHOT_SUBVOL=@cachy-snapshots
LOG_FILE=$STATE/operations.jsonl
LOCK_FILE=$TEST_ROOT/cachy-freeze.lock
ROOT_UUID=
ROOT_DEVICE=$LOOP_DEVICE
EOF

run_backend freeze >"$TEST_ROOT/freeze.json"
[[ -f $TOP/@golden/approved && -f $TOP/@active/approved ]] ||
  fail "FREEZE did not create the Golden/Active pair."
[[ -f $TOP/@golden/var/lib/machines/approved-marker ]] ||
  fail "The standard nested machine data was not flattened into Golden."
[[ ! -e $TOP/@golden/.snapshots/old-marker ]] ||
  fail "Third-party Snapper history was copied into Golden."
[[ -f $TOP/@/.snapshots/old-marker ]] ||
  fail "Third-party Snapper history was modified."
[[ ! -e $TOP/@cachy-capture ]] ||
  fail "The transaction-scoped capture remained after FREEZE."
[[ $(btrfs property get -ts "$TOP/@golden" ro) == ro=true ]] ||
  fail "Golden is not read-only."
grep -qx 'cachy_mode=frozen' <(grub-editenv "$TOP/@/boot/grub/grubenv" list) ||
  fail "FROZEN was not scheduled."

for cycle in 1 2 3 4; do
  printf 'maintained-%s\n' "$cycle" >"$TOP/@/approved"
  grub-editenv "$TOP/@/boot/grub/grubenv" set cachy_mode=thawed
  run_backend freeze >"$TEST_ROOT/freeze-$cycle.json"
done
for forbidden in \
  @golden.next @golden.pending @active.next @active.pending \
  @golden.previous @active.previous @cachy-capture @cachy-snapshots; do
  [[ ! -e $TOP/$forbidden ]] || fail "History accumulated: $forbidden"
done

printf '%s\n' runtime-only >"$TOP/@active/unique-marker"
TEST_RUNNING_SUBVOL=@active run_backend thaw >"$TEST_ROOT/thaw.json"
[[ ! -e $TOP/@/unique-marker && ! -e $TOP/@golden/unique-marker ]] ||
  fail "THAW promoted disposable runtime data."
TEST_RUNNING_SUBVOL=@ run_backend boot-success >"$TEST_ROOT/boot-success.json"
[[ ! -e $TOP/@active ]] || fail "THAWED boot retained stale @active."

# Mismatched legacy contents must fail closed without deletion.
btrfs subvolume create "$TOP/@cachy-snapshots" >/dev/null
btrfs subvolume create "$TOP/@cachy-snapshots/unowned" >/dev/null
printf '%s\n' '{"schema":1,"snapshots":[]}' >"$STATE/snapshots.json"
if run_backend migrate >"$TEST_ROOT/migrate.json" 2>"$TEST_ROOT/migrate.err"; then
  fail "Ambiguous legacy history was accepted."
fi
btrfs subvolume show "$TOP/@cachy-snapshots/unowned" >/dev/null ||
  fail "Fail-closed migration deleted unowned data."

printf '%s\n' "Freeze/thaw engine integration tests passed."
