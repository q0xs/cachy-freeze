#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly ROOT
TEST_DIR=$(mktemp -d /tmp/cachy-freeze-initramfs.XXXXXX)
readonly TEST_DIR
readonly INSTALLED_RESET=/usr/lib/cachy-freeze/cachy-freeze-reset
readonly INSTALLED_UNIT=/usr/lib/systemd/system/cachy-freeze-reset.service
readonly INSTALLED_HOOK=/etc/initcpio/install/cachy-freeze
readonly INSTALLED_CONFIG=/etc/cachy-freeze-initrd.conf

cleanup() {
  rm -f \
    "$INSTALLED_RESET" \
    "$INSTALLED_UNIT" \
    "$INSTALLED_HOOK" \
    "$INSTALLED_CONFIG"
  rmdir /usr/lib/cachy-freeze 2>/dev/null || true
  rm -rf --one-file-system "$TEST_DIR"
}

fail() {
  printf 'TEST ERROR: %s\n' "$*" >&2
  exit 1
}

(( EUID == 0 )) || fail "The disposable initramfs test requires root."

for path in \
  "$INSTALLED_RESET" \
  "$INSTALLED_UNIT" \
  "$INSTALLED_HOOK" \
  "$INSTALLED_CONFIG"; do
  [[ ! -e $path ]] || fail "The test will not overwrite an existing file: $path"
done

trap cleanup EXIT
install -d -m 0755 /usr/lib/cachy-freeze /etc/initcpio/install
install -m 0755 "$ROOT/initcpio/cachy-freeze-reset" "$INSTALLED_RESET"
install -m 0644 "$ROOT/initcpio/cachy-freeze-reset.service" "$INSTALLED_UNIT"
install -m 0644 "$ROOT/initcpio/install-hook" "$INSTALLED_HOOK"

cat >"$INSTALLED_CONFIG" <<EOF
ROOT_UUID=$(findmnt -n -o UUID /)
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
chmod 0600 "$INSTALLED_CONFIG"

for kernel in /usr/lib/modules/*; do
  [[ -d $kernel ]] || continue
  version=${kernel##*/}
  image="$TEST_DIR/initramfs-$version.img"

  printf 'Testing kernel initramfs: %s\n' "$version"
  mkinitcpio -n -k "$version" -g "$image" -A cachy-freeze

    listing="$TEST_DIR/initramfs-$version.list"
    lsinitcpio "$image" >"$listing"
    grep -qx 'usr/bin/findmnt' "$listing" ||
      fail "$version does not contain the mounted-subvolume guard."
    grep -qx 'usr/bin/grub-editenv' "$listing" ||
      fail "$version does not contain the protected THAWED fallback tool."
    grep -qx 'usr/lib/cachy-freeze/cachy-freeze-reset' "$listing" ||
    fail "$version does not contain the reset program."
  grep -qx 'etc/cachy-freeze-initrd.conf' "$listing" ||
    fail "$version does not contain the configuration."
  grep -qx 'usr/lib/systemd/system/cachy-freeze-reset.service' "$listing" ||
    fail "$version does not contain the systemd unit."
  grep -qx \
    'usr/lib/systemd/system/initrd-root-fs.target.requires/cachy-freeze-reset.service' \
    "$listing" ||
    fail "$version does not contain the initrd dependency link."
done

printf '%s\n' "Temporary initramfs tests passed for both kernels."
