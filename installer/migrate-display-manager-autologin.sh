#!/usr/bin/env bash
set -Eeuo pipefail

readonly DISPLAY_MANAGER=/etc/systemd/system/display-manager.service
readonly LEGACY_SDDM_CONFIG=/etc/sddm.conf.d/cachy-autologin.conf
readonly PLASMA_LOGIN_CONFIG=/etc/plasmalogin.conf
readonly BACKEND=/usr/local/sbin/cachy-freeze

(( EUID == 0 )) || {
  printf '%s\n' "ERROR: Automatic-login migration requires root privileges." >&2
  exit 1
}

[[ $(readlink -f "$DISPLAY_MANAGER" 2>/dev/null) == */plasmalogin.service ]] || exit 0
[[ -r $LEGACY_SDDM_CONFIG && -x $BACKEND ]] || exit 0

legacy_user=$(sed -n 's/^[[:space:]]*User[[:space:]]*=[[:space:]]*//p' \
  "$LEGACY_SDDM_CONFIG" | head -n 1)
[[ $legacy_user =~ ^[a-z_][a-z0-9_-]{0,30}$ ]] || exit 0
[[ $legacy_user != localadm ]] || exit 0
id "$legacy_user" >/dev/null 2>&1 || exit 0

current_user=
if [[ -r $PLASMA_LOGIN_CONFIG ]]; then
  current_user=$(sed -n 's/^[[:space:]]*User[[:space:]]*=[[:space:]]*//p' \
    "$PLASMA_LOGIN_CONFIG" | head -n 1)
fi
[[ -z $current_user ]] || exit 0

"$BACKEND" user autologin "$legacy_user" >/dev/null
printf '%s\n' \
  "Existing CachyFreeze automatic-login selection migrated to Plasma Login Manager."
