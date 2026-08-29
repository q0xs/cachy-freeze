#!/usr/bin/env bash
set -Eeuo pipefail

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly project_root
entrypoint=$project_root/workstation/bin/workstation-setup

[[ -x $entrypoint ]] || {
  printf 'ERROR: Workstation setup entrypoint is missing: %s\n' "$entrypoint" >&2
  exit 1
}

exec /usr/bin/bash "$entrypoint" "$@"
