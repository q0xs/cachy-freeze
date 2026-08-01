#!/usr/bin/env bash
set -Eeuo pipefail

readonly TEST_ROOT=$(mktemp -d /tmp/cachy-freeze-engine.XXXXXX)
readonly IMAGE=$TEST_ROOT/btrfs.img
readonly TOP=$TEST_ROOT/top
readonly STATE=$TEST_ROOT/state
readonly CONFIG=$TEST_ROOT/cachy-freeze.conf
readonly PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
readonly BACKEND=$PROJECT_ROOT/deepfreeze/bin/cachy-freeze
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

run_backend() {
  CACHY_FREEZE_CONFIG=$CONFIG \
    CACHY_FREEZE_ROOT_SUBVOLUME=@ \
    "$BACKEND" "$@"
}

json_result_field() {
  local path=$1 field=$2
  python - "$path" "$field" <<'PY'
import json
import sys

value = json.load(open(sys.argv[1], encoding="utf-8"))["result"]
for component in sys.argv[2].split("."):
    value = value[component]
print(value)
PY
}

(( EUID == 0 )) || fail "Entegrasyon testi root gerektirir."
for command in btrfs blkid grub-editenv losetup mkfs.btrfs python; do
  command -v "$command" >/dev/null || fail "Gerekli test komutu yok: $command"
done
trap cleanup EXIT

truncate -s 1G "$IMAGE"
LOOP_DEVICE=$(losetup --find --show "$IMAGE")
mkfs.btrfs -q -f "$LOOP_DEVICE"
mkdir -p "$TOP" "$STATE"
mount -o subvolid=5 "$LOOP_DEVICE" "$TOP"
btrfs subvolume create "$TOP/@" >/dev/null
mkdir -p "$TOP/@/boot/grub"
touch \
  "$TOP/@/boot/vmlinuz-linux-cachyos" \
  "$TOP/@/boot/initramfs-linux-cachyos.img"
printf "%s\n" "menuentry test --id 'cachyos-current' {" "}" \
  >"$TOP/@/boot/grub/grub.cfg"
grub-editenv "$TOP/@/boot/grub/grubenv" create

cat >"$CONFIG" <<EOF
STATE_DIR=$STATE
TOP_MOUNT=$TOP
MAINTENANCE_SUBVOL=@
GOLDEN_SUBVOL=@golden
GOLDEN_PREVIOUS_SUBVOL=@golden.previous
GOLDEN_NEXT_SUBVOL=@golden.next
GOLDEN_PENDING_SUBVOL=@golden.previous.pending
ACTIVE_SUBVOL=@active
PREVIOUS_SUBVOL=@active.previous
NEXT_SUBVOL=@active.next
ACTIVE_PENDING_SUBVOL=@active.previous.pending
STATE_SUBVOL=@cachy-state
SNAPSHOT_SUBVOL=@cachy-snapshots
EXPORT_DIR=$STATE/exports
LOG_FILE=$STATE/operations.jsonl
LOCK_FILE=$TEST_ROOT/cachy-freeze.lock
RETENTION_COUNT=3
ROOT_UUID=
ROOT_DEVICE=$LOOP_DEVICE
EOF

run_backend snapshot create --description 'Golden v1' >"$TEST_ROOT/one.json"
snapshot_one=$(json_result_field "$TEST_ROOT/one.json" snapshot_id)
printf '%s\n' v2 >"$TOP/@/version"
run_backend snapshot create --description 'Golden v2' >"$TEST_ROOT/two.json"
snapshot_two=$(json_result_field "$TEST_ROOT/two.json" snapshot_id)

run_backend snapshot verify "$snapshot_one" >"$TEST_ROOT/verify.json"
[[ $(json_result_field "$TEST_ROOT/verify.json" healthy) == True ]] ||
  fail "Snapshot hizli dogrulamadan gecmedi."
run_backend snapshot compare "$snapshot_one" "$snapshot_two" \
  >"$TEST_ROOT/compare.json"

