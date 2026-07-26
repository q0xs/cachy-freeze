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
grep -q 'ConditionKernelCommandLine=cachy.freeze=1' \
  "$ROOT/initcpio/cachy-freeze-reset.service"
grep -q 'ConditionKernelCommandLine=cachy.freeze=1' \
  "$ROOT/../user/files/cachy-frozen-admin-restrict.service"
grep -q 'ensure_boot_layout' "$ROOT/bin/cachy-freeze"

[[ $(find "$PROJECT_ROOT" -maxdepth 1 -type f -name '*.sh' | wc -l) -eq 4 ]]
for desktop in "$PROJECT_ROOT"/user/desktop/*.desktop; do
  grep -qx '\[Desktop Entry\]' "$desktop"
  grep -q '^Type=Application$' "$desktop"
  grep -q '^Exec=/' "$desktop"
done

if command -v python >/dev/null; then
  python -m json.tool "$PROJECT_ROOT/policies/chrome/managed.json" >/dev/null
fi

if command -v systemd-analyze >/dev/null; then
  if ! verify_output=$(systemd-analyze verify \
    "$ROOT/initcpio/cachy-freeze-reset.service" \
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
