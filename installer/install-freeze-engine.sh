#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly PROJECT_ROOT
readonly DF_ROOT=$PROJECT_ROOT/deepfreeze

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

(( EUID == 0 )) || die "Run as root: sudo $0"
[[ -r $DF_ROOT/bin/cachy-freeze ]] || die "CachyFreeze repository files are missing."
[[ -r $PROJECT_ROOT/VERSION ]] || die "The release VERSION file is missing."
release_version=$(<"$PROJECT_ROOT/VERSION")
[[ $release_version =~ ^[0-9]+\.[0-9]+\.[0-9]+(rc[0-9]+)?$ ]] ||
  die "The release VERSION is invalid."
readonly release_version
command -v python >/dev/null || die "Python was not found."
python -c 'import PyQt6' 2>/dev/null ||
  die "PyQt6 was not found. Install python-pyqt6 first."

CACHY_FREEZE_CONFIG="$DF_ROOT/etc/cachy-freeze.conf" \
  bash "$DF_ROOT/bin/cachy-freeze" preflight

root_uuid=$(findmnt -n -o UUID /)
[[ -n $root_uuid ]] || die "The root Btrfs UUID could not be detected."
[[ $(findmnt -n -o SOURCE /) == *'[/@]' ]] ||
  die "Installation is allowed only on the maintenance @ root."
root_options=$(findmnt -n -o OPTIONS /)
[[ ,$root_options, == *,rw,* ]] ||
  die "The maintenance @ root is read-only; CachyFreeze cannot be installed."

backup_dir="/var/backups/cachy-freeze/$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 0700 "$backup_dir"
cp -a /etc/mkinitcpio.conf /etc/default/grub /boot/grub/grub.cfg "$backup_dir/"
cp -a /etc/grub.d "$backup_dir/"

rollback_boot_configuration() {
  rc=$?
  trap - ERR
  set +e
  cp -a "$backup_dir/mkinitcpio.conf" /etc/mkinitcpio.conf
  cp -a "$backup_dir/grub" /etc/default/grub
  cp -a "$backup_dir/grub.cfg" /boot/grub/grub.cfg
  cp -a "$backup_dir/grub.d/." /etc/grub.d/
  systemctl daemon-reload
  printf 'ERROR: Boot configuration was restored from %s.\n' "$backup_dir" >&2
  exit "$rc"
}
trap rollback_boot_configuration ERR

install -d -m 0755 \
  /usr/lib/cachy-freeze \
  /etc/initcpio/install \
  /etc/grub.d \
  /etc/systemd/system \
  /usr/local/sbin \
  /usr/share/applications \
  /usr/share/icons/hicolor/512x512/apps \
  /usr/share/polkit-1/actions
install -m 0755 "$DF_ROOT/bin/cachy-freeze" /usr/local/sbin/cachy-freeze
install -m 0644 "$PROJECT_ROOT/VERSION" /usr/lib/cachy-freeze/VERSION
install -d -m 0755 /usr/lib/cachy-freeze/python
cp -a "$PROJECT_ROOT/src/cachy_freeze" /usr/lib/cachy-freeze/python/
cp -a "$PROJECT_ROOT/app/cachy_freeze_gui" /usr/lib/cachy-freeze/python/
find /usr/lib/cachy-freeze/python/cachy_freeze -type d -name __pycache__ \
  -prune -exec rm -rf --one-file-system {} +
chown -R root:root /usr/lib/cachy-freeze/python

deployment=/usr/lib/cachy-freeze/deployment
deployment_next=/usr/lib/cachy-freeze/deployment.next
deployment_previous=/usr/lib/cachy-freeze/deployment.previous
rm -rf --one-file-system "$deployment_next"
install -d -m 0755 "$deployment_next"
cp -a "$PROJECT_ROOT/installer" "$deployment_next/"
cp -a "$PROJECT_ROOT/policies" "$deployment_next/"
cp -a "$PROJECT_ROOT/vendor" "$deployment_next/"
cp -a "$PROJECT_ROOT/deepfreeze" "$deployment_next/"
cp -a "$PROJECT_ROOT/user" "$deployment_next/"
chown -R root:root "$deployment_next"
rm -rf --one-file-system "$deployment_previous"
if [[ -d $deployment ]]; then
  mv "$deployment" "$deployment_previous"
