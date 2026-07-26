#!/usr/bin/env bash
set -Eeuo pipefail
readonly ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec sudo bash "$ROOT/installer/05-COZ.sh"
