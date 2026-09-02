#!/usr/bin/env bash
set -Eeuo pipefail

export PATH=/usr/local/sbin:/usr/local/bin:/usr/bin:/usr/sbin
unset CDPATH ENV BASH_ENV PYTHONHOME PYTHONPATH

PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly PROJECT_ROOT
readonly DF_ROOT=$PROJECT_ROOT/deepfreeze

die() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

(( EUID == 0 )) || die "Administrator authorization is required."
[[ -r $DF_ROOT/bin/cachy-freeze && -r $PROJECT_ROOT/VERSION ]] ||
  die "The CachyFreeze installer payload is incomplete."
release_version=$(<"$PROJECT_ROOT/VERSION")
[[ $release_version =~ ^[0-9]+\.[0-9]+\.[0-9]+(rc[0-9]+)?$ ]] ||
  die "The release VERSION is invalid."
readonly release_version
command -v python >/dev/null || die "Python was not found."
python -c 'import PyQt6' 2>/dev/null || die "PyQt6 was not installed."
IFS= read -r boot_secret || die "The boot-maintenance password was not received."
(( ${#boot_secret} >= 12 && ${#boot_secret} <= 256 )) ||
  die "The boot-maintenance password must contain 12-256 characters."
[[ $boot_secret != *:* && $boot_secret != *$'\r'* && $boot_secret != *$'\n'* ]] ||
  die "The boot-maintenance password contains an unsupported character."

# Full compatibility validation occurs before any CachyFreeze-owned Btrfs or
# boot mutation. Installation and upgrade are allowed only from persistent @.
CACHY_FREEZE_CONFIG="$DF_ROOT/etc/cachy-freeze.conf" \
  bash "$DF_ROOT/bin/cachy-freeze" preflight >/dev/null
[[ $(findmnt -n -o SOURCE /) == *'[/@]' ]] ||
  die "Install or upgrade CachyFreeze only while booted in THAWED @."
[[ ,$(findmnt -n -o OPTIONS /), == *,rw,* ]] ||
  die "The THAWED root is read-only."
root_uuid=$(findmnt -n -o UUID /)
[[ $root_uuid =~ ^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$ ]] ||
  die "The root Btrfs UUID is missing or malformed."

# Existing deployments allowed configurable subvolume/state names. This
# simplified release cannot safely migrate a customized ownership boundary, so
# reject it before replacing the configuration or deleting any legacy object.
if [[ -f /etc/cachy-freeze.conf ]]; then
  python - /etc/cachy-freeze.conf <<'PY'
import sys
from pathlib import Path

expected = {
    "STATE_DIR": {"/var/lib/cachy-freeze"},
    "STATE_SUBVOL": {"@cachy-state"},
    "MAINTENANCE_SUBVOL": {"@"},
    "GOLDEN_SUBVOL": {"@golden"},
    "GOLDEN_PREVIOUS_SUBVOL": {"@golden.previous"},
    "GOLDEN_NEXT_SUBVOL": {"@golden.next"},
    "GOLDEN_PENDING_SUBVOL": {"@golden.previous.pending", "@golden.pending"},
    "FAILED_GOLDEN_SUBVOL": {"@golden.failed"},
    "ACTIVE_SUBVOL": {"@active"},
    "PREVIOUS_SUBVOL": {"@active.previous"},
    "NEXT_SUBVOL": {"@active.next"},
    "ACTIVE_NEXT_SUBVOL": {"@active.next"},
    "ACTIVE_PENDING_SUBVOL": {"@active.previous.pending", "@active.pending"},
    "CAPTURE_SUBVOL": {"@cachy-capture"},
    "SNAPSHOT_SUBVOL": {"@cachy-snapshots"},
    "LEGACY_SNAPSHOT_SUBVOL": {"@cachy-snapshots"},
}
seen = {}
for number, raw in enumerate(Path(sys.argv[1]).read_text(encoding="utf-8").splitlines(), 1):
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    if "=" not in line:
        raise SystemExit(f"ERROR: Existing CachyFreeze configuration is malformed at line {number}.")
    key, value = (part.strip() for part in line.split("=", 1))
    if key in seen:
        raise SystemExit(f"ERROR: Existing CachyFreeze configuration repeats {key}.")
    seen[key] = value
if seen.get("MAINTENANCE_SUBVOL") != "@":
    raise SystemExit("ERROR: Existing configuration ownership cannot be verified as CachyFreeze.")
for key, values in expected.items():
    if key in seen and seen[key] not in values:
        raise SystemExit(
            f"ERROR: Existing customized {key}={seen[key]!r} requires a reviewed manual migration; no state was changed."
        )
PY
fi

install -d -m 0700 /var/backups/cachy-freeze
backup_dir=$(mktemp -d /var/backups/cachy-freeze/install.XXXXXXXX)
readonly backup_dir
cp -a \
  /etc/mkinitcpio.conf \
  /etc/default/grub \
  /boot/grub/grub.cfg \
  /boot/grub/grubenv \
  "$backup_dir/"
state_mount=/var/lib/cachy-freeze
state_unit=$(systemd-escape --path --suffix=mount "$state_mount")
readonly state_unit
readonly -a owned_files=(
  /etc/cachy-freeze.conf
  /etc/cachy-freeze-initrd.conf
  /etc/cachy-freeze-grub-auth.conf
  /etc/initcpio/install/cachy-freeze
  /etc/grub.d/01_cachy_auth
  /etc/grub.d/09_cachy_recovery_begin
  /etc/grub.d/40_cachy_freeze
  /etc/grub.d/98_cachy_recovery_end
  /etc/grub.d/99_cachy_freeze
  "/etc/systemd/system/$state_unit"
  /usr/lib/systemd/system/cachy-freeze-reset.service
  /usr/lib/systemd/system/cachy-freeze-boot-health.service
  /usr/local/sbin/cachy-freeze
  /usr/bin/cachy-freeze-manager
  /usr/lib/cachy-freeze/VERSION
  /usr/lib/cachy-freeze/cachy-freeze-manager-helper
  /usr/lib/cachy-freeze/cachy-freeze-reset
  /usr/share/applications/cachy-freeze-manager.desktop
  /usr/share/icons/hicolor/512x512/apps/cachy-freeze.png
  /usr/share/polkit-1/actions/org.cachyos.cachy-freeze.policy
)
install -d -m 0700 "$backup_dir/owned"
for target in "${owned_files[@]}"; do
  if [[ -e $target || -L $target ]]; then
    install -d -m 0700 "$backup_dir/owned$(dirname "$target")"
    cp -a -- "$target" "$backup_dir/owned$target"
  else
    : >"$backup_dir/owned.missing.${target//\//_}"
  fi
done
state_unit_was_enabled=$(systemctl is-enabled "$state_unit" 2>/dev/null || true)
boot_health_was_enabled=$(systemctl is-enabled cachy-freeze-boot-health.service 2>/dev/null || true)

rollback_boot_configuration() {
  local rc=$?
  trap - ERR
  set +e
  cp -a "$backup_dir/mkinitcpio.conf" /etc/mkinitcpio.conf
  cp -a "$backup_dir/grub" /etc/default/grub
  cp -a "$backup_dir/grub.cfg" /boot/grub/grub.cfg
  cp -a "$backup_dir/grubenv" /boot/grub/grubenv
  for target in "${owned_files[@]}"; do
    rm -f -- "$target"
    if [[ -e $backup_dir/owned$target || -L $backup_dir/owned$target ]]; then
      install -d "$(dirname "$target")"
      cp -a -- "$backup_dir/owned$target" "$target"
    fi
  done
  if [[ ${python_swapped:-0} == 1 ]]; then
    rm -rf --one-file-system "${python_root:-/usr/lib/cachy-freeze/python}"
  fi
  if [[ -n ${python_previous:-} && -d $python_previous ]]; then
    mv "$python_previous" "${python_root:-/usr/lib/cachy-freeze/python}"
  fi
  if [[ ${deployment_swapped:-0} == 1 ]]; then
    rm -rf --one-file-system "${deployment:-/usr/lib/cachy-freeze/deployment}"
  fi
  if [[ -n ${deployment_previous:-} && -d $deployment_previous ]]; then
    mv "$deployment_previous" "${deployment:-/usr/lib/cachy-freeze/deployment}"
  fi
  if [[ $state_unit_was_enabled != enabled ]]; then
    systemctl disable --now "$state_unit" 2>/dev/null || true
  fi
  if [[ $boot_health_was_enabled != enabled ]]; then
    systemctl disable cachy-freeze-boot-health.service 2>/dev/null || true
  fi
  systemctl daemon-reload
  if mkinitcpio -P; then
    printf 'ERROR: Owned files, GRUB configuration, and initramfs were restored from %s. No reboot was requested.\n' \
      "$backup_dir" >&2
  else
    printf 'CRITICAL: Owned files and GRUB configuration were restored from %s, but initramfs restoration failed. Do not reboot; use the retained backup and recovery media.\n' \
      "$backup_dir" >&2
  fi
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
python_root=/usr/lib/cachy-freeze/python
python_next=/usr/lib/cachy-freeze/python.next
python_previous=/usr/lib/cachy-freeze/python.previous
rm -rf --one-file-system "$python_next"
install -d -m 0755 "$python_next"
cp -a "$PROJECT_ROOT/src/cachy_freeze" "$python_next/"
cp -a "$PROJECT_ROOT/app/cachy_freeze_gui" "$python_next/"
find "$python_next" -type d -name __pycache__ \
  -prune -exec rm -rf --one-file-system {} +
chown -R root:root "$python_next"
rm -rf --one-file-system "$python_previous"
if [[ -d $python_root ]]; then
  mv "$python_root" "$python_previous"
fi
mv "$python_next" "$python_root"
python_swapped=1

deployment=/usr/lib/cachy-freeze/deployment
deployment_next=/usr/lib/cachy-freeze/deployment.next
deployment_previous=/usr/lib/cachy-freeze/deployment.previous
rm -rf --one-file-system "$deployment_next"
install -d -m 0755 "$deployment_next"
cp -a "$PROJECT_ROOT/installer" "$deployment_next/"
cp -a "$PROJECT_ROOT/deepfreeze" "$deployment_next/"
cp -a "$PROJECT_ROOT/workstation" "$deployment_next/"
cp -a "$PROJECT_ROOT/LICENSE" "$deployment_next/"
cp -a "$PROJECT_ROOT/NOTICE" "$deployment_next/"
chown -R root:root "$deployment_next"
rm -rf --one-file-system "$deployment_previous"
if [[ -d $deployment ]]; then
  mv "$deployment" "$deployment_previous"
fi
mv "$deployment_next" "$deployment"
deployment_swapped=1

install -m 0755 "$PROJECT_ROOT/app/cachy-freeze-manager" /usr/bin/cachy-freeze-manager
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
install -m 0644 "$DF_ROOT/initcpio/install-hook" /etc/initcpio/install/cachy-freeze
install -m 0755 "$DF_ROOT/grub/01_cachy_auth" /etc/grub.d/01_cachy_auth
install -m 0755 \
  "$DF_ROOT/grub/09_cachy_recovery_begin" \
  /etc/grub.d/09_cachy_recovery_begin
install -m 0755 \
  "$DF_ROOT/grub/98_cachy_recovery_end" \
  /etc/grub.d/98_cachy_recovery_end
install -m 0755 "$DF_ROOT/grub/99_cachy_freeze" /etc/grub.d/99_cachy_freeze
# 40_cachy_freeze was owned by CachyFreeze through rc5. The managed entry now
# runs last so every preserved vendor/recovery entry can stay inside the
# explicit recovery gate while the normal menu exposes exactly one mode.
rm -f /etc/grub.d/40_cachy_freeze

sed "s/^ROOT_UUID=.*/ROOT_UUID=$root_uuid/" \
  "$DF_ROOT/etc/cachy-freeze.conf" >/etc/cachy-freeze.conf
chmod 0600 /etc/cachy-freeze.conf

# Keep only minimal operational metadata in a dedicated persistent subvolume.
state_stage=/run/cachy-freeze/state-install
top_stage=/run/cachy-freeze/install-btrfs
install -d -m 0700 "$state_mount" "$state_stage" "$top_stage"
cleanup_state_install() {
  mountpoint -q "$state_stage" && umount "$state_stage" || true
  mountpoint -q "$top_stage" && umount "$top_stage" || true
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
  "$DF_ROOT/systemd/cachy-freeze-state.mount.in" >"/etc/systemd/system/$state_unit"
chmod 0644 "/etc/systemd/system/$state_unit"

cat >/etc/cachy-freeze-initrd.conf <<EOF
ROOT_UUID=$root_uuid
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
chmod 0600 /etc/cachy-freeze-initrd.conf

systemctl daemon-reload
systemctl enable --now "$state_unit"
systemctl enable cachy-freeze-boot-health.service
mountpoint -q "$state_mount" || die "Persistent CachyFreeze state could not be mounted."

if ! grep -Eq '^HOOKS=.*\bcachy-freeze\b' /etc/mkinitcpio.conf; then
  sed -i -E \
    '/^HOOKS=/s/(^|[[:space:]])filesystems([[:space:]]|\))/\1cachy-freeze filesystems\2/' \
    /etc/mkinitcpio.conf
fi
grep -Eq '^HOOKS=.*\bsystemd\b.*\bcachy-freeze\b.*\bfilesystems\b' \
  /etc/mkinitcpio.conf || die "mkinitcpio HOOKS could not be updated safely."

set_grub_setting() {
  local key=$1 value=$2 count
  count=$(grep -c "^${key}=" /etc/default/grub || true)
  if (( count > 1 )); then
    printf 'ERROR: The GRUB setting %s is duplicated.\n' "$key" >&2
    return 1
  fi
  if (( count == 1 )); then
    sed -i -E "s|^${key}=.*|${key}=${value}|" /etc/default/grub
  else
    printf '%s=%s\n' "$key" "$value" >>/etc/default/grub
  fi
  if [[ $(grep -c "^${key}=" /etc/default/grub) -ne 1 ]]; then
    printf 'ERROR: The GRUB setting %s could not be written exactly once.\n' "$key" >&2
    return 1
  fi
}

# The managed entry has a stable ID and selects FROZEN or THAWED from grubenv.
# Make that ID the direct default: relying on the saved-entry setting allowed the
# first stock CachyOS entry to boot on systems where saved_entry was ignored.
# Keep the mode menu visible long enough to identify FROZEN or THAWED. Unrelated
# entries remain generated inside the explicit cachy_recovery gate and do not
# appear in the normal appliance menu.
set_grub_setting GRUB_DEFAULT cachyos-current
set_grub_setting GRUB_SAVEDEFAULT false
set_grub_setting GRUB_TIMEOUT_STYLE menu
set_grub_setting GRUB_TIMEOUT 5

# Preserve every unrelated generator and boot entry under the recovery gate.
# Only CachyFreeze-owned generators are installed, replaced, or removed.
mkinitcpio -P
printf '%s\n' "$boot_secret" |
  CACHY_SETUP_NONINTERACTIVE=1 bash "$PROJECT_ROOT/installer/configure-grub-password.sh"
unset boot_secret
[[ $(grep -c -- "--id 'cachyos-current'" /boot/grub/grub.cfg) -eq 1 ]] ||
  die "Exactly one managed CachyFreeze GRUB entry is required."
grep -Fq 'set default="cachyos-current"' /boot/grub/grub.cfg ||
  die "The managed CachyFreeze GRUB entry is not the direct default."
grub-editenv /boot/grub/grubenv set \
  cachy_mode=thawed \
  saved_entry=cachyos-current \
  cachy_recovery=0
grub-editenv /boot/grub/grubenv list | grep -qx 'cachy_mode=thawed' ||
  die "The safe initial THAWED boot mode could not be verified."
grub-editenv /boot/grub/grubenv list | grep -qx 'cachy_recovery=0' ||
  die "The normal single-entry GRUB menu could not be verified."
for image in /boot/initramfs-linux-cachyos.img /boot/initramfs-linux-cachyos-lts.img; do
  [[ -r $image ]] || continue
  image_listing=$(lsinitcpio "$image")
  for required in \
    usr/bin/findmnt \
    usr/bin/grub-editenv \
    usr/lib/cachy-freeze/cachy-freeze-reset \
    usr/lib/systemd/system/cachy-freeze-reset.service \
    usr/lib/systemd/system/initrd-root-fs.target.requires/cachy-freeze-reset.service; do
    grep -qx "$required" <<<"$image_listing" ||
      die "Required FROZEN reset payload is missing from $image: $required"
  done
done

[[ -x /usr/bin/cachy-freeze-manager ]] || die "The desktop application was not installed."
[[ -x /usr/lib/cachy-freeze/cachy-freeze-manager-helper ]] ||
  die "The privileged helper was not installed."
[[ -r /usr/share/applications/cachy-freeze-manager.desktop ]] ||
  die "The KDE application entry was not installed."
[[ -x /usr/lib/cachy-freeze/deployment/workstation/bin/workstation-setup ]] ||
  die "The CachyWorkstation payload was not installed."
cmp -s "$PROJECT_ROOT/VERSION" /usr/lib/cachy-freeze/VERSION ||
  die "The installed version does not match the payload."

# Everything required for a bootable THAWED installation has passed. Legacy
# history deletion is intentionally the commit boundary because deleted Btrfs
# snapshots cannot be recreated by a file rollback. On migration failure, keep
# the new, bootable core and durable migration record so a rerun can reconcile
# safely instead of restoring an engine that cannot understand partial state.
trap - ERR
if ! /usr/local/sbin/cachy-freeze migrate >/dev/null; then
  printf 'ERROR: Core installation is bootable in THAWED mode, but legacy state migration did not complete. Retry the installer; recovery files remain in %s.\n' \
    "$backup_dir" >&2
  exit 1
fi

# All fallible Btrfs/initramfs/GRUB checks have completed. Retire only paths
# with established ownership in prior CachyFreeze releases; unrelated services
# and boot generators are never touched.
for unit in \
  cachy-freeze-auto-snapshot.timer \
  cachy-freeze-auto-snapshot.service \
  cachy-freeze-idle-power.service \
  cachy-freeze-finalize.service \
  cachy-employee-reset.service \
  cachy-frozen-admin-restrict.service; do
  systemctl disable --now "$unit" 2>/dev/null || true
  rm -f "/etc/systemd/system/$unit" "/usr/lib/systemd/system/$unit"
done
rm -f \
  /usr/local/sbin/cachy-employee-reset \
  /usr/local/sbin/cachy-frozen-admin-restrict \
  /usr/local/bin/company-microsip \
  /usr/local/bin/cachyfreeze-finish-session
systemctl daemon-reload
rm -rf --one-file-system "$python_previous" "$deployment_previous"
rm -rf --one-file-system "$backup_dir"

printf 'CachyFreeze %s core installation verified.\n' "$release_version"