fi
mv "$deployment_next" "$deployment"
install -m 0755 \
  "$PROJECT_ROOT/app/cachy-freeze-manager" \
  /usr/bin/cachy-freeze-manager
install -m 0755 \
  "$PROJECT_ROOT/app/cachy-freeze-manager-helper" \
  /usr/lib/cachy-freeze/cachy-freeze-manager-helper
install -m 0644 \
  "$PROJECT_ROOT/app/cachy-freeze-manager.desktop" \
  /usr/share/applications/cachy-freeze-manager.desktop
install -m 0644 \
  "$PROJECT_ROOT/app/cachy_freeze_gui/assets/cachy-freeze.png" \
  /usr/share/icons/hicolor/512x512/apps/cachy-freeze.png
install -m 0644 \
  "$PROJECT_ROOT/app/org.cachyos.cachy-freeze.policy" \
  /usr/share/polkit-1/actions/org.cachyos.cachy-freeze.policy
install -m 0755 \
  "$DF_ROOT/initcpio/cachy-freeze-reset" \
  /usr/lib/cachy-freeze/cachy-freeze-reset
install -m 0644 \
  "$DF_ROOT/initcpio/cachy-freeze-reset.service" \
  /usr/lib/systemd/system/cachy-freeze-reset.service
install -m 0644 \
  "$DF_ROOT/systemd/cachy-freeze-boot-health.service" \
  /usr/lib/systemd/system/cachy-freeze-boot-health.service
install -m 0644 \
  "$DF_ROOT/systemd/cachy-freeze-auto-snapshot.service" \
  /usr/lib/systemd/system/cachy-freeze-auto-snapshot.service
install -m 0644 \
  "$DF_ROOT/systemd/cachy-freeze-auto-snapshot.timer" \
  /usr/lib/systemd/system/cachy-freeze-auto-snapshot.timer
install -m 0644 \
  "$DF_ROOT/systemd/cachy-freeze-finalize.service" \
  /usr/lib/systemd/system/cachy-freeze-finalize.service
install -m 0644 \
  "$DF_ROOT/systemd/cachy-freeze-idle-power.service" \
  /usr/lib/systemd/system/cachy-freeze-idle-power.service
install -m 0755 \
  "$PROJECT_ROOT/user/files/cachy-employee-reset" \
  /usr/local/sbin/cachy-employee-reset
install -m 0644 \
  "$PROJECT_ROOT/user/files/cachy-employee-reset.service" \
  /usr/lib/systemd/system/cachy-employee-reset.service
install -m 0755 \
  "$PROJECT_ROOT/user/files/cachy-frozen-admin-restrict" \
  /usr/local/sbin/cachy-frozen-admin-restrict
install -m 0644 \
  "$PROJECT_ROOT/user/files/cachy-frozen-admin-restrict.service" \
  /usr/lib/systemd/system/cachy-frozen-admin-restrict.service
install -m 0755 \
  "$PROJECT_ROOT/user/files/company-microsip" \
  /usr/local/bin/company-microsip
install -m 0755 \
  "$PROJECT_ROOT/user/files/cachyfreeze-finish-session" \
  /usr/local/bin/cachyfreeze-finish-session
printf '%s\n' 'ADMIN_USER=localadm' >/etc/cachy-frozen-admin.conf
chmod 0600 /etc/cachy-frozen-admin.conf
install -d -m 0700 /var/lib/cachy-user-template
install -m 0644 "$DF_ROOT/initcpio/install-hook" /etc/initcpio/install/cachy-freeze
install -m 0755 "$DF_ROOT/grub/40_cachy_freeze" /etc/grub.d/40_cachy_freeze
install -m 0755 "$DF_ROOT/grub/01_cachy_auth" /etc/grub.d/01_cachy_auth

