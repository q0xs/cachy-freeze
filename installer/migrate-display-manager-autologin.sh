#!/usr/bin/env bash
set -Eeuo pipefail

readonly DISPLAY_MANAGER=/etc/systemd/system/display-manager.service
readonly LEGACY_SDDM_CONFIG=/etc/sddm.conf.d/cachy-autologin.conf
readonly LEGACY_PLASMA_LOGIN_CONFIG=/etc/plasmalogin.conf
readonly PLASMA_LOGIN_DROP_IN=/etc/plasmalogin.conf.d/90-cachy-freeze-autologin.conf
readonly LOGIN_SELECTION=/var/lib/cachy-freeze/login-selection.json
readonly BACKEND=/usr/local/sbin/cachy-freeze

(( EUID == 0 )) || {
  printf '%s\n' "ERROR: Login-selection migration requires root privileges." >&2
  exit 1
}

[[ $(readlink -f "$DISPLAY_MANAGER" 2>/dev/null) == */plasmalogin.service ]] || exit 0
[[ -x $BACKEND ]] || exit 0

legacy_user=
if [[ -r $LOGIN_SELECTION ]]; then
  legacy_user=$(/usr/bin/python - "$LOGIN_SELECTION" <<'PY'
import json
import sys

try:
    document = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, ValueError):
    raise SystemExit(0)
if document.get("schema") == 1 and document.get("password_required") is True:
    print(document.get("username") or "")
PY
)
fi
if [[ -z $legacy_user && -r $PLASMA_LOGIN_DROP_IN ]]; then
  legacy_user=$(sed -n 's/^[[:space:]]*User[[:space:]]*=[[:space:]]*//p' \
    "$PLASMA_LOGIN_DROP_IN" | head -n 1)
fi
if [[ -z $legacy_user && -r $LEGACY_PLASMA_LOGIN_CONFIG ]]; then
  legacy_user=$(sed -n 's/^[[:space:]]*User[[:space:]]*=[[:space:]]*//p' \
    "$LEGACY_PLASMA_LOGIN_CONFIG" | head -n 1)
fi
if [[ -z $legacy_user && -r $LEGACY_SDDM_CONFIG ]]; then
  legacy_user=$(sed -n 's/^[[:space:]]*User[[:space:]]*=[[:space:]]*//p' \
    "$LEGACY_SDDM_CONFIG" | head -n 1)
fi
if [[ ! $legacy_user =~ ^[a-z_][a-z0-9_-]{0,30}$ ]] || \
  [[ $legacy_user == localadm ]] || ! id "$legacy_user" >/dev/null 2>&1; then
  "$BACKEND" user autologin >/dev/null
  printf '%s\n' "CachyFreeze automatic login is disabled."
  exit 0
fi

"$BACKEND" user autologin "$legacy_user" >/dev/null
printf '%s\n' \
  "Password-required login-screen selection applied; automatic login is disabled."
