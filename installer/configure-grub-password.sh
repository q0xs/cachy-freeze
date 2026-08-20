#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly PROJECT_ROOT
readonly AUTH_GENERATOR=$PROJECT_ROOT/deepfreeze/grub/01_cachy_auth
readonly AUTH_CONFIG=/etc/cachy-freeze-grub-auth.conf
readonly AUTH_USER=cachyadmin

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

(( EUID == 0 )) || die "Run as root: sudo $0"
command -v grub-mkpasswd-pbkdf2 >/dev/null ||
  die "grub-mkpasswd-pbkdf2 was not found."
command -v grub-mkconfig >/dev/null || die "grub-mkconfig was not found."
[[ -r $AUTH_GENERATOR ]] || die "The GRUB authorization generator is missing."

if [[ ${CACHY_SETUP_NONINTERACTIVE:-0} == 1 ]]; then
  IFS= read -r grub_password || die "GRUB password was not received from the GUI channel."
  (( ${#grub_password} >= 12 && ${#grub_password} <= 256 )) ||
    die "GRUB password must contain 12-256 characters."
  [[ $grub_password != *:* && $grub_password != *$'\n'* && \
    $grub_password != *$'\r'* ]] ||
    die "GRUB password contains an unsupported character."
  hash=$(
    printf '%s\n%s\n' "$grub_password" "$grub_password" |
      grub-mkpasswd-pbkdf2 |
      sed -n 's/.*\(grub\.pbkdf2\.[^[:space:]]*\).*/\1/p'
  )
  unset grub_password
else
  printf '%s\n' \
    "GRUB maintenance username: $AUTH_USER" \
    "Enter the password twice when prompted; it will not be displayed."
  hash=$(
    grub-mkpasswd-pbkdf2 |
      sed -n 's/.*\(grub\.pbkdf2\.[^[:space:]]*\).*/\1/p'
  )
fi
[[ $hash == grub.pbkdf2.* ]] || die "The password hash could not be created."

install -m 0755 "$AUTH_GENERATOR" /etc/grub.d/01_cachy_auth
umask 077
printf 'GRUB_AUTH_USER=%q\nGRUB_AUTH_HASH=%q\n' \
  "$AUTH_USER" "$hash" >"$AUTH_CONFIG"

grub-mkconfig -o /boot/grub/grub.cfg
grep -q "^set superusers=\"$AUTH_USER\"$" /boot/grub/grub.cfg ||
  die "The GRUB user was not added to the configuration."
grep -q "^password_pbkdf2 $AUTH_USER " /boot/grub/grub.cfg ||
  die "The GRUB password hash was not added to the configuration."
grep -q "menuentry .*--id 'cachyos-current'.*--unrestricted" \
  /boot/grub/grub.cfg ||
  die "The managed GRUB entry was not found."
grep -q '^[[:space:]]*if authenticate; then$' /boot/grub/grub.cfg ||
  die "THAWED password enforcement was not added to GRUB."
grep -q 'set cachy_boot_authorized="false"' /boot/grub/grub.cfg ||
  die "The fail-closed GRUB authorization guard was not added."
grep -q 'if \[ "\${cachy_boot_authorized}" = "true" \]; then' /boot/grub/grub.cfg ||
  die "GRUB boot commands are not protected by the authorization result."
[[ $(grep -c '^menuentry ' /boot/grub/grub.cfg) -eq 1 ]] ||
  die "The GRUB menu contains more than one entry."

printf '%s\n' \
  "GRUB maintenance protection was enabled." \
  "Fixed GRUB username: $AUTH_USER" \
  "The menu shows one entry named FROZEN or THAWED according to the mode." \
  "FROZEN is passwordless; THAWED requires $AUTH_USER and the GRUB password."