sed "s/^ROOT_UUID=.*/ROOT_UUID=$root_uuid/" \
  "$DF_ROOT/etc/cachy-freeze.conf" >/etc/cachy-freeze.conf
chmod 0600 /etc/cachy-freeze.conf

# Metadata and transaction journals must survive both Golden rollback and
# Frozen root recreation. Keep them in a dedicated top-level Btrfs subvolume.
state_mount=/var/lib/cachy-freeze
state_stage=/run/cachy-freeze/state-install
state_unit=$(systemd-escape --path --suffix=mount "$state_mount")
top_stage=/run/cachy-freeze/install-btrfs
install -d -m 0700 "$state_mount" "$state_stage" "$top_stage"

cleanup_state_install() {
  if mountpoint -q "$state_stage"; then
    umount "$state_stage" || true
  fi
  if mountpoint -q "$top_stage"; then
    umount "$top_stage" || true
  fi
}
trap cleanup_state_install EXIT

mount -o subvolid=5 "$(findmnt -n -o SOURCE / | sed 's/\[.*$//')" "$top_stage"
if ! btrfs subvolume show "$top_stage/@cachy-state" >/dev/null 2>&1; then
  btrfs subvolume create "$top_stage/@cachy-state"
fi
umount "$top_stage"

mount -o subvol=@cachy-state "/dev/disk/by-uuid/$root_uuid" "$state_stage"
chmod 0755 "$state_stage"
if ! mountpoint -q "$state_mount" &&
  find "$state_mount" -mindepth 1 -print -quit | grep -q .; then
  rsync -aHAX "$state_mount/" "$state_stage/"
fi
umount "$state_stage"
trap - EXIT

sed "s/__ROOT_UUID__/$root_uuid/g" \
  "$DF_ROOT/systemd/cachy-freeze-state.mount.in" \
  >"/etc/systemd/system/$state_unit"
chmod 0644 "/etc/systemd/system/$state_unit"

cat >/etc/cachy-freeze-initrd.conf <<EOF
ROOT_UUID=$root_uuid
MAINTENANCE_SUBVOL=@
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
chmod 0600 /etc/cachy-freeze-initrd.conf

systemctl daemon-reload
systemctl enable --now "$state_unit"
systemctl enable cachy-freeze-boot-health.service
systemctl enable --now cachy-freeze-auto-snapshot.timer
systemctl enable cachy-employee-reset.service
systemctl enable cachy-frozen-admin-restrict.service
systemctl enable cachy-freeze-idle-power.service
mountpoint -q "$state_mount" || die "The persistent CachyFreeze state could not be mounted."
/usr/local/sbin/cachy-freeze migrate
systemctl is-enabled --quiet cachy-freeze-boot-health.service ||
  die "The boot-health service could not be enabled."
systemctl is-enabled --quiet cachy-freeze-auto-snapshot.timer ||
  die "The automatic snapshot timer could not be enabled."
systemctl is-enabled --quiet cachy-employee-reset.service ||
  die "The managed-user reset service could not be enabled."
systemctl is-enabled --quiet cachy-frozen-admin-restrict.service ||
  die "The FROZEN administrator restriction service could not be enabled."
systemctl is-enabled --quiet cachy-freeze-idle-power.service ||
  die "The idle sleep and shutdown policy could not be enabled."

if ! grep -Eq '^HOOKS=.*\bcachy-freeze\b' /etc/mkinitcpio.conf; then
  sed -i -E \
    '/^HOOKS=/s/(^|[[:space:]])filesystems([[:space:]]|\))/\1cachy-freeze filesystems\2/' \
    /etc/mkinitcpio.conf
fi
grep -Eq '^HOOKS=.*\bsystemd\b.*\bcachy-freeze\b.*\bfilesystems\b' \
  /etc/mkinitcpio.conf ||
  die "mkinitcpio HOOKS could not be updated safely."

