#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly PROJECT_ROOT
readonly INSTALL_ROOT=/usr/lib/cachy-freeze

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

(( EUID == 0 )) || die "Live application deployment requires root privileges."
[[ $(findmnt -n -o SOURCE /) == *'[/@]' ]] ||
  die "Live application deployment is allowed only in THAWED maintenance mode."
[[ -d $INSTALL_ROOT/python/cachy_freeze ]] || die "CachyFreeze is not installed."
[[ -d $INSTALL_ROOT/deployment ]] || die "CachyFreeze deployment files are missing."
[[ -r $PROJECT_ROOT/VERSION ]] || die "The release VERSION file is missing."
release_version=$(<"$PROJECT_ROOT/VERSION")
[[ $release_version =~ ^[0-9]+\.[0-9]+\.[0-9]+(rc[0-9]+)?$ ]] ||
  die "The release VERSION is invalid."
readonly release_version

stage=$(mktemp -d "$INSTALL_ROOT/app-update.XXXXXX")
readonly stage
cleanup() { rm -rf --one-file-system "$stage"; }
trap cleanup EXIT

cp -a "$PROJECT_ROOT/src/cachy_freeze" "$stage/cachy_freeze"
cp -a "$PROJECT_ROOT/app/cachy_freeze_gui" "$stage/cachy_freeze_gui"
install -d -m 0755 "$stage/deployment"
for tree in installer policies vendor deepfreeze user; do
  cp -a "$PROJECT_ROOT/$tree" "$stage/deployment/"
done
install -m 0644 "$PROJECT_ROOT/VERSION" "$stage/VERSION"
find "$stage" -type d -name __pycache__ -prune -exec rm -rf --one-file-system {} +
python -m compileall -q "$stage/cachy_freeze" "$stage/cachy_freeze_gui"
chown -R root:root "$stage"

backup_dir="/var/backups/cachy-freeze/app/$(date -u +%Y%m%dT%H%M%SZ)-$release_version"
if [[ -e $backup_dir ]]; then
  backup_dir="${backup_dir}-$$"
fi
readonly backup_dir
install -d -m 0700 "$backup_dir/root"

idle_power_was_enabled=false
idle_power_was_active=false
systemctl is-enabled --quiet cachy-freeze-idle-power.service 2>/dev/null &&
  idle_power_was_enabled=true
systemctl is-active --quiet cachy-freeze-idle-power.service 2>/dev/null &&
  idle_power_was_active=true
readonly idle_power_was_enabled idle_power_was_active

readonly -a managed_paths=(
  "$INSTALL_ROOT/python/cachy_freeze"
  "$INSTALL_ROOT/python/cachy_freeze_gui"
  "$INSTALL_ROOT/deployment"
  "$INSTALL_ROOT/cachy-freeze-manager-helper"
  "$INSTALL_ROOT/VERSION"
  /usr/local/sbin/cachy-freeze
  /usr/bin/cachy-freeze-manager
  /usr/share/applications/cachy-freeze-manager.desktop
  /usr/share/polkit-1/actions/org.cachyos.cachy-freeze.policy
  /usr/share/icons/hicolor/512x512/apps/cachy-freeze.png
  /usr/local/bin/company-microsip
  /usr/local/bin/cachyfreeze-finish-session
  /usr/local/sbin/cachy-frozen-admin-restrict
  /usr/lib/systemd/system/cachy-frozen-admin-restrict.service
  /usr/lib/systemd/system/cachy-freeze-finalize.service
  /usr/lib/systemd/system/cachy-freeze-idle-power.service
  /etc/cachy-frozen-admin.conf
  /etc/plasmalogin.conf.d/90-cachy-freeze-autologin.conf
  /etc/sddm.conf.d/cachy-autologin.conf
  /var/lib/cachy-freeze/schema-version.json
)

