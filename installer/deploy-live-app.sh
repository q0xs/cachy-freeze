#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly INSTALL_ROOT=/usr/lib/cachy-freeze

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

(( EUID == 0 )) || die "Live application deployment requires root privileges."
[[ $(findmnt -n -o SOURCE /) == *'[/@]' ]] ||
  die "Live application deployment is allowed only in THAWED maintenance mode."
[[ -d $INSTALL_ROOT/python/cachy_freeze ]] || die "CachyFreeze is not installed."

readonly stage=$(mktemp -d "$INSTALL_ROOT/app-update.XXXXXX")
cleanup() { rm -rf --one-file-system "$stage"; }
trap cleanup EXIT

cp -a "$PROJECT_ROOT/src/cachy_freeze" "$stage/cachy_freeze"
cp -a "$PROJECT_ROOT/app/cachy_freeze_gui" "$stage/cachy_freeze_gui"
find "$stage" -type d -name __pycache__ -prune -exec rm -rf --one-file-system {} +
python -m compileall -q "$stage/cachy_freeze" "$stage/cachy_freeze_gui"
chown -R root:root "$stage"

rm -rf --one-file-system "$INSTALL_ROOT/python/cachy_freeze.previous"
rm -rf --one-file-system "$INSTALL_ROOT/python/cachy_freeze_gui.previous"
mv "$INSTALL_ROOT/python/cachy_freeze" "$INSTALL_ROOT/python/cachy_freeze.previous"
mv "$INSTALL_ROOT/python/cachy_freeze_gui" "$INSTALL_ROOT/python/cachy_freeze_gui.previous"
mv "$stage/cachy_freeze" "$INSTALL_ROOT/python/cachy_freeze"
mv "$stage/cachy_freeze_gui" "$INSTALL_ROOT/python/cachy_freeze_gui"

install -m 0755 "$PROJECT_ROOT/app/cachy-freeze-manager-helper" \
  "$INSTALL_ROOT/cachy-freeze-manager-helper"
install -m 0755 "$PROJECT_ROOT/installer/prepare-standard-user.sh" \
  "$INSTALL_ROOT/deployment/installer/prepare-standard-user.sh"
install -m 0755 "$PROJECT_ROOT/user/files/company-microsip" \
  /usr/local/bin/company-microsip
install -m 0755 "$PROJECT_ROOT/user/files/cachyfreeze-finish-session" \
  /usr/local/bin/cachyfreeze-finish-session
install -m 0755 "$PROJECT_ROOT/user/files/cachy-frozen-admin-restrict" \
  /usr/local/sbin/cachy-frozen-admin-restrict
install -m 0644 "$PROJECT_ROOT/user/files/cachy-frozen-admin-restrict.service" \
  /usr/lib/systemd/system/cachy-frozen-admin-restrict.service
printf '%s\n' 'ADMIN_USER=localadm' >/etc/cachy-frozen-admin.conf
chmod 0600 /etc/cachy-frozen-admin.conf
systemctl daemon-reload
systemctl enable cachy-frozen-admin-restrict.service

cmp -s "$PROJECT_ROOT/src/cachy_freeze/users.py" \
  "$INSTALL_ROOT/python/cachy_freeze/users.py" || die "Backend verification failed."
cmp -s "$PROJECT_ROOT/app/cachy_freeze_gui/window.py" \
  "$INSTALL_ROOT/python/cachy_freeze_gui/window.py" || die "GUI verification failed."
cmp -s "$PROJECT_ROOT/app/cachy_freeze_gui/styles.py" \
  "$INSTALL_ROOT/python/cachy_freeze_gui/styles.py" || die "Style verification failed."

printf '%s\n' \
  "CachyFreeze application files were updated successfully." \
  "No boot, GRUB, initramfs, Btrfs, or reboot operation was performed."
