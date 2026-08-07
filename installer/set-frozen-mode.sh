#!/usr/bin/env bash
set -Eeuo pipefail
(( EUID == 0 )) || {
  printf 'Su sekilde calistir: sudo %s\n' "$0" >&2
  exit 1
}
/usr/local/sbin/cachy-freeze freeze
printf '%s\n' "Frozen mod etkin. Yeniden baslatinca kullanici degisiklikleri sifirlanacak."