for target in "${managed_paths[@]}"; do
  if [[ -e $target || -L $target ]]; then
    relative=${target#/}
    install -d -m 0700 "$backup_dir/root/${relative%/*}"
    cp -a -- "$target" "$backup_dir/root/$relative"
  fi
done
if [[ -d /var/lib/cachy-freeze ]]; then
  install -d -m 0700 "$backup_dir/state"
  find /var/lib/cachy-freeze -maxdepth 1 -type f -exec cp -a -t "$backup_dir/state" -- {} +
fi
printf '%s\n' "$release_version" >"$backup_dir/target-version"
chmod 0600 "$backup_dir/target-version"

rollback_app_update() {
  rc=$?
  trap - ERR
  set +e
  systemctl disable --now cachy-freeze-idle-power.service >/dev/null 2>&1
  for target in "${managed_paths[@]}"; do
    case $target in
      "$INSTALL_ROOT"/* | /usr/local/sbin/* | /usr/local/bin/* | \
        /usr/bin/cachy-freeze-manager | \
        /usr/share/applications/cachy-freeze-manager.desktop | \
        /usr/share/polkit-1/actions/org.cachyos.cachy-freeze.policy | \
        /usr/share/icons/hicolor/512x512/apps/cachy-freeze.png | \
        /usr/lib/systemd/system/cachy-freeze-*.service | \
        /etc/cachy-frozen-admin.conf | \
        /etc/plasmalogin.conf.d/90-cachy-freeze-autologin.conf | \
        /etc/sddm.conf.d/cachy-autologin.conf | \
        /var/lib/cachy-freeze/schema-version.json) ;;
      *)
        printf 'ERROR: Refusing unsafe rollback target: %s\n' "$target" >&2
        continue
        ;;
    esac
    rm -rf --one-file-system -- "$target"
    relative=${target#/}
    if [[ -e $backup_dir/root/$relative || -L $backup_dir/root/$relative ]]; then
      install -d -m 0755 "${target%/*}"
      cp -a -- "$backup_dir/root/$relative" "$target"
    fi
  done
  if [[ -d $backup_dir/state ]]; then
    find "$backup_dir/state" -maxdepth 1 -type f -exec cp -a -t /var/lib/cachy-freeze -- {} +
  fi
  systemctl daemon-reload
  if [[ $idle_power_was_enabled == true ]]; then
    systemctl enable cachy-freeze-idle-power.service >/dev/null 2>&1
  fi
  if [[ $idle_power_was_active == true ]]; then
    systemctl start cachy-freeze-idle-power.service >/dev/null 2>&1
  fi
  printf 'ERROR: Application update failed and was restored from %s.\n' "$backup_dir" >&2
  exit "$rc"
}
trap rollback_app_update ERR

rm -rf --one-file-system "$INSTALL_ROOT/python/cachy_freeze.previous"
rm -rf --one-file-system "$INSTALL_ROOT/python/cachy_freeze_gui.previous"
mv "$INSTALL_ROOT/python/cachy_freeze" "$INSTALL_ROOT/python/cachy_freeze.previous"
mv "$INSTALL_ROOT/python/cachy_freeze_gui" "$INSTALL_ROOT/python/cachy_freeze_gui.previous"
mv "$stage/cachy_freeze" "$INSTALL_ROOT/python/cachy_freeze"
mv "$stage/cachy_freeze_gui" "$INSTALL_ROOT/python/cachy_freeze_gui"
rm -rf --one-file-system "$INSTALL_ROOT/deployment.previous"
mv "$INSTALL_ROOT/deployment" "$INSTALL_ROOT/deployment.previous"
mv "$stage/deployment" "$INSTALL_ROOT/deployment"
install -m 0644 "$stage/VERSION" "$INSTALL_ROOT/VERSION"

install -m 0755 "$PROJECT_ROOT/deepfreeze/bin/cachy-freeze" \
  /usr/local/sbin/cachy-freeze
install -m 0755 "$PROJECT_ROOT/app/cachy-freeze-manager" \
  /usr/bin/cachy-freeze-manager
install -m 0755 "$PROJECT_ROOT/app/cachy-freeze-manager-helper" \
  "$INSTALL_ROOT/cachy-freeze-manager-helper"
install -d -m 0755 /usr/share/icons/hicolor/512x512/apps
install -m 0644 "$PROJECT_ROOT/app/cachy-freeze-manager.desktop" \
  /usr/share/applications/cachy-freeze-manager.desktop
install -m 0644 "$PROJECT_ROOT/app/org.cachyos.cachy-freeze.policy" \
  /usr/share/polkit-1/actions/org.cachyos.cachy-freeze.policy
install -m 0644 \
  "$PROJECT_ROOT/deepfreeze/systemd/cachy-freeze-finalize.service" \
  /usr/lib/systemd/system/cachy-freeze-finalize.service
install -m 0644 \
  "$PROJECT_ROOT/deepfreeze/systemd/cachy-freeze-idle-power.service" \
  /usr/lib/systemd/system/cachy-freeze-idle-power.service
install -m 0644 "$PROJECT_ROOT/app/cachy_freeze_gui/assets/cachy-freeze.png" \
  /usr/share/icons/hicolor/512x512/apps/cachy-freeze.png
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
systemctl enable --now cachy-freeze-idle-power.service
bash "$PROJECT_ROOT/installer/migrate-display-manager-autologin.sh"
/usr/local/sbin/cachy-freeze migrate

cmp -s "$PROJECT_ROOT/src/cachy_freeze/users.py" \
  "$INSTALL_ROOT/python/cachy_freeze/users.py" || die "Backend verification failed."
cmp -s "$PROJECT_ROOT/app/cachy_freeze_gui/window.py" \
  "$INSTALL_ROOT/python/cachy_freeze_gui/window.py" || die "GUI verification failed."
cmp -s "$PROJECT_ROOT/app/cachy_freeze_gui/styles.py" \
  "$INSTALL_ROOT/python/cachy_freeze_gui/styles.py" || die "Style verification failed."
cmp -s "$PROJECT_ROOT/installer/install-applications.sh" \
  "$INSTALL_ROOT/deployment/installer/install-applications.sh" ||
  die "Deployment verification failed."
cmp -s "$PROJECT_ROOT/VERSION" "$INSTALL_ROOT/VERSION" ||
  die "Installed release version verification failed."
version_output=$(/usr/local/sbin/cachy-freeze version)
VERSION_OUTPUT=$version_output EXPECTED_VERSION=$release_version /usr/bin/python - <<'PY'
import json
import os

document = json.loads(os.environ["VERSION_OUTPUT"])
actual = document.get("result", {}).get("application_version")
if document.get("ok") is not True or actual != os.environ["EXPECTED_VERSION"]:
    raise SystemExit("Installed backend version verification failed.")
PY

trap - ERR

printf '%s\n' \
  "CachyFreeze $release_version application files were updated successfully." \
  "Rollback backup: $backup_dir" \
  "No boot, GRUB, initramfs, Btrfs, or reboot operation was performed."
