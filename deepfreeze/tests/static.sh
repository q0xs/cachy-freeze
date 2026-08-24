#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly ROOT
PROJECT_ROOT=$(cd -- "$ROOT/.." && pwd)
readonly PROJECT_ROOT

while IFS= read -r -d '' script; do
  bash -n "$script"
done < <(
  find "$PROJECT_ROOT" -type f \
    \( -name '*.sh' -o -path "$PROJECT_ROOT/deepfreeze/bin/cachy-freeze" -o \
      -path "$PROJECT_ROOT/deepfreeze/initcpio/cachy-freeze-reset" -o \
      -path "$PROJECT_ROOT/deepfreeze/initcpio/install-hook" -o \
      -path "$PROJECT_ROOT/deepfreeze/grub/01_cachy_auth" -o \
      -path "$PROJECT_ROOT/deepfreeze/grub/09_cachy_recovery_begin" -o \
      -path "$PROJECT_ROOT/deepfreeze/grub/98_cachy_recovery_end" -o \
      -path "$PROJECT_ROOT/deepfreeze/grub/99_cachy_freeze" -o \
      -path "$PROJECT_ROOT/app/cachy-freeze-manager-helper" -o \
      -path "$PROJECT_ROOT/app/cachy-freeze-setup" \) -print0
)

if command -v shellcheck >/dev/null; then
  while IFS= read -r -d '' script; do
    shellcheck -x "$script"
  done < <(
    find "$PROJECT_ROOT/installer" "$PROJECT_ROOT/packaging" "$ROOT/tests" \
      -type f -name '*.sh' -print0
  )
  shellcheck -x \
    "$ROOT/bin/cachy-freeze" \
    "$ROOT/initcpio/cachy-freeze-reset" \
    "$ROOT/initcpio/install-hook" \
    "$ROOT/grub/01_cachy_auth" \
    "$ROOT/grub/09_cachy_recovery_begin" \
    "$ROOT/grub/98_cachy_recovery_end" \
    "$ROOT/grub/99_cachy_freeze" \
    "$PROJECT_ROOT/app/cachy-freeze-manager-helper" \
    "$PROJECT_ROOT/app/cachy-freeze-setup"
else
  printf '%s\n' "WARNING: ShellCheck is unavailable; Bash syntax only."
fi

grep -qx 'MAINTENANCE_SUBVOL=@' "$ROOT/etc/cachy-freeze.conf"
grep -qx 'GOLDEN_SUBVOL=@golden' "$ROOT/etc/cachy-freeze.conf"
grep -qx 'ACTIVE_SUBVOL=@active' "$ROOT/etc/cachy-freeze.conf"
grep -qx 'CAPTURE_SUBVOL=@cachy-capture' "$ROOT/etc/cachy-freeze.conf"
grep -qx 'STATE_SUBVOL=@cachy-state' "$ROOT/etc/cachy-freeze.conf"
! grep -q '^SNAPSHOT_SUBVOL=' "$ROOT/etc/cachy-freeze.conf"
! grep -q 'RETENTION_COUNT' "$ROOT/etc/cachy-freeze.conf"
grep -q 'ConditionKernelCommandLine=cachy.freeze=1' \
  "$ROOT/initcpio/cachy-freeze-reset.service"
grep -q 'RemainAfterExit=yes' "$ROOT/initcpio/cachy-freeze-reset.service"
grep -q 'no prior runtime was retained' "$ROOT/initcpio/cachy-freeze-reset"
grep -q 'already reset for this boot' "$ROOT/initcpio/cachy-freeze-reset"
grep -q 'Refusing to delete mounted subvolume' "$ROOT/initcpio/cachy-freeze-reset"
grep -q 'MAINTENANCE_SUBVOL=@' "$PROJECT_ROOT/installer/install-freeze-engine.sh"
grep -q 'inspect-internal rootid' "$ROOT/initcpio/cachy-freeze-reset"
grep -q 'subvolume list "$TOP"' "$ROOT/initcpio/cachy-freeze-reset"
grep -q 'subvolume delete -i' "$ROOT/initcpio/cachy-freeze-reset"
! grep -q -- '--recursive' "$ROOT/initcpio/cachy-freeze-reset"
! grep -q '@active.previous' "$ROOT/initcpio/cachy-freeze-reset"
grep -q 'cachy.freeze=1 fstab=no' "$ROOT/grub/99_cachy_freeze"
grep -q 'CACHYFREEZE_RECOVERY_MENU_BEGIN' "$ROOT/grub/09_cachy_recovery_begin"
grep -q 'CACHYFREEZE_RECOVERY_MENU_END' "$ROOT/grub/98_cachy_recovery_end"
grep -q 'class OperationJournal' "$PROJECT_ROOT/src/cachy_freeze/catalog.py"
grep -q 'def freeze' "$PROJECT_ROOT/src/cachy_freeze/engine.py"
grep -q 'def thaw' "$PROJECT_ROOT/src/cachy_freeze/engine.py"
grep -q 'Refusing unmanaged Btrfs target' "$PROJECT_ROOT/src/cachy_freeze/engine.py"
grep -q 'ALLOWED_ACTIONS.*status.*freeze.*thaw.*reboot' \
  "$PROJECT_ROOT/app/cachy_freeze_gui/backend.py"
