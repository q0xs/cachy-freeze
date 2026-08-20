#!/usr/bin/env bash
set -Eeuo pipefail

readonly DISPLAY_MANAGER=/etc/systemd/system/display-manager.service
readonly LEGACY_SDDM_CONFIG=/etc/sddm.conf.d/cachy-autologin.conf
readonly LEGACY_PLASMA_LOGIN_CONFIG=/etc/plasmalogin.conf
readonly PLASMA_LOGIN_DROP_IN=/etc/plasmalogin.conf.d/90-cachy-freeze-autologin.conf
readonly BACKEND=/usr/local/sbin/cachy-freeze

(( EUID == 0 )) || {
  printf '%s\n' "ERROR: Automatic-login migration requires root privileges." >&2
  exit 1
}

[[ $(readlink -f "$DISPLAY_MANAGER" 2>/dev/null) == */plasmalogin.service ]] || exit 0
[[ -x $BACKEND ]] || exit 0

# Any existing owned drop-in is authoritative, including the intentionally empty
# User= form that disables a legacy automatic-login selection in the main file.
[[ -r $PLASMA_LOGIN_DROP_IN ]] && exit 0

legacy_user=
if [[ -r $LEGACY_PLASMA_LOGIN_CONFIG ]]; then
  legacy_user=$(sed -n 's/^[[:space:]]*User[[:space:]]*=[[:space:]]*//p' \
    "$LEGACY_PLASMA_LOGIN_CONFIG" | head -n 1)
fi
if [[ -z $legacy_user && -r $LEGACY_SDDM_CONFIG ]]; then
  legacy_user=$(sed -n 's/^[[:space:]]*User[[:space:]]*=[[:space:]]*//p' \
    "$LEGACY_SDDM_CONFIG" | head -n 1)
fi
[[ $legacy_user =~ ^[a-z_][a-z0-9_-]{0,30}$ ]] || exit 0
[[ $legacy_user != localadm ]] || exit 0
id "$legacy_user" >/dev/null 2>&1 || exit 0

"$BACKEND" user autologin "$legacy_user" >/dev/null
printf '%s\n' \
  "Existing automatic-login selection migrated to the CachyFreeze Plasma drop-in."