sed -i -E "s/^GRUB_DEFAULT=.*/GRUB_DEFAULT=saved/" /etc/default/grub
if grep -q '^GRUB_DISABLE_OS_PROBER=' /etc/default/grub; then
  sed -i -E "s/^GRUB_DISABLE_OS_PROBER=.*/GRUB_DISABLE_OS_PROBER=true/" \
    /etc/default/grub
else
  printf '%s\n' 'GRUB_DISABLE_OS_PROBER=true' >>/etc/default/grub
fi
if grep -q '^GRUB_SAVEDEFAULT=' /etc/default/grub; then
  sed -i -E "s/^GRUB_SAVEDEFAULT=.*/GRUB_SAVEDEFAULT=false/" /etc/default/grub
else
  printf '%s\n' 'GRUB_SAVEDEFAULT=false' >>/etc/default/grub
fi

# Show only the managed entry. Other generators are retained in the backup but
# have their execute permission disabled.
for generator in /etc/grub.d/*; do
  [[ -f $generator ]] || continue
  case ${generator##*/} in
    00_header | 01_cachy_auth | 05_debian_theme | 40_cachy_freeze)
      chmod a+x "$generator"
      ;;
    *)
      chmod a-x "$generator"
      ;;
  esac
done

mkinitcpio -P
grub-mkconfig -o /boot/grub/grub.cfg

for image in /boot/initramfs-linux-cachyos.img /boot/initramfs-linux-cachyos-lts.img; do
  [[ -r $image ]] || continue
  lsinitcpio "$image" | grep -qx 'usr/lib/cachy-freeze/cachy-freeze-reset' ||
    die "The reset program is missing from initramfs: $image"
done
grep -q -- "--id 'cachyos-current'" /boot/grub/grub.cfg ||
  die "The managed GRUB entry is missing: cachyos-current"
[[ $(grep -c '^menuentry ' /boot/grub/grub.cfg) -eq 1 ]] ||
  die "The GRUB menu contains more than one entry."
[[ -x /usr/bin/cachy-freeze-manager ]] ||
  die "The CachyFreeze desktop application was not installed."
[[ -x /usr/lib/cachy-freeze/cachy-freeze-manager-helper ]] ||
  die "The CachyFreeze privileged helper was not installed."
[[ -r /usr/share/applications/cachy-freeze-manager.desktop ]] ||
    die "The CachyFreeze application-menu entry was not installed."
[[ -r /usr/lib/cachy-freeze/python/cachy_freeze/cli.py ]] ||
  die "The CachyFreeze Python backend was not installed."
cmp -s "$PROJECT_ROOT/VERSION" /usr/lib/cachy-freeze/VERSION ||
  die "The CachyFreeze release version was not installed correctly."

/usr/local/sbin/cachy-freeze thaw
bash "$PROJECT_ROOT/installer/migrate-display-manager-autologin.sh"

# CachyFreeze deliberately disables third-party GRUB entry generators. The
# grub-btrfs snapshot watcher otherwise keeps executing its now non-executable
# generator and produces a recurring failed systemd unit on every Snapper
# change. Stop both supported grub-btrfs regeneration mechanisms and clear the
# stale failure after the managed GRUB configuration has been verified.
for conflicting_unit in grub-btrfs-snapper.path grub-btrfsd.service; do
  if systemctl list-unit-files "$conflicting_unit" --no-legend 2>/dev/null |
    grep -q "^${conflicting_unit}[[:space:]]"; then
    systemctl disable --now "$conflicting_unit"
  fi
done
systemctl reset-failed grub-btrfs-snapper.service grub-btrfsd.service 2>/dev/null || true

trap - ERR

printf '%s\n' \
  "CachyFreeze $release_version was installed and verified." \
  "Safe default: THAWED maintenance mode." \
  "Golden has not been published by this internal step." \
  "Use the public installer or management app to complete setup."
