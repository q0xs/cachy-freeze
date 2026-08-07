#!/usr/bin/env bash
set -Eeuo pipefail
(( EUID == 0 )) || {
  printf 'Run as root: sudo %s\n' "$0" >&2
  exit 1
}
/usr/local/sbin/cachy-freeze freeze
printf '%s\n' "FROZEN mode enabled. User changes will reset after reboot."