run_backend publish --description 'Publish v2' >"$TEST_ROOT/publish.json"
btrfs subvolume show "$TOP/@golden" >/dev/null || fail "Golden olusmadi."
btrfs subvolume show "$TOP/@active" >/dev/null || fail "Active olusmadi."
[[ $(btrfs property get -ts "$TOP/@golden" ro) == ro=true ]] ||
  fail "Golden salt-okunur degil."
[[ $(btrfs property get -ts "$TOP/@active" ro) == ro=false ]] ||
  fail "Active yazilabilir degil."

run_backend snapshot export "$snapshot_one" >"$TEST_ROOT/export.json"
[[ -s $STATE/exports/$snapshot_one.btrfs ]] || fail "Export stream olusmadi."
(cd "$STATE/exports" && sha256sum "$snapshot_one.btrfs") >/dev/null
run_backend snapshot delete "$snapshot_one" >"$TEST_ROOT/delete.json"
run_backend snapshot import "$snapshot_one.btrfs" >"$TEST_ROOT/import.json"
imported=$(json_result_field "$TEST_ROOT/import.json" snapshot_id)
run_backend snapshot rollback "$imported" >"$TEST_ROOT/rollback.json"
grep -qx 'cachy_mode=frozen' <(
  grub-editenv "$TOP/@/boot/grub/grubenv" list
) || fail "Rollback Frozen boot modunu ayarlamadi."
run_backend thaw-once >"$TEST_ROOT/thaw-once.json"
grep -qx 'cachy_once=thawed' <(
  grub-editenv "$TOP/@/boot/grub/grubenv" list
) || fail "Tek seferlik Thawed boot ayarlanamadı."
run_backend thaw >"$TEST_ROOT/thaw.json"
! grep -qx 'cachy_once=thawed' <(
  grub-editenv "$TOP/@/boot/grub/grubenv" list
) || fail "Kalıcı Thawed seçimi tek seferlik ayarı temizlemedi."
run_backend freeze >"$TEST_ROOT/freeze.json"

# Simulate power loss after current Golden was moved to its pending name.
btrfs subvolume snapshot -r "$TOP/@" "$TOP/@golden.next" >/dev/null
btrfs subvolume snapshot "$TOP/@golden.next" "$TOP/@active.next" >/dev/null
PYTHONPATH=$PROJECT_ROOT/src python - "$STATE" <<'PY'
import sys
from pathlib import Path
from cachy_freeze.catalog import SnapshotCatalog

SnapshotCatalog(Path(sys.argv[1])).begin_transaction(
    "publish", "prepared", {"snapshot_id": "power-loss-test"}
)
PY
mv "$TOP/@golden" "$TOP/@golden.previous.pending"
run_backend status >"$TEST_ROOT/recovered-status.json"
[[ ! -e $STATE/transaction.json ]] || fail "Transaction journal temizlenmedi."
btrfs subvolume show "$TOP/@golden" >/dev/null || fail "Golden kurtarilamadi."
btrfs subvolume show "$TOP/@active" >/dev/null || fail "Active kurtarilamadi."

# Exercise repeated metadata/catalog/subvolume lifecycle operations to catch
# leaks, ID collisions, and retention regressions under sustained use.
for iteration in $(seq 1 25); do
  printf 'stress-%s\n' "$iteration" >"$TOP/@/stress-state"
  run_backend snapshot create --description "Stress snapshot $iteration" \
    >"$TEST_ROOT/stress-$iteration.json"
  if (( iteration % 5 == 0 )); then
    printf 'Snapshot stres ilerlemesi: %s/25\n' "$iteration"
  fi
done

run_backend health >"$TEST_ROOT/health.json"
run_backend snapshot cleanup --keep 2 >"$TEST_ROOT/cleanup.json"
[[ $(run_backend snapshot list | python -c 'import json,sys; print(len(json.load(sys.stdin)["result"]))') -eq 2 ]] ||
  fail "Snapshot retention politikasi uygulanmadi."

printf '%s\n' "Snapshot engine entegrasyon testleri başarılı."
