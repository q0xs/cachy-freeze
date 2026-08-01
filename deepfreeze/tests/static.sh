#!/usr/bin/env bash
set -Eeuo pipefail

readonly ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly PROJECT_ROOT=$(cd -- "$ROOT/.." && pwd)

while IFS= read -r -d '' script; do
  bash -n "$script"
done < <(
  find "$PROJECT_ROOT" \
    -path "$PROJECT_ROOT/CachyOS-USB-Kurulum" -prune -o \
    -type f \( -name '*.sh' -o \
      -path "$PROJECT_ROOT/deepfreeze/bin/cachy-freeze" -o \
      -path "$PROJECT_ROOT/deepfreeze/initcpio/cachy-freeze-reset" -o \
      -path "$PROJECT_ROOT/deepfreeze/initcpio/install-hook" -o \
      -path "$PROJECT_ROOT/deepfreeze/grub/01_cachy_auth" -o \
      -path "$PROJECT_ROOT/deepfreeze/grub/40_cachy_freeze" -o \
      -path "$PROJECT_ROOT/app/cachy-freeze-manager-helper" -o \
      -path "$PROJECT_ROOT/user/files/cachy-employee-reset" -o \
      -path "$PROJECT_ROOT/user/files/cachy-frozen-admin-restrict" -o \
      -path "$PROJECT_ROOT/user/files/cachy-kurulum-oturum-kapat" -o \
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
  printf '%s\n' "UYARI: shellcheck kurulu değil; yalnızca bash sözdizimi test edildi."
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
grep -q 'AUTH_ADMIN_KEEP' \
  "$ROOT/../user/files/49-company-employee-auth.rules"
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
grep -q 'gpasswd -d "$employee_user" wheel' \
  "$PROJECT_ROOT/installer/03-CALISAN-KULLANICI-OLUSTUR.sh"
grep -q 'auth_admin_keep' \
  "$PROJECT_ROOT/app/org.cachyos.cachy-freeze.policy"
grep -q '^Exec=/usr/bin/cachy-freeze-manager$' \
  "$PROJECT_ROOT/app/cachy-freeze-manager.desktop"

[[ $(find "$PROJECT_ROOT" -maxdepth 1 -type f -name '*.sh' | wc -l) -eq 5 ]]
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
      "UYARI: systemd-analyze sandbox izinleri nedeniyle tam çalışmadı."
  fi
fi

printf '%s\n' "Statik testler başarılı."