! grep -Eq 'snapshot-(list|create|delete)|user-create|applications-install|diagnostics' \
  "$PROJECT_ROOT/app/cachy-freeze-manager-helper"
grep -q 'auth_admin_keep' "$PROJECT_ROOT/app/org.cachyos.cachy-freeze.policy"
grep -qx 'Name=CachyFreeze' "$PROJECT_ROOT/app/cachy-freeze-manager.desktop"
grep -qx 'Exec=/usr/bin/cachy-freeze-manager' \
  "$PROJECT_ROOT/app/cachy-freeze-manager.desktop"
grep -q 'CachyFreeze-Installer-\$version.run' \
  "$PROJECT_ROOT/packaging/build-installer.sh"
grep -q 'SOURCE_DATE_EPOCH' "$PROJECT_ROOT/packaging/build-installer.sh"
grep -q 'will not reboot automatically' "$PROJECT_ROOT/installer/install-cachyfreeze.sh"
! grep -q 'systemctl reboot' "$PROJECT_ROOT/installer/install-cachyfreeze.sh"
grep -q 'Preserve every unrelated generator and boot entry under the recovery gate' \
  "$PROJECT_ROOT/installer/install-freeze-engine.sh"
grep -q 'set_grub_setting GRUB_DEFAULT cachyos-current' \
  "$PROJECT_ROOT/installer/install-freeze-engine.sh"
grep -q 'set_grub_setting GRUB_TIMEOUT_STYLE menu' \
  "$PROJECT_ROOT/installer/install-freeze-engine.sh"
grep -q 'set_grub_setting GRUB_TIMEOUT 5' \
  "$PROJECT_ROOT/installer/install-freeze-engine.sh"
! grep -q 'GRUB_DEFAULT=saved' "$PROJECT_ROOT/installer/install-freeze-engine.sh"
grep -q 'readonly AUTH_USER=cachyadmin' \
  "$PROJECT_ROOT/installer/configure-grub-password.sh"

for removed in \
  src/cachy_freeze/users.py \
  src/cachy_freeze/applications.py \
  src/cachy_freeze/power.py \
  src/cachy_freeze/diagnostics.py \
  deepfreeze/systemd/cachy-freeze-auto-snapshot.timer \
  deepfreeze/systemd/cachy-freeze-idle-power.service; do
  [[ ! -e $PROJECT_ROOT/$removed ]]
done

if command -v desktop-file-validate >/dev/null; then
  desktop-file-validate \
    "$PROJECT_ROOT/app/cachy-freeze-manager.desktop"
fi
if command -v python >/dev/null; then
  while IFS= read -r -d '' python_file; do
    python -m py_compile "$python_file"
  done < <(
    find "$PROJECT_ROOT/src" "$PROJECT_ROOT/app/cachy_freeze_gui" \
      "$PROJECT_ROOT/tests" -type f -name '*.py' -print0
  )
  python -m py_compile "$PROJECT_ROOT/app/cachy-freeze-manager"
fi
if command -v xmllint >/dev/null; then
  xmllint --noout "$PROJECT_ROOT/app/org.cachyos.cachy-freeze.policy"
fi
if command -v systemd-analyze >/dev/null; then
  systemd-analyze verify \
    "$ROOT/initcpio/cachy-freeze-reset.service" \
    "$ROOT/systemd/cachy-freeze-boot-health.service" >/dev/null 2>&1 || true
fi

printf '%s\n' "Static tests passed."
