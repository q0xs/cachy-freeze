#!/usr/bin/env bash
set -Eeuo pipefail
readonly ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec sudo bash "$ROOT/installer/08-KURULUMU-TAMAMLA.sh"
