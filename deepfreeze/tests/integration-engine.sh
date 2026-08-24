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
readonly BACKEND=$PROJECT_ROOT/deepfreeze/bin/cachy-freeze
LOOP_DEVICE=

cleanup() {
  mountpoint -q "$TOP" && umount "$TOP" || true
  [[ -z $LOOP_DEVICE ]] || losetup -d "$LOOP_DEVICE"
  rm -rf --one-file-system "$TEST_ROOT"
}
fail() { printf 'TEST ERROR: %s\n' "$*" >&2; exit 1; }
run_backend() {
  CACHY_FREEZE_CONFIG=$CONFIG \
    CACHY_FREEZE_ROOT_SUBVOLUME=${TEST_RUNNING_SUBVOL:-@} \
    "$BACKEND" "$@"
}

(( EUID == 0 )) || fail "The disposable loopback test requires root."
for command in btrfs blkid grub-editenv losetup mkfs.btrfs python; do
  command -v "$command" >/dev/null || fail "Missing test command: $command"
done
trap cleanup EXIT

truncate -s 1G "$IMAGE"
LOOP_DEVICE=$(losetup --find --show "$IMAGE")
mkfs.btrfs -q -f "$LOOP_DEVICE"
mkdir -p "$TOP" "$STATE"
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
btrfs subvolume create "$TOP/@" >/dev/null
mkdir -p "$TOP/@/boot/grub"
touch "$TOP/@/boot/vmlinuz-linux-cachyos" "$TOP/@/boot/initramfs-linux-cachyos.img"
printf "%s\n" "menuentry test --id 'cachyos-current' {" "}" \
  >"$TOP/@/boot/grub/grub.cfg"
grub-editenv "$TOP/@/boot/grub/grubenv" create
grub-editenv "$TOP/@/boot/grub/grubenv" set cachy_mode=thawed saved_entry=cachyos-current
printf '%s\n' maintained-a >"$TOP/@/approved"

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
LEGACY_SNAPSHOT_SUBVOL=@cachy-snapshots
LOG_FILE=$STATE/operations.jsonl
LOCK_FILE=$TEST_ROOT/cachy-freeze.lock
ROOT_UUID=
ROOT_DEVICE=$LOOP_DEVICE
EOF

run_backend freeze >"$TEST_ROOT/freeze.json"
[[ -f $TOP/@golden/approved && -f $TOP/@active/approved ]] ||
  fail "FREEZE did not create the Golden/Active pair."
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
  @golden.previous @active.previous @cachy-snapshots; do
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
