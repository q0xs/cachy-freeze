#!/usr/bin/env bash
set -Eeuo pipefail
(( EUID == 0 )) || {
  printf 'Run as root: sudo %s\n' "$0" >&2
  exit 1
}
/usr/local/sbin/cachy-freeze publish
printf '%s\n' "A new Golden was published. Enable FROZEN from the application when ready."
