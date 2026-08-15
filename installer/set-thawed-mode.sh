#!/usr/bin/env bash
set -Eeuo pipefail
readonly PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
(( EUID == 0 )) || {
  printf 'Run as root: sudo %s\n' "$0" >&2
  exit 1
}
CACHY_FREEZE_CONFIG=/etc/cachy-freeze.conf \
  bash "$PROJECT_ROOT/deepfreeze/bin/cachy-freeze" thaw
printf '%s\n' "THAWED maintenance mode enabled. The persistent system will start after reboot."
