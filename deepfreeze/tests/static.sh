#!/usr/bin/env bash
set -Eeuo pipefail

readonly ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly PROJECT_ROOT=$(cd -- "$ROOT/.." && pwd)

while IFS= read -r -d '' script; do
  bash -n "$script"
done < <(
  find "$PROJECT_ROOT" \
    -type f \( -name '*.sh' -o \
      -path "$PROJECT_ROOT/deepfreeze/bin/cachy-freeze" -o \
      -path "$PROJECT_ROOT/deepfreeze/initcpio/cachy-freeze-reset" -o \
      -path "$PROJECT_ROOT/deepfreeze/initcpio/install-hook" -o \
      -path "$PROJECT_ROOT/deepfreeze/grub/01_cachy_auth" -o \
      -path "$PROJECT_ROOT/deepfreeze/grub/40_cachy_freeze" -o \
      -path "$PROJECT_ROOT/app/cachy-freeze-manager-helper" -o \
      -path "$PROJECT_ROOT/app/cachy-freeze-setup" -o \
      -path "$PROJECT_ROOT/user/files/cachy-employee-reset" -o \
      -path "$PROJECT_ROOT/user/files/cachy-frozen-admin-restrict" -o \
      -path "$PROJECT_ROOT/user/files/cachyfreeze-finish-session" -o \
      -path "$PROJECT_ROOT/user/files/company-microsip" \) \
    -print0
)

if command -v shellcheck >/dev/null; then
  shellcheck -x \
    "$ROOT/bin/cachy-freeze" \
    "$ROOT/initcpio/cachy-freeze-reset" \
    "$ROOT/initcpio/install-hook" \
    "$ROOT/grub/01_cachy_auth" \
    "$ROOT/grub/40_cachy_freeze"
else
  printf '%s\n' "WARNING: ShellCheck is unavailable; only Bash syntax was tested."
fi

grep -q '^MAINTENANCE_SUBVOL=@$' "$ROOT/etc/cachy-freeze.conf"
grep -q '^GOLDEN_SUBVOL=@golden$' "$ROOT/etc/cachy-freeze.conf"
grep -q '^ACTIVE_SUBVOL=@active$' "$ROOT/etc/cachy-freeze.conf"
grep -q '^STATE_SUBVOL=@cachy-state$' "$ROOT/etc/cachy-freeze.conf"
grep -q '^SNAPSHOT_SUBVOL=@cachy-snapshots$' "$ROOT/etc/cachy-freeze.conf"
grep -q 'ConditionKernelCommandLine=cachy.freeze=1' \
  "$ROOT/initcpio/cachy-freeze-reset.service"
grep -q '^BOOT_FAILURE_LIMIT=3$' "$ROOT/etc/cachy-freeze.conf"
grep -q 'ConditionKernelCommandLine=cachy.freeze=1' \
  "$ROOT/../user/files/cachy-frozen-admin-restrict.service"
grep -q 'def preflight' "$PROJECT_ROOT/src/cachy_freeze/engine.py"
grep -q 'begin_transaction' "$PROJECT_ROOT/src/cachy_freeze/engine.py"
grep -Fq '"$BACKEND" publish --description "Golden publication from the GUI" >&2' \
  "$PROJECT_ROOT/app/cachy-freeze-manager-helper"
grep -q 'chpasswd", "--encrypted"' \
  "$PROJECT_ROOT/src/cachy_freeze/users.py"
! grep -q '"--password"' \
  "$PROJECT_ROOT/src/cachy_freeze/users.py"
grep -q 'test_encrypted_password_hash_uses_stdin_safe_payload' \
  "$PROJECT_ROOT/tests/test_users.py"
for aur_package in google-chrome slack-desktop gtk2 zoiper-bin anydesk-bin; do
  [[ -r $PROJECT_ROOT/vendor/aur/$aur_package/PKGBUILD ]]
  grep -Eq "^${aur_package} [0-9a-f]{40}$" \
    "$PROJECT_ROOT/vendor/aur/AUR-REVISIONS.txt"
done
! sed -n '/^aur_install()/,/^}/p' \
  "$PROJECT_ROOT/installer/lib/common.sh" | grep -q 'git clone'
for agent_rules in \
  "$PROJECT_ROOT/AGENTS.md" \
  "$PROJECT_ROOT/app/AGENTS.md" \
  "$PROJECT_ROOT/installer/AGENTS.md" \
  "$PROJECT_ROOT/deepfreeze/AGENTS.md"; do
  [[ -s $agent_rules ]]
done
grep -q 'cachy-user-template' \
  "$ROOT/../user/files/cachy-employee-reset"
grep -q '^ColorScheme=BreezeDark$' \
  "$PROJECT_ROOT/user/files/kdeglobals"
grep -q '^LookAndFeelPackage=org.kde.breezedark.desktop$' \
  "$PROJECT_ROOT/user/files/kdeglobals"
grep -q '^name=breeze-dark$' \
  "$PROJECT_ROOT/user/files/plasmarc"
! grep -q 'Action Restrictions' \
  "$PROJECT_ROOT/user/files/kdeglobals"
! grep -Eq 'gpasswd|usermod --append --groups' \
  "$PROJECT_ROOT/installer/create-employee-user.sh"
grep -q 'auth_admin_keep' \
  "$PROJECT_ROOT/app/org.cachyos.cachy-freeze.policy"
grep -q '^Exec=/usr/bin/cachy-freeze-manager$' \
  "$PROJECT_ROOT/app/cachy-freeze-manager.desktop"
grep -q '^Icon=cachy-freeze$' \
  "$PROJECT_ROOT/app/cachy-freeze-manager.desktop"
grep -q '^Name=CachyFreeze Setup$' \
  "$PROJECT_ROOT/cachyfreeze-setup.desktop"
grep -q '^Terminal=false$' \
  "$PROJECT_ROOT/cachyfreeze-setup.desktop"
grep -q '^Icon=cachy-freeze$' \
  "$PROJECT_ROOT/cachyfreeze-setup.desktop"
if command -v desktop-file-validate >/dev/null; then
  desktop-file-validate \
    "$PROJECT_ROOT/cachyfreeze-setup.desktop" \
    "$PROJECT_ROOT/app/cachy-freeze-manager.desktop" \
    "$PROJECT_ROOT"/user/desktop/*.desktop
fi
grep -q 'setup-install)' \
  "$PROJECT_ROOT/app/cachy-freeze-manager-helper"
grep -q 'setup-freeze)' \
  "$PROJECT_ROOT/app/cachy-freeze-manager-helper"
! sed -n '/setup-freeze)/,/;;/p' \
  "$PROJECT_ROOT/app/cachy-freeze-manager-helper" | grep -q '/etc/cachy-employee.conf'
grep -q 'CACHY_SETUP_NONINTERACTIVE' \
  "$PROJECT_ROOT/installer/create-employee-user.sh"
grep -q 'prepare-standard-user.sh' \
  "$PROJECT_ROOT/src/cachy_freeze/users.py"
grep -q 'cachyfreeze-finish-session' \
  "$PROJECT_ROOT/installer/create-employee-user.sh"
! grep -q 'cachy-kurulum-oturum-kapat' \
  "$PROJECT_ROOT/installer/create-employee-user.sh"
for required_user_asset in \
  "$PROJECT_ROOT/user/files/company-microsip" \
  "$PROJECT_ROOT/user/files/cachyfreeze-finish-session" \
  "$PROJECT_ROOT/installer/prepare-standard-user.sh" \
  "$PROJECT_ROOT/installer/deploy-live-app.sh"; do
  [[ -x $required_user_asset ]]
done

[[ -x $PROJECT_ROOT/install.sh ]]
[[ -s $PROJECT_ROOT/app/cachy_freeze_gui/assets/cachy-freeze.png ]]
grep -q 'setWindowIcon' "$PROJECT_ROOT/app/cachy_freeze_gui/main.py"
grep -q 'GRUB maintenance username' "$PROJECT_ROOT/app/cachy_freeze_gui/window.py"
grep -q 'readonly AUTH_USER=cachyadmin' \
  "$PROJECT_ROOT/installer/configure-grub-password.sh"
grep -q 'fixed GRUB username.*cachyadmin' "$PROJECT_ROOT/README.md"
grep -q 'always `cachyadmin`' "$PROJECT_ROOT/docs/installation.md"
grep -q '/usr/share/icons/hicolor/512x512/apps/cachy-freeze.png' \
  "$PROJECT_ROOT/installer/install-freeze-engine.sh"
grep -Fq 'git clone --branch main https://github.com/q0xs/cachy-freeze.git' \
  "$PROJECT_ROOT/README.md"
! grep -REq 'archive/refs/heads|raw.githubusercontent.com/.*/install.sh|curl .*install.sh' \
  "$PROJECT_ROOT/README.md" "$PROJECT_ROOT/docs"/*.md
for desktop in "$PROJECT_ROOT"/user/desktop/*.desktop; do
  grep -qx '\[Desktop Entry\]' "$desktop"
  grep -q '^Type=Application$' "$desktop"
  grep -q '^Exec=/' "$desktop"
done

if command -v python >/dev/null; then
  python -m json.tool "$PROJECT_ROOT/policies/chrome/managed.json" >/dev/null
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
  if ! verify_output=$(systemd-analyze verify \
    "$ROOT/initcpio/cachy-freeze-reset.service" \
    "$ROOT/systemd/cachy-freeze-boot-health.service" \
    "$ROOT/systemd/cachy-freeze-auto-snapshot.service" \
    "$ROOT/systemd/cachy-freeze-auto-snapshot.timer" \
    "$PROJECT_ROOT/user/files/cachy-employee-reset.service" \
    "$PROJECT_ROOT/user/files/cachy-frozen-admin-restrict.service" 2>&1); then
    unexpected_output=$(grep -Ev 'SO_PASSRIGHTS|SO_PASSCRED' \
      <<<"$verify_output" || true)
    [[ -z $unexpected_output ]] || {
      printf '%s\n' "$unexpected_output" >&2
      exit 1
    }
    printf '%s\n' \
      "WARNING: systemd-analyze could not run fully because of sandbox permissions."
  fi
fi

printf '%s\n' "Static tests passed."
